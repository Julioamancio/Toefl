#!/usr/bin/env python3
"""
Script para testar conexão com PostgreSQL do Render
"""
import os
import sys
from config import ProductionConfig
from sqlalchemy import create_engine, text

def test_database_connection():
    """Testa a conexão com o banco de dados"""
    
    # Definir a URL do banco com as credenciais corretas
    database_url = "postgresql://toefl_db_user:qdC4Is0UOswCI8pGNNptXTT3PhlFsK8o@dpg-d39tj33ipnbc73b66rfg-a.oregon-postgres.render.com/toefl_db"
    os.environ['DATABASE_URL'] = database_url
    
    print('🔍 TESTANDO CONEXÃO COM CREDENCIAIS CORRETAS...')
    print()
    
    try:
        # Usar configuração de produção
        config = ProductionConfig()
        final_url = config.SQLALCHEMY_DATABASE_URI
        
        print(f'📊 URL original: {database_url[:60]}...')
        print(f'📊 URL processada: {final_url[:60]}...')
        print()
        
        # Criar engine com as configurações otimizadas
        engine = create_engine(final_url, **config.SQLALCHEMY_ENGINE_OPTIONS)
        
        # Testar conexão
        print('🔌 Tentando conectar...')
        with engine.connect() as conn:
            # Testar versão do PostgreSQL
            result = conn.execute(text('SELECT version();'))
            version = result.fetchone()[0]
            print('✅ CONEXÃO ESTABELECIDA COM SUCESSO!')
            print(f'📋 Versão PostgreSQL: {version[:80]}...')
            print()
            
            # Testar se as tabelas existem
            print('📊 Verificando tabelas existentes...')
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f'📊 Tabelas encontradas: {len(tables)}')
            
            if tables:
                print('   Tabelas:')
                for table in tables[:10]:  # Mostrar até 10 tabelas
                    print(f'   - {table}')
                if len(tables) > 10:
                    print(f'   ... e mais {len(tables) - 10} tabelas')
            else:
                print('   ⚠️  Nenhuma tabela encontrada (banco vazio)')
            
            print()
            print('🎉 BANCO DE DADOS FUNCIONANDO PERFEITAMENTE!')
            return True
            
    except Exception as e:
        print(f'❌ ERRO NA CONEXÃO: {e}')
        print(f'🔧 Tipo do erro: {type(e).__name__}')
        return False

if __name__ == '__main__':
    success = test_database_connection()
    sys.exit(0 if success else 1)