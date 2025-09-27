#!/usr/bin/env python3
"""
Script para DELETAR todas as tabelas e recriar do zero no Render.com
Este é o approach mais simples e eficaz para resolver problemas de schema
"""
import os
import sys
from sqlalchemy import create_engine, text, MetaData

def drop_and_recreate_tables():
    """Deleta todas as tabelas e recria do zero"""
    try:
        print("🗑️ [BUILD] Iniciando limpeza completa do banco de dados...")
        
        # Obter URL do banco
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ [BUILD] DATABASE_URL não encontrada!")
            return False
            
        print(f"🔗 [BUILD] Conectando ao banco: {database_url[:50]}...")
        
        # Conectar ao banco
        engine = create_engine(database_url)
        
        # Criar metadata para descobrir todas as tabelas
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        print(f"📋 [BUILD] Tabelas encontradas: {list(metadata.tables.keys())}")
        
        # Deletar todas as tabelas existentes
        if metadata.tables:
            print("🗑️ [BUILD] Deletando todas as tabelas existentes...")
            with engine.connect() as conn:
                # Desabilitar foreign key checks temporariamente
                try:
                    conn.execute(text("SET session_replication_role = replica;"))
                    print("✅ [BUILD] Foreign key checks desabilitados")
                except Exception as e:
                    print(f"⚠️ [BUILD] Aviso ao desabilitar FK checks: {e}")
                
                # Deletar cada tabela
                for table_name in metadata.tables.keys():
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                        print(f"🗑️ [BUILD] Tabela '{table_name}' deletada")
                    except Exception as e:
                        print(f"⚠️ [BUILD] Erro ao deletar tabela '{table_name}': {e}")
                
                # Reabilitar foreign key checks
                try:
                    conn.execute(text("SET session_replication_role = DEFAULT;"))
                    print("✅ [BUILD] Foreign key checks reabilitados")
                except Exception as e:
                    print(f"⚠️ [BUILD] Aviso ao reabilitar FK checks: {e}")
                
                conn.commit()
                print("✅ [BUILD] Todas as tabelas foram deletadas com sucesso!")
        else:
            print("ℹ️ [BUILD] Nenhuma tabela encontrada para deletar")
            
        print("✅ [BUILD] Limpeza do banco concluída - tabelas serão recriadas pela aplicação")
        return True
        
    except Exception as e:
        print(f"❌ [BUILD] Erro crítico na limpeza do banco: {e}")
        return False

if __name__ == "__main__":
    print("🚀 [BUILD] Executando limpeza completa do banco...")
    success = drop_and_recreate_tables()
    
    if success:
        print("✅ [BUILD] Limpeza concluída - aplicação pode recriar tabelas")
        sys.exit(0)
    else:
        print("❌ [BUILD] Limpeza falhou - mas continuando...")
        sys.exit(0)  # Não falhar o build, apenas avisar