#!/usr/bin/env python3
"""
Script para inicializar o banco de dados no Render
Executa automaticamente durante o deploy
"""
import os
import sys
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def init_render_database():
    """Inicializa o banco de dados no Render"""
    try:
        # Importar após configurar o path
        from app import create_app
        from models import db, User
        
        print("🚀 Inicializando banco de dados no Render...")
        
        # Verificar se deve fazer reset completo
        reset_database = os.environ.get('RESET_DATABASE', 'false').lower() == 'true'
        import_backup = os.environ.get('IMPORT_BACKUP', 'false').lower() == 'true'
        
        if reset_database:
            print("🗑️  MODO RESET: Limpando banco de dados completamente...")
        
        # Criar aplicação em modo produção
        app = create_app('production')
        
        with app.app_context():
            # Verificar conexão com o banco
            print("🔗 Verificando conexão com PostgreSQL...")
            
            # Se reset solicitado, remover todas as tabelas primeiro
            if reset_database:
                print("🗑️  Removendo todas as tabelas existentes...")
                db.drop_all()
                print("✅ Tabelas removidas!")
            
            # Criar todas as tabelas
            print("🔧 Criando tabelas do banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # Verificar se já existe um usuário admin
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                print("👤 Criando usuário administrador...")
                
                # Usar senha do ambiente ou padrão
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                
                admin_user = User(
                    username='admin',
                    email='admin@toefl.com',
                    is_admin=True,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                admin_user.set_password(admin_password)
                
                db.session.add(admin_user)
                db.session.commit()
                
                print("✅ Usuário admin criado com sucesso!")
                print(f"   Username: admin")
                print(f"   Password: {admin_password}")
            else:
                print("ℹ️  Usuário admin já existe.")
            
            # Verificar tabelas criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas no banco: {tables}")
            
            # AUTO-FIX: Corrigir asteriscos nos dados existentes
            print("🔧 Verificando e corrigindo asteriscos nos dados...")
            try:
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
                    print(f"✅ {corrections} estudantes corrigidos automaticamente!")
                else:
                    print("✅ Nenhum asterisco encontrado nos dados!")
                    
            except Exception as fix_error:
                print(f"⚠️  Erro na correção automática: {fix_error}")
                # Não falha a inicialização por causa disso
            
            # IMPORTAÇÃO DE BACKUP (se solicitada)
            if import_backup:
                print("📥 Importando backup de dados...")
                try:
                    import json
                    from models import Student, Teacher, Class, ComputedLevel
                    
                    # Procurar arquivo de backup
                    backup_file = None
                    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
                    
                    if os.path.exists(backup_dir):
                        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
                        if backup_files:
                            backup_file = os.path.join(backup_dir, backup_files[-1])
                            print(f"📁 Usando backup: {backup_file}")
                    
                    if backup_file and os.path.exists(backup_file):
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Importar Teachers
                        if 'teachers' in data:
                            print(f"👨‍🏫 Importando {len(data['teachers'])} professores...")
                            for teacher_data in data['teachers']:
                                teacher = Teacher(**teacher_data)
                                db.session.add(teacher)
                            db.session.commit()
                        
                        # Importar Classes
                        if 'classes' in data:
                            print(f"🏫 Importando {len(data['classes'])} turmas...")
                            for class_data in data['classes']:
                                class_obj = Class(**class_data)
                                db.session.add(class_obj)
                            db.session.commit()
                        
                        # Importar Students (com limpeza de asteriscos)
                        if 'students' in data:
                            print(f"👨‍🎓 Importando {len(data['students'])} estudantes...")
                            for student_data in data['students']:
                                # Limpar asteriscos durante importação
                                if 'Read_CEFR' in student_data and student_data['Read_CEFR']:
                                    student_data['Read_CEFR'] = str(student_data['Read_CEFR']).replace('*', '')
                                if 'LFM_CEFR' in student_data and student_data['LFM_CEFR']:
                                    student_data['LFM_CEFR'] = str(student_data['LFM_CEFR']).replace('*', '')
                                if 'Listen_CEFR' in student_data and student_data['Listen_CEFR']:
                                    student_data['Listen_CEFR'] = str(student_data['Listen_CEFR']).replace('*', '')
                                
                                student = Student(**student_data)
                                db.session.add(student)
                            db.session.commit()
                        
                        # Importar ComputedLevels
                        if 'computed_levels' in data:
                            print(f"📊 Importando {len(data['computed_levels'])} níveis computados...")
                            for level_data in data['computed_levels']:
                                level = ComputedLevel(**level_data)
                                db.session.add(level)
                            db.session.commit()
                        
                        print("✅ Backup importado com sucesso!")
                    else:
                        print("⚠️  Nenhum arquivo de backup encontrado para importar!")
                        
                except Exception as import_error:
                    print(f"❌ Erro na importação do backup: {import_error}")
                    import traceback
                    traceback.print_exc()
            
            print("🎉 Inicialização concluída com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro durante inicialização: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_render_database()
    if success:
        print("✅ BANCO DE DADOS INICIALIZADO COM SUCESSO!")
    else:
        print("❌ FALHA NA INICIALIZAÇÃO DO BANCO DE DADOS!")
        sys.exit(1)