#!/usr/bin/env python3
"""
Script para inicializar o banco de dados e criar dados iniciais
Compatível com desenvolvimento (SQLite) e produção (PostgreSQL)
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from models import db, User, Class

def init_database():
    """Inicializa o banco de dados criando todas as tabelas de forma segura"""
    # Determinar o ambiente
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    with app.app_context():
        try:
            from sqlalchemy import inspect
            
            # Verificar se as tabelas já existem para evitar condição de corrida
            insp = inspect(db.engine)
            
            if not insp.has_table("classes"):
                print("🔧 Criando tabelas do banco de dados...")
                
                # Para desenvolvimento, remover bancos SQLite existentes se necessário
                if config_name == 'development':
                    db_paths = ['toefl.db', 'toefl_dashboard.db']
                    for db_path in db_paths:
                        if os.path.exists(db_path):
                            print(f"Removendo banco de dados existente: {db_path}")
                            os.remove(db_path)
                
                # Criar todas as tabelas
                db.create_all()
                print("✅ Tabelas criadas com sucesso!")
            else:
                print("ℹ️  Tabelas já existem, nada a fazer.")
            
            # Verificar se as tabelas foram criadas (para debug)
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas encontradas: {tables}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inicializar banco de dados: {e}")
            return False

def create_admin_user():
    """Cria o usuário administrador padrão"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    with app.app_context():
        try:
            # Verificar se já existe um admin
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print("Usuário admin já existe!")
                return True
            
            # Criar usuário admin
            admin = User(
                username='admin',
                email='admin@toefl.local',
                is_admin=True,
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado com sucesso!")
            print("Username: admin")
            print("Password: admin123")
            
            return True
            
        except Exception as e:
            print(f"Erro ao criar usuário admin: {e}")
            db.session.rollback()
            return False

def create_sample_classes():
    """Cria turmas de exemplo"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    with app.app_context():
        try:
            # Verificar se já existem turmas
            if Class.query.count() > 0:
                print("Turmas já existem no banco de dados!")
                return True
            
            sample_classes = [
                {
                    'name': 'Inglês Básico 2024.1',
                    'description': 'Turma de inglês básico para iniciantes - Primeiro semestre de 2024'
                },
                {
                    'name': 'Inglês Intermediário 2024.1',
                    'description': 'Turma de inglês intermediário - Primeiro semestre de 2024'
                },
                {
                    'name': 'Inglês Avançado 2024.1',
                    'description': 'Turma de inglês avançado - Primeiro semestre de 2024'
                },
                {
                    'name': 'Preparatório TOEFL 2024.1',
                    'description': 'Curso preparatório para o exame TOEFL Junior'
                }
            ]
            
            for class_data in sample_classes:
                new_class = Class(
                    name=class_data['name'],
                    description=class_data['description'],
                    created_at=datetime.utcnow()
                )
                db.session.add(new_class)
            
            db.session.commit()
            print(f"Criadas {len(sample_classes)} turmas de exemplo!")
            return True
            
        except Exception as e:
            print(f"Erro ao criar turmas de exemplo: {e}")
            db.session.rollback()
            return False

def create_sample_user():
    """Cria um usuário de exemplo (não admin)"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    with app.app_context():
        try:
            # Verificar se já existe
            user = User.query.filter_by(username='professor').first()
            if user:
                print("Usuário professor já existe!")
                return True
            
            # Criar usuário professor
            professor = User(
                username='professor',
                email='professor@toefl.local',
                is_admin=False,
                is_active=True,
                created_at=datetime.utcnow()
            )
            professor.set_password('professor123')
            
            db.session.add(professor)
            db.session.commit()
            
            print("Usuário professor criado:")
            print("  Username: professor")
            print("  Password: professor123")
            print("  Email: professor@toefl.local")
            return True
            
        except Exception as e:
            print(f"Erro ao criar usuário professor: {e}")
            db.session.rollback()
            return False

def main():
    """Função principal"""
    print("=" * 50)
    print("INICIALIZANDO BANCO DE DADOS TOEFL DASHBOARD")
    print("=" * 50)
    
    success = True
    
    try:
        # Inicializar banco
        print("1. Inicializando banco de dados...")
        if not init_database():
            success = False
        
        # Criar dados iniciais apenas em desenvolvimento
        config_name = os.environ.get('FLASK_ENV', 'development')
        if config_name == 'development':
            print("\n2. Criando dados iniciais...")
            if not create_admin_user():
                success = False
            if not create_sample_user():
                success = False
            if not create_sample_classes():
                success = False
        else:
            print("\n2. Criando usuário admin para produção...")
            if not create_admin_user():
                success = False
        
        print("\n" + "=" * 50)
        if success:
            print("INICIALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        else:
            print("INICIALIZAÇÃO CONCLUÍDA COM ALGUNS ERROS!")
        print("=" * 50)
        
        return success
        
    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")
        print("=" * 50)
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("INICIALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 50)
        print("\nPara iniciar a aplicação, execute:")
        print("  python app.py")
        print("\nOu use o comando make:")
        print("  make run")
        print("\nAcesse: http://localhost:5000")
        print("\nCredenciais de acesso:")
        print("  Admin: admin / admin123")
        print("  Professor: professor / professor123")
    sys.exit(0 if success else 1)
    exit(main())