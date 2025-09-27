#!/usr/bin/env python3
"""
Script para limpar completamente o banco de dados do Render
e permitir importação de backup limpo.

Este script:
1. Remove todas as tabelas existentes
2. Recria as tabelas do zero
3. Permite importação de backup
4. Executa correções automáticas

Uso:
- Para reset completo: python render_database_reset.py --reset
- Para reset + importar backup: python render_database_reset.py --reset --import-backup
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Configurar o caminho para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Student, Teacher, Class, ComputedLevel

def drop_all_tables():
    """Remove todas as tabelas do banco de dados"""
    print("🗑️  Removendo todas as tabelas...")
    
    try:
        with app.app_context():
            # Usar drop_all para remover todas as tabelas
            db.drop_all()
            print("✅ Todas as tabelas foram removidas!")
            return True
    except Exception as e:
        print(f"❌ Erro ao remover tabelas: {e}")
        return False

def create_all_tables():
    """Recria todas as tabelas"""
    print("🔨 Criando todas as tabelas...")
    
    try:
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✅ Todas as tabelas foram criadas!")
            
            # Verificar tabelas criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas criadas: {tables}")
            
            return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def import_backup_data(backup_file=None):
    """Importa dados de backup"""
    if not backup_file:
        # Procurar arquivo de backup na pasta backups
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
            if backup_files:
                backup_file = os.path.join(backup_dir, backup_files[-1])  # Usar o mais recente
                print(f"📁 Usando backup: {backup_file}")
    
    if not backup_file or not os.path.exists(backup_file):
        print("⚠️  Nenhum arquivo de backup encontrado!")
        return False
    
    print(f"📥 Importando dados de: {backup_file}")
    
    try:
        with app.app_context():
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Importar Teachers
            if 'teachers' in data:
                print(f"👨‍🏫 Importando {len(data['teachers'])} professores...")
                for teacher_data in data['teachers']:
                    teacher = Teacher(**teacher_data)
                    db.session.add(teacher)
                db.session.commit()
                print("✅ Professores importados!")
            
            # Importar Classes
            if 'classes' in data:
                print(f"🏫 Importando {len(data['classes'])} turmas...")
                for class_data in data['classes']:
                    class_obj = Class(**class_data)
                    db.session.add(class_obj)
                db.session.commit()
                print("✅ Turmas importadas!")
            
            # Importar Students
            if 'students' in data:
                print(f"👨‍🎓 Importando {len(data['students'])} estudantes...")
                for student_data in data['students']:
                    # Limpar asteriscos durante a importação
                    if 'Read_CEFR' in student_data and student_data['Read_CEFR']:
                        student_data['Read_CEFR'] = str(student_data['Read_CEFR']).replace('*', '')
                    if 'LFM_CEFR' in student_data and student_data['LFM_CEFR']:
                        student_data['LFM_CEFR'] = str(student_data['LFM_CEFR']).replace('*', '')
                    if 'Listen_CEFR' in student_data and student_data['Listen_CEFR']:
                        student_data['Listen_CEFR'] = str(student_data['Listen_CEFR']).replace('*', '')
                    
                    student = Student(**student_data)
                    db.session.add(student)
                db.session.commit()
                print("✅ Estudantes importados!")
            
            # Importar ComputedLevels
            if 'computed_levels' in data:
                print(f"📊 Importando {len(data['computed_levels'])} níveis computados...")
                for level_data in data['computed_levels']:
                    level = ComputedLevel(**level_data)
                    db.session.add(level)
                db.session.commit()
                print("✅ Níveis computados importados!")
            
            print("🎉 Importação concluída com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_cefr_asterisks():
    """Remove asteriscos dos campos CEFR e recalcula General_CEFR"""
    print("🔧 Verificando e corrigindo asteriscos nos dados...")
    
    try:
        with app.app_context():
            asterisk_count = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            if asterisk_count > 0:
                print(f"🔍 Encontrados {asterisk_count} registros com asteriscos - corrigindo...")
                
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
                
                db.session.commit()
                print(f"✅ {corrections} estudantes corrigidos!")
            else:
                print("✅ Nenhum asterisco encontrado nos dados!")
                
            return True
            
    except Exception as e:
        print(f"❌ Erro na correção de asteriscos: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Reset do banco de dados do Render')
    parser.add_argument('--reset', action='store_true', help='Fazer reset completo do banco')
    parser.add_argument('--import-backup', action='store_true', help='Importar backup após reset')
    parser.add_argument('--backup-file', help='Arquivo de backup específico para importar')
    parser.add_argument('--fix-asterisks', action='store_true', help='Apenas corrigir asteriscos')
    
    args = parser.parse_args()
    
    print("🚀 RENDER DATABASE RESET TOOL")
    print("=" * 50)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.fix_asterisks:
        print("🔧 Modo: Correção de asteriscos apenas")
        success = fix_cefr_asterisks()
        if success:
            print("✅ Correção concluída com sucesso!")
        else:
            print("❌ Falha na correção!")
            sys.exit(1)
        return
    
    if not args.reset:
        print("⚠️  Use --reset para confirmar o reset do banco de dados")
        print("⚠️  ATENÇÃO: Isso irá APAGAR TODOS OS DADOS!")
        return
    
    print("🗑️  Modo: Reset completo do banco de dados")
    print("⚠️  ATENÇÃO: TODOS OS DADOS SERÃO PERDIDOS!")
    
    # Passo 1: Remover todas as tabelas
    if not drop_all_tables():
        print("❌ Falha ao remover tabelas!")
        sys.exit(1)
    
    # Passo 2: Recriar tabelas
    if not create_all_tables():
        print("❌ Falha ao criar tabelas!")
        sys.exit(1)
    
    # Passo 3: Importar backup (se solicitado)
    if args.import_backup:
        if not import_backup_data(args.backup_file):
            print("❌ Falha na importação do backup!")
            sys.exit(1)
        
        # Passo 4: Corrigir asteriscos
        fix_cefr_asterisks()
    
    print("🎉 RESET CONCLUÍDO COM SUCESSO!")
    print(f"⏰ Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()