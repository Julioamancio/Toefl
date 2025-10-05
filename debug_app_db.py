#!/usr/bin/env python3
"""
Script para verificar qual banco a aplicação Flask está usando e se há dados
"""

import os
import sys

# Definir DATABASE_URL para SQLite local (mesmo que a aplicação usa)
os.environ['DATABASE_URL'] = 'sqlite:///toefl_dashboard.db'

from app import create_app
from models import db, Student

def debug_app_database():
    """Verifica o banco que a aplicação está usando"""
    try:
        print("🔍 DEBUGANDO BANCO DA APLICAÇÃO...")
        
        # Criar aplicação
        app, csrf = create_app()
        
        with app.app_context():
            # Verificar configuração do banco
            print(f"📋 Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            
            # Verificar se há estudantes
            try:
                total_students = Student.query.count()
                print(f"👥 Total de estudantes: {total_students}")
                
                if total_students > 0:
                    # Mostrar alguns estudantes
                    students = Student.query.limit(5).all()
                    print("📝 Primeiros estudantes:")
                    for student in students:
                        print(f"  ID: {student.id}, Nome: {student.name}")
                        print(f"      Listening: {student.listening}, Reading: {student.reading}")
                        print(f"      LFM: {student.lfm}, Total: {student.total}")
                        print()
                else:
                    print("❌ Nenhum estudante encontrado no banco!")
                    
                    # Verificar se as tabelas existem
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    tables = inspector.get_table_names()
                    print(f"📋 Tabelas disponíveis: {tables}")
                    
            except Exception as e:
                print(f"❌ Erro ao consultar estudantes: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar com banco: {e}")
        return False

if __name__ == "__main__":
    success = debug_app_database()
    if not success:
        sys.exit(1)