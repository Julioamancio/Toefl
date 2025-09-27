#!/usr/bin/env python3
"""
Script para criar usuário admin no banco de dados
"""
import os
import sys
from werkzeug.security import generate_password_hash

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def create_admin_user():
    """Cria o usuário admin se não existir"""
    with app.app_context():
        try:
            # Verificar se o usuário admin já existe
            admin_user = User.query.filter_by(username='admin').first()
            
            if admin_user:
                print("✅ Usuário admin já existe!")
                print(f"   Username: {admin_user.username}")
                print(f"   Ativo: {admin_user.is_active}")
                return True
            
            # Criar usuário admin
            admin_password = 'admin123'
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash(admin_password),
                is_active=True
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Usuário admin criado com sucesso!")
            print(f"   Username: admin")
            print(f"   Password: {admin_password}")
            print(f"   Ativo: True")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário admin: {e}")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("CRIANDO USUÁRIO ADMIN")
    print("=" * 50)
    
    success = create_admin_user()
    
    if success:
        print("\n✅ Processo concluído com sucesso!")
        print("\nCredenciais de acesso:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nAcesse: http://127.0.0.1:5000/login")
    else:
        print("\n❌ Processo falhou!")
        sys.exit(1)