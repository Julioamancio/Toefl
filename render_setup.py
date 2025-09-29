#!/usr/bin/env python3
"""
Script de setup completo para o Render.com
Cria tabelas e importa dados automaticamente
"""

import os
import sys
from app import create_app
from models import db, User
from database_backup import import_data_json
from werkzeug.security import generate_password_hash

def create_tables():
    """Cria todas as tabelas necessárias"""
    try:
        print("📋 Criando tabelas...")
        db.create_all()
        print("✅ Tabelas criadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def create_admin_user():
    """Cria usuário admin se não existir"""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("👤 Criando usuário admin...")
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado")
        else:
            print("ℹ️  Usuário admin já existe")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
        return False

def import_backup_data():
    """Importa dados do backup"""
    try:
        backup_file = 'backups/export_20250928_085940.json'
        
        if not os.path.exists(backup_file):
            print(f"⚠️  Arquivo de backup não encontrado: {backup_file}")
            return True  # Não é erro crítico
        
        print(f"📥 Importando dados de: {backup_file}")
        import_data_json(backup_file)
        print("✅ Dados importados com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao importar dados: {e}")
        return False

def verify_setup():
    """Verifica se o setup foi bem-sucedido"""
    try:
        from models import Student, Teacher, Class
        
        student_count = Student.query.count()
        teacher_count = Teacher.query.count()
        class_count = Class.query.count()
        
        print(f"\n📊 VERIFICAÇÃO FINAL:")
        print(f"   Estudantes: {student_count}")
        print(f"   Professores: {teacher_count}")
        print(f"   Turmas: {class_count}")
        
        if student_count > 0:
            print("✅ Setup concluído com sucesso!")
            return True
        else:
            print("⚠️  Nenhum estudante encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 SETUP COMPLETO DO RENDER.COM")
    print("=" * 50)
    
    # Verificar ambiente
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("✅ DATABASE_URL encontrada")
    else:
        print("⚠️  DATABASE_URL não definida - usando configuração padrão")
    
    try:
        # Criar aplicação (create_app retorna tupla (app, csrf))
        app, csrf = create_app('production')
        
        with app.app_context():
            print("✅ Aplicação Flask criada")
            
            # Executar setup
            steps = [
                ("Criar tabelas", create_tables),
                ("Criar usuário admin", create_admin_user),
                ("Importar dados", import_backup_data),
                ("Verificar setup", verify_setup)
            ]
            
            for step_name, step_func in steps:
                print(f"\n🔄 {step_name}...")
                if not step_func():
                    print(f"❌ Falha em: {step_name}")
                    return 1
            
            print(f"\n🎉 SETUP CONCLUÍDO COM SUCESSO!")
            print(f"   O sistema está pronto para uso no Render.com")
            return 0
            
    except Exception as e:
        print(f"❌ Erro crítico durante setup: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())