#!/usr/bin/env python3
"""
Script para inicializar o banco de dados SQLite local
"""

import os
import sys

# Definir DATABASE_URL para SQLite local
os.environ['DATABASE_URL'] = 'sqlite:///toefl_dashboard.db'

from app import create_app
from models import db

def init_database():
    """Inicializa o banco de dados SQLite"""
    try:
        print("🚀 Inicializando banco de dados SQLite...")
        
        # Criar aplicação
        app, csrf = create_app()
        
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # Verificar se existem tabelas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas criadas: {', '.join(tables)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    if success:
        print("🎉 Banco de dados inicializado com sucesso!")
    else:
        print("💥 Falha na inicialização do banco de dados")
        sys.exit(1)