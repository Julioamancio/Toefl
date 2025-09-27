#!/usr/bin/env python3
"""
Script completo para DELETAR e RECRIAR todas as tabelas no Render.com
Este script garante que as tabelas sejam criadas com o schema correto
"""
import os
import sys
from sqlalchemy import create_engine, text, MetaData

def drop_and_recreate_tables():
    """Deleta todas as tabelas e recria do zero com schema correto"""
    try:
        print("🗑️ [BUILD] Iniciando limpeza completa do banco de dados...")
        
        # Obter URL do banco
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ [BUILD] DATABASE_URL não encontrada!")
            return False
            
        # Corrigir URL para usar psycopg3 em vez de psycopg2
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
            
        print(f"🔗 [BUILD] Conectando ao banco: {database_url[:50]}...")
        
        # Conectar ao banco
        engine = create_engine(database_url)
        
        # Criar metadata para descobrir todas as tabelas
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        print(f"📋 [BUILD] Tabelas encontradas: {list(metadata.tables.keys())}")
        
        # Deletar todas as tabelas existentes
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
            
            # Commit das mudanças
            conn.commit()
        
        print("✅ [BUILD] Todas as tabelas foram deletadas com sucesso!")
        
        # Agora recriar as tabelas com o schema correto
        print("🔧 [BUILD] Recriando tabelas com schema correto...")
        
        # Importar os modelos para criar as tabelas
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from models import db, User, Student, Class, Teacher, ComputedLevel
            print("✅ [BUILD] Modelos importados com sucesso")
            
            # Criar todas as tabelas
            db.metadata.create_all(bind=engine)
            print("✅ [BUILD] Tabelas recriadas com schema correto!")
            
            # Verificar se as tabelas foram criadas corretamente
            metadata_new = MetaData()
            metadata_new.reflect(bind=engine)
            print(f"📋 [BUILD] Tabelas criadas: {list(metadata_new.tables.keys())}")
            
            # Verificar especificamente a tabela users
            if 'users' in metadata_new.tables:
                users_table = metadata_new.tables['users']
                columns = [col.name for col in users_table.columns]
                print(f"👤 [BUILD] Colunas da tabela users: {columns}")
                
                # Verificar se as colunas necessárias existem
                required_columns = ['id', 'username', 'email', 'password_hash', 'is_admin', 'is_teacher', 'is_active', 'created_at', 'last_login']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    print(f"❌ [BUILD] Colunas faltando: {missing_columns}")
                    return False
                else:
                    print("✅ [BUILD] Todas as colunas necessárias estão presentes!")
            
            return True
            
        except Exception as e:
            print(f"❌ [BUILD] Erro ao importar modelos ou criar tabelas: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ [BUILD] Erro geral no script: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 [BUILD] Executando script de migração completa...")
    success = drop_and_recreate_tables()
    if success:
        print("🎉 [BUILD] Migração completa executada com sucesso!")
        sys.exit(0)
    else:
        print("💥 [BUILD] Falha na migração!")
        sys.exit(1)