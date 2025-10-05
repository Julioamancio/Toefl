#!/usr/bin/env python3
"""
Script para restaurar backup e corrigir o banco de dados
"""

import os
import sys
import json
from datetime import datetime

# Definir DATABASE_URL para SQLite local
os.environ['DATABASE_URL'] = 'sqlite:///toefl_dashboard.db'

def restore_from_backup():
    """Restaura dados do backup mais recente"""
    
    try:
        print("🔄 Iniciando restauração do backup...")
        
        # Importar modelos e app
        from app import create_app
        from models import db, User, Student, Teacher, Class, ComputedLevel
        from database_backup import import_data_json
        
        # Criar aplicação
        app, csrf = create_app()
        
        with app.app_context():
            print("🗑️ Removendo dados existentes...")
            # Limpar tabelas existentes
            db.drop_all()
            
            print("🔧 Criando tabelas...")
            # Criar todas as tabelas
            db.create_all()
            
            # Verificar se as tabelas foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Tabelas criadas: {', '.join(tables)}")
            
            # Criar usuário admin
            print("👤 Criando usuário admin...")
            admin = User(
                username='admin',
                email='admin@toefl.com',
                is_admin=True,
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado!")
            
            # Restaurar dados do backup
            backup_file = 'backups/export_20250928_085940.json'
            if os.path.exists(backup_file):
                print(f"📂 Restaurando dados de {backup_file}...")
                
                # Importar dados usando a função existente
                try:
                    import_data_json(backup_file)
                    print("✅ Backup restaurado com sucesso!")
                    success = True
                except Exception as e:
                    print(f"❌ Erro na importação: {e}")
                    success = False
                
                if success:
                    # Verificar dados restaurados
                    student_count = Student.query.count()
                    teacher_count = Teacher.query.count()
                    class_count = Class.query.count()
                    
                    print(f"📊 Dados restaurados:")
                    print(f"  - Estudantes: {student_count}")
                    print(f"  - Professores: {teacher_count}")
                    print(f"  - Turmas: {class_count}")
                    
                    return True
                else:
                    return False
            else:
                print(f"❌ Arquivo de backup não encontrado: {backup_file}")
                return False
                
    except Exception as e:
        print(f"❌ Erro na restauração: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_system():
    """Testa se o sistema está funcionando após a restauração"""
    
    try:
        print("🧪 Testando sistema após restauração...")
        
        from app import create_app
        from models import db, Student, Teacher, Class
        
        app, csrf = create_app()
        
        with app.app_context():
            # Verificar se há dados
            student_count = Student.query.count()
            teacher_count = Teacher.query.count()
            class_count = Class.query.count()
            
            print(f"📊 Status atual:")
            print(f"  - Estudantes: {student_count}")
            print(f"  - Professores: {teacher_count}")
            print(f"  - Turmas: {class_count}")
            
            if student_count > 0:
                print("✅ Sistema restaurado e funcionando!")
                return True
            else:
                print("⚠️ Sistema restaurado mas sem dados de estudantes")
                return False
                
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Iniciando processo de restauração...")
    
    # Restaurar backup
    if restore_from_backup():
        # Testar sistema
        if test_system():
            print("🎉 Restauração concluída com sucesso!")
            return True
        else:
            print("⚠️ Restauração parcial - verificar dados")
            return False
    else:
        print("💥 Falha na restauração")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)