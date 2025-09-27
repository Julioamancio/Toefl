#!/usr/bin/env python3
"""
Script para forçar recriação completa do banco de dados
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def force_recreate_database():
    """Força a recriação completa do banco de dados"""
    
    # Importar após configurar o path
    from app import app, db
    from models import User, Student, Class
    
    with app.app_context():
        print("=== FORÇANDO RECRIAÇÃO COMPLETA DO BANCO ===")
        
        # Remover bancos existentes
        db_paths = ['toefl.db', 'toefl_dashboard.db']
        for db_path in db_paths:
            if os.path.exists(db_path):
                print(f"Removendo banco existente: {db_path}")
                os.remove(db_path)
        
        # Dropar todas as tabelas se existirem
        print("Dropando todas as tabelas...")
        db.drop_all()
        
        # Criar todas as tabelas novamente
        print("Criando todas as tabelas...")
        db.create_all()
        
        # Verificar se as tabelas foram criadas
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tabelas criadas: {tables}")
        
        # Verificar estrutura da tabela students
        if 'students' in tables:
            columns = inspector.get_columns('students')
            print("Colunas da tabela students:")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
        
        # Criar dados iniciais
        create_initial_data()
        
        print("=== RECRIAÇÃO COMPLETA FINALIZADA ===")

def create_initial_data():
    """Cria dados iniciais"""
    from app import db
    from models import User, Class, seed_teachers
    
    # Criar usuário admin
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@toefl.local',
            is_admin=True,
            is_active=True,
            created_at=datetime.utcnow()
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("Usuário admin criado!")
    
    # Criar usuário professor
    professor = User.query.filter_by(username='professor').first()
    if not professor:
        professor = User(
            username='professor',
            email='professor@toefl.local',
            is_admin=False,
            is_active=True,
            created_at=datetime.utcnow()
        )
        professor.set_password('professor123')
        db.session.add(professor)
        print("Usuário professor criado!")
    
    # Criar turmas padrão
    default_classes = [
        {'name': 'Turma A', 'description': 'Turma de nível iniciante'},
        {'name': 'Turma B', 'description': 'Turma de nível intermediário'},
        {'name': 'Turma C', 'description': 'Turma de nível avançado'}
    ]
    
    for class_data in default_classes:
        existing_class = Class.query.filter_by(name=class_data['name']).first()
        if not existing_class:
            new_class = Class(
                name=class_data['name'],
                description=class_data['description'],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(new_class)
            print(f"Turma '{class_data['name']}' criada!")
    
    # Salvar todas as mudanças
    db.session.commit()
    
    # Criar professores
    seed_teachers()
    
    # Criar usuários para os professores
    from models import seed_teacher_users
    seed_teacher_users()
    
    print("Dados iniciais criados com sucesso!")

if __name__ == "__main__":
    force_recreate_database()