#!/usr/bin/env python3
"""
Script simples para adicionar a coluna is_teacher se ela não existir
Este script é mais seguro para produção do que recriar todas as tabelas
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

def add_missing_columns():
    """Adiciona colunas faltantes sem recriar tabelas"""
    try:
        print("🔧 [MIGRATION] Iniciando migração incremental...")
        
        # Obter URL do banco
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ [MIGRATION] DATABASE_URL não encontrada!")
            return False
            
        # Corrigir URL para usar psycopg3
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
            
        print(f"🔗 [MIGRATION] Conectando ao banco...")
        
        # Conectar ao banco
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Verificar se a tabela users existe
            inspector = inspect(engine)
            if 'users' not in inspector.get_table_names():
                print("❌ [MIGRATION] Tabela 'users' não existe!")
                return False
            
            # Verificar colunas existentes na tabela users
            columns = [col['name'] for col in inspector.get_columns('users')]
            print(f"📋 [MIGRATION] Colunas existentes em users: {columns}")
            
            # Adicionar coluna is_teacher se não existir
            if 'is_teacher' not in columns:
                print("🔧 [MIGRATION] Adicionando coluna is_teacher...")
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_teacher BOOLEAN NOT NULL DEFAULT FALSE"))
                    conn.commit()
                    print("✅ [MIGRATION] Coluna is_teacher adicionada com sucesso!")
                except Exception as e:
                    print(f"❌ [MIGRATION] Erro ao adicionar coluna is_teacher: {e}")
                    conn.rollback()
                    return False
            else:
                print("✅ [MIGRATION] Coluna is_teacher já existe!")
            
            # Verificar outras colunas necessárias
            required_columns = ['id', 'username', 'email', 'password_hash', 'is_admin', 'is_teacher', 'is_active', 'created_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"⚠️ [MIGRATION] Colunas ainda faltando: {missing_columns}")
                # Aqui você pode adicionar lógica para criar outras colunas se necessário
            else:
                print("✅ [MIGRATION] Todas as colunas necessárias estão presentes!")
            
            return True
            
    except Exception as e:
        print(f"❌ [MIGRATION] Erro na migração: {e}")
        return False

if __name__ == "__main__":
    print("🚀 [MIGRATION] Executando migração incremental...")
    success = add_missing_columns()
    if success:
        print("🎉 [MIGRATION] Migração incremental executada com sucesso!")
        sys.exit(0)
    else:
        print("💥 [MIGRATION] Falha na migração!")
        sys.exit(1)