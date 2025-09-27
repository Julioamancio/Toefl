#!/usr/bin/env python3
"""
Script de migração para Render.com - Adiciona coluna turma_meta
Este script deve ser executado no Render.com para corrigir o erro interno do servidor.
"""

import os
import sys
from sqlalchemy import text, inspect

def migrate_turma_meta():
    """Migra a coluna turma_meta no Render.com"""
    try:
        # Importar depois de configurar o ambiente
        from app import create_app
        from models import db, Student, Class
        
        print("🚀 Iniciando migração turma_meta no Render.com...")
        
        # Criar aplicação Flask
        app_tuple = create_app()
        app = app_tuple[0] if isinstance(app_tuple, tuple) else app_tuple
        
        with app.app_context():
            # Verificar se a coluna já existe
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('students')]
            
            if 'turma_meta' not in columns:
                print("📝 Adicionando coluna turma_meta...")
                
                # Adicionar a coluna turma_meta
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE students ADD COLUMN turma_meta VARCHAR(10)'))
                    conn.commit()
                
                print("✅ Coluna turma_meta adicionada com sucesso!")
            else:
                print("ℹ️ Coluna turma_meta já existe.")
            
            # Migrar dados existentes
            print("🔄 Migrando dados existentes...")
            
            students_to_migrate = Student.query.filter(Student.turma_meta.is_(None)).all()
            migrated_count = 0
            
            for student in students_to_migrate:
                if student.class_info and student.class_info.meta_label:
                    student.turma_meta = student.class_info.meta_label
                    migrated_count += 1
            
            if migrated_count > 0:
                db.session.commit()
                print(f"✅ {migrated_count} alunos migrados com sucesso!")
            else:
                print("ℹ️ Nenhum aluno precisou ser migrado.")
            
            print("🎉 Migração concluída com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_turma_meta()
    sys.exit(0 if success else 1)