#!/usr/bin/env python3
"""
Script para forçar a criação das tabelas no banco SQLite
"""

import os
import sys
from datetime import datetime

# Definir DATABASE_URL para SQLite local
os.environ['DATABASE_URL'] = 'sqlite:///toefl_dashboard.db'

def force_create_tables():
    """Força a criação de todas as tabelas"""
    
    try:
        print("🚀 Forçando criação das tabelas...")
        
        # Importar modelos e app
        from app import create_app
        from models import db, User, Student, Teacher, Class, ComputedLevel, CertificateLayout, StudentCertificateLayout
        
        # Criar aplicação
        app, csrf = create_app()
        
        with app.app_context():
            # Remover todas as tabelas existentes
            print("🗑️ Removendo tabelas existentes...")
            db.drop_all()
            
            # Criar todas as tabelas novamente
            print("🔧 Criando todas as tabelas...")
            db.create_all()
            
            # Verificar se as tabelas foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✅ Tabelas criadas: {', '.join(tables)}")
            
            # Verificar especificamente a tabela student_certificate_layouts
            if 'student_certificate_layouts' in tables:
                print("✅ Tabela student_certificate_layouts criada com sucesso!")
                
                # Mostrar estrutura da tabela
                columns = inspector.get_columns('student_certificate_layouts')
                print("📋 Colunas da tabela student_certificate_layouts:")
                for col in columns:
                    print(f"  - {col['name']} ({col['type']})")
            else:
                print("❌ Tabela student_certificate_layouts NÃO foi criada!")
                return False
            
            # Criar usuário admin
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
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
            else:
                print("ℹ️ Usuário admin já existe")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_create_tables()
    if success:
        print("🎉 Tabelas criadas com sucesso!")
    else:
        print("💥 Falha na criação das tabelas")
        sys.exit(1)