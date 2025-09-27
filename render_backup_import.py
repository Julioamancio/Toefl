#!/usr/bin/env python3
"""
Script para importar backup de dados no Render
Pode ser usado independentemente ou junto com o reset

Uso:
python render_backup_import.py [arquivo_backup.json]

Se nenhum arquivo for especificado, procura automaticamente na pasta backups/
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Configurar o caminho para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def import_backup_to_render(backup_file=None):
    """Importa backup para o banco do Render"""
    
    try:
        from app import create_app
        from models import db, Student, Teacher, Class, ComputedLevel
        
        print("📥 RENDER BACKUP IMPORT TOOL")
        print("=" * 50)
        print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Procurar arquivo de backup se não especificado
        if not backup_file:
            backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
            if os.path.exists(backup_dir):
                backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
                if backup_files:
                    # Usar o mais recente
                    backup_files.sort()
                    backup_file = os.path.join(backup_dir, backup_files[-1])
                    print(f"📁 Backup encontrado automaticamente: {backup_file}")
        
        if not backup_file or not os.path.exists(backup_file):
            print("❌ Nenhum arquivo de backup encontrado!")
            print("💡 Coloque o arquivo .json na pasta 'backups/' ou especifique o caminho")
            return False
        
        # Criar aplicação
        app = create_app('production')
        
        with app.app_context():
            print(f"📂 Carregando backup: {backup_file}")
            
            # Carregar dados do backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📊 Dados encontrados no backup:")
            if 'teachers' in data:
                print(f"   👨‍🏫 Professores: {len(data['teachers'])}")
            if 'classes' in data:
                print(f"   🏫 Turmas: {len(data['classes'])}")
            if 'students' in data:
                print(f"   👨‍🎓 Estudantes: {len(data['students'])}")
            if 'computed_levels' in data:
                print(f"   📊 Níveis computados: {len(data['computed_levels'])}")
            
            # Verificar se já existem dados
            existing_students = Student.query.count()
            existing_teachers = Teacher.query.count()
            existing_classes = Class.query.count()
            
            if existing_students > 0 or existing_teachers > 0 or existing_classes > 0:
                print(f"⚠️  ATENÇÃO: Dados existentes encontrados!")
                print(f"   👨‍🎓 Estudantes existentes: {existing_students}")
                print(f"   👨‍🏫 Professores existentes: {existing_teachers}")
                print(f"   🏫 Turmas existentes: {existing_classes}")
                print("   💡 Use RESET_DATABASE=true para limpar antes da importação")
            
            # Importar Teachers
            if 'teachers' in data and data['teachers']:
                print(f"👨‍🏫 Importando {len(data['teachers'])} professores...")
                imported_teachers = 0
                for teacher_data in data['teachers']:
                    try:
                        # Verificar se já existe
                        existing = Teacher.query.filter_by(email=teacher_data.get('email')).first()
                        if not existing:
                            teacher = Teacher(**teacher_data)
                            db.session.add(teacher)
                            imported_teachers += 1
                    except Exception as e:
                        print(f"   ⚠️  Erro ao importar professor: {e}")
                
                db.session.commit()
                print(f"   ✅ {imported_teachers} professores importados!")
            
            # Importar Classes
            if 'classes' in data and data['classes']:
                print(f"🏫 Importando {len(data['classes'])} turmas...")
                imported_classes = 0
                for class_data in data['classes']:
                    try:
                        # Verificar se já existe
                        existing = Class.query.filter_by(name=class_data.get('name')).first()
                        if not existing:
                            class_obj = Class(**class_data)
                            db.session.add(class_obj)
                            imported_classes += 1
                    except Exception as e:
                        print(f"   ⚠️  Erro ao importar turma: {e}")
                
                db.session.commit()
                print(f"   ✅ {imported_classes} turmas importadas!")
            
            # Importar Students (com limpeza de asteriscos)
            if 'students' in data and data['students']:
                print(f"👨‍🎓 Importando {len(data['students'])} estudantes...")
                imported_students = 0
                cleaned_asterisks = 0
                
                for student_data in data['students']:
                    try:
                        # Limpar asteriscos durante importação
                        asterisk_found = False
                        if 'Read_CEFR' in student_data and student_data['Read_CEFR']:
                            if '*' in str(student_data['Read_CEFR']):
                                student_data['Read_CEFR'] = str(student_data['Read_CEFR']).replace('*', '')
                                asterisk_found = True
                        
                        if 'LFM_CEFR' in student_data and student_data['LFM_CEFR']:
                            if '*' in str(student_data['LFM_CEFR']):
                                student_data['LFM_CEFR'] = str(student_data['LFM_CEFR']).replace('*', '')
                                asterisk_found = True
                        
                        if 'Listen_CEFR' in student_data and student_data['Listen_CEFR']:
                            if '*' in str(student_data['Listen_CEFR']):
                                student_data['Listen_CEFR'] = str(student_data['Listen_CEFR']).replace('*', '')
                                asterisk_found = True
                        
                        if asterisk_found:
                            cleaned_asterisks += 1
                        
                        # Verificar se já existe (por email ou nome)
                        existing = None
                        if 'email' in student_data and student_data['email']:
                            existing = Student.query.filter_by(email=student_data['email']).first()
                        
                        if not existing:
                            student = Student(**student_data)
                            db.session.add(student)
                            imported_students += 1
                            
                    except Exception as e:
                        print(f"   ⚠️  Erro ao importar estudante: {e}")
                
                db.session.commit()
                print(f"   ✅ {imported_students} estudantes importados!")
                if cleaned_asterisks > 0:
                    print(f"   🔧 {cleaned_asterisks} estudantes tiveram asteriscos removidos!")
            
            # Importar ComputedLevels
            if 'computed_levels' in data and data['computed_levels']:
                print(f"📊 Importando {len(data['computed_levels'])} níveis computados...")
                imported_levels = 0
                for level_data in data['computed_levels']:
                    try:
                        # Verificar se já existe
                        existing = ComputedLevel.query.filter_by(
                            student_id=level_data.get('student_id')
                        ).first()
                        if not existing:
                            level = ComputedLevel(**level_data)
                            db.session.add(level)
                            imported_levels += 1
                    except Exception as e:
                        print(f"   ⚠️  Erro ao importar nível computado: {e}")
                
                db.session.commit()
                print(f"   ✅ {imported_levels} níveis computados importados!")
            
            # Estatísticas finais
            final_students = Student.query.count()
            final_teachers = Teacher.query.count()
            final_classes = Class.query.count()
            final_levels = ComputedLevel.query.count()
            
            print("\n📊 ESTATÍSTICAS FINAIS:")
            print(f"   👨‍🎓 Total de estudantes: {final_students}")
            print(f"   👨‍🏫 Total de professores: {final_teachers}")
            print(f"   🏫 Total de turmas: {final_classes}")
            print(f"   📊 Total de níveis computados: {final_levels}")
            
            print(f"\n🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"⏰ Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Importar backup para o Render')
    parser.add_argument('backup_file', nargs='?', help='Arquivo de backup para importar')
    
    args = parser.parse_args()
    
    success = import_backup_to_render(args.backup_file)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()