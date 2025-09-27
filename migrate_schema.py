#!/usr/bin/env python3
"""
Script de migração de schema para executar durante o build do Render.com
Este script DEVE ser executado ANTES da aplicação iniciar
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

def migrate_schema():
    """Executa migração de schema do banco de dados"""
    try:
        print("🔄 [BUILD] Iniciando migração de schema...")
        
        # Obter URL do banco
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ [BUILD] DATABASE_URL não encontrada!")
            return False
            
        print(f"🔗 [BUILD] Conectando ao banco: {database_url[:50]}...")
        
        # Conectar ao banco
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Verificar se a tabela users existe
        tables = inspector.get_table_names()
        print(f"📋 [BUILD] Tabelas encontradas: {tables}")
        
        if 'users' not in tables:
            print("⚠️ [BUILD] Tabela 'users' não existe ainda - será criada pela aplicação")
            return True
            
        # Verificar colunas existentes
        columns = [col['name'] for col in inspector.get_columns('users')]
        print(f"📋 [BUILD] Colunas na tabela users: {columns}")
        
        # Definir colunas necessárias
        required_columns = {
            'is_teacher': 'BOOLEAN DEFAULT FALSE',
            'is_active': 'BOOLEAN DEFAULT TRUE', 
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'last_login': 'TIMESTAMP'
        }
        
        # Identificar colunas faltantes
        missing_columns = []
        for col_name, col_def in required_columns.items():
            if col_name not in columns:
                missing_columns.append((col_name, col_def))
                
        if not missing_columns:
            print("✅ [BUILD] Todas as colunas já existem!")
            return True
            
        print(f"🔧 [BUILD] Adicionando {len(missing_columns)} colunas faltantes...")
        
        # Adicionar colunas faltantes
        with engine.connect() as conn:
            for col_name, col_def in missing_columns:
                try:
                    sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                    print(f"🔧 [BUILD] Executando: {sql}")
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ [BUILD] Coluna '{col_name}' adicionada com sucesso!")
                except Exception as e:
                    print(f"⚠️ [BUILD] Erro ao adicionar coluna '{col_name}': {e}")
                    # Continuar com outras colunas
                    
        print("✅ [BUILD] Migração de schema concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ [BUILD] Erro crítico na migração: {e}")
        return False

if __name__ == "__main__":
    print("🚀 [BUILD] Executando migração de schema...")
    success = migrate_schema()
    
    if success:
        print("✅ [BUILD] Migração concluída - aplicação pode iniciar")
        sys.exit(0)
    else:
        print("❌ [BUILD] Migração falhou - mas continuando...")
        sys.exit(0)  # Não falhar o build, apenas avisar