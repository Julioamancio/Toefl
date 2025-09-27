#!/usr/bin/env python3
"""
Script para inicializar o banco de dados em produção
"""
import os
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

def init_production_db():
    """Inicializa o banco de dados em produção"""
    
    # Criar aplicação em modo produção
    app = create_app('production')
    
    with app.app_context():
        # Criar todas as tabelas
        print("Criando tabelas do banco de dados...")
        db.create_all()
        
        # Verificar se já existe um usuário admin
        admin_user = User.query.filter_by(username='admin').first()
        
        if not admin_user:
            # Criar usuário admin padrão
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_user = User(
                username='admin',
                email='admin@toefl.com',
                is_admin=True,
                is_active=True
            )
            admin_user.set_password(admin_password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"Usuário admin criado com sucesso!")
            print(f"Username: admin")
            print(f"Password: {admin_password}")
        else:
            print("Usuário admin já existe.")
        
        print("Inicialização do banco de dados concluída!")

if __name__ == '__main__':
    init_production_db()