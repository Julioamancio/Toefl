#!/usr/bin/env python3
"""
Script para ser executado automaticamente no deploy do Render
Integra com o processo de inicialização para corrigir asteriscos e migrar schema
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import logging

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_user_schema():
    """Migrate the users table to add missing columns"""
    try:
        logger.info("🔧 SCHEMA-FIX: Starting user schema migration...")
        
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
        
        # Create engine
        engine = create_engine(database_url)
        
        # Check if users table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'users' not in tables:
            logger.error("Users table does not exist!")
            return False
        
        # List of columns that should exist in the users table
        required_columns = [
            ('is_teacher', 'BOOLEAN DEFAULT FALSE'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('last_login', 'TIMESTAMP NULL')
        ]
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                for column_name, column_definition in required_columns:
                    # Check if column exists
                    columns = inspector.get_columns('users')
                    existing_columns = [col['name'] for col in columns]
                    
                    if column_name not in existing_columns:
                        logger.info(f"🔧 SCHEMA-FIX: Adding column {column_name} to users table...")
                        
                        # Add the column
                        sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"
                        conn.execute(text(sql))
                        
                        logger.info(f"✅ SCHEMA-FIX: Successfully added column {column_name}")
                    else:
                        logger.info(f"✅ SCHEMA-FIX: Column {column_name} already exists, skipping...")
                
                # Commit transaction
                trans.commit()
                logger.info("✅ SCHEMA-FIX: User schema migration completed successfully!")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"❌ SCHEMA-FIX: Error during migration, rolling back: {e}")
                return False
                
    except SQLAlchemyError as e:
        logger.error(f"❌ SCHEMA-FIX: Database connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ SCHEMA-FIX: Unexpected error: {e}")
        return False

def auto_fix_on_deploy():
    """Executa correção automática durante o deploy"""
    try:
        print("🔧 AUTO-FIX: Verificando e corrigindo asteriscos durante deploy...")
        
        # PRIMEIRO: Migrar schema do usuário se necessário
        print("🔧 AUTO-FIX: Verificando schema da tabela users...")
        schema_success = migrate_user_schema()
        if not schema_success:
            print("⚠️  AUTO-FIX: Schema migration falhou, mas continuando com correção de asteriscos...")
        
        # Forçar ambiente de produção
        os.environ['FLASK_ENV'] = 'production'
        
        from app import create_app
        from models import db, Student
        
        app = create_app('production')
        
        with app.app_context():
            # Verificar se existem asteriscos
            asterisk_count = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            if asterisk_count == 0:
                print("✅ AUTO-FIX: Nenhum asterisco encontrado. Dados OK!")
                return True
            
            print(f"🔍 AUTO-FIX: Encontrados {asterisk_count} registros com asteriscos")
            print("🔧 AUTO-FIX: Aplicando correções...")
            
            # Buscar e corrigir estudantes com asteriscos
            students_with_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).all()
            
            corrections = 0
            for student in students_with_asterisks:
                changed = False
                
                if student.Read_CEFR and '*' in str(student.Read_CEFR):
                    student.Read_CEFR = str(student.Read_CEFR).replace('*', '')
                    changed = True
                
                if student.LFM_CEFR and '*' in str(student.LFM_CEFR):
                    student.LFM_CEFR = str(student.LFM_CEFR).replace('*', '')
                    changed = True
                
                if student.Listen_CEFR and '*' in str(student.Listen_CEFR):
                    student.Listen_CEFR = str(student.Listen_CEFR).replace('*', '')
                    changed = True
                
                if changed:
                    # Recalcular General_CEFR
                    levels = []
                    if student.Listen_CEFR and str(student.Listen_CEFR).strip():
                        levels.append(str(student.Listen_CEFR).strip())
                    if student.Read_CEFR and str(student.Read_CEFR).strip():
                        levels.append(str(student.Read_CEFR).strip())
                    if student.LFM_CEFR and str(student.LFM_CEFR).strip():
                        levels.append(str(student.LFM_CEFR).strip())
                    
                    if levels:
                        level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
                        valid_levels = [level for level in levels if level in level_order]
                        
                        if valid_levels:
                            min_level_index = min(level_order.index(level) for level in valid_levels)
                            student.General_CEFR = level_order[min_level_index]
                    
                    corrections += 1
            
            # Salvar todas as correções
            db.session.commit()
            
            # Verificação final
            final_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            print(f"✅ AUTO-FIX: {corrections} estudantes corrigidos")
            print(f"📊 AUTO-FIX: Asteriscos restantes: {final_asterisks}")
            
            return final_asterisks == 0
            
    except Exception as e:
        print(f"❌ AUTO-FIX ERROR: {e}")
        return False

if __name__ == '__main__':
    print("🚀 RENDER AUTO-FIX DEPLOY")
    print("="*40)
    
    # First run schema migration
    print("🔧 SCHEMA-FIX: Running database schema migration...")
    schema_success = migrate_user_schema()
    
    if schema_success:
        print("✅ SCHEMA-FIX: Schema migration completed successfully!")
    else:
        print("⚠️  SCHEMA-FIX: Schema migration had issues, but continuing...")
    
    print("-"*40)
    
    # Then run asterisk fixes
    success = auto_fix_on_deploy()
    
    if success:
        print("✅ AUTO-FIX: Correções aplicadas com sucesso!")
    else:
        print("⚠️  AUTO-FIX: Algumas correções podem não ter sido aplicadas")
    
    print("="*40)