#!/usr/bin/env python3
"""
Script de migração para adicionar a coluna certificate_date na tabela student_certificate_layouts
"""

import sqlite3
import os
from config import Config

def migrate_certificate_date():
    """Adiciona a coluna certificate_date se ela não existir"""
    
    # Determinar o caminho do banco de dados
    if os.getenv('DATABASE_URL'):
        print("❌ Este script é apenas para SQLite local. Para PostgreSQL, use migrations do Flask-Migrate.")
        return False
    
    # Usar banco SQLite local
    db_path = 'toefl_dashboard.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    try:
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(student_certificate_layouts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'certificate_date' in columns:
            print("✅ Coluna 'certificate_date' já existe na tabela student_certificate_layouts")
            conn.close()
            return True
        
        print("🔧 Adicionando coluna 'certificate_date' na tabela student_certificate_layouts...")
        
        # Adicionar a coluna certificate_date
        cursor.execute("""
            ALTER TABLE student_certificate_layouts 
            ADD COLUMN certificate_date VARCHAR(20)
        """)
        
        # Confirmar as mudanças
        conn.commit()
        
        # Verificar se a coluna foi adicionada
        cursor.execute("PRAGMA table_info(student_certificate_layouts)")
        columns_after = [column[1] for column in cursor.fetchall()]
        
        if 'certificate_date' in columns_after:
            print("✅ Coluna 'certificate_date' adicionada com sucesso!")
            
            # Mostrar estrutura da tabela atualizada
            print("\n📋 Estrutura atual da tabela student_certificate_layouts:")
            for column_info in cursor.fetchall():
                print(f"   - {column_info[1]} ({column_info[2]})")
            
            conn.close()
            return True
        else:
            print("❌ Falha ao adicionar a coluna 'certificate_date'")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Erro ao executar migração: {e}")
        if 'conn' in locals():
            conn.close()
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    print("🚀 Iniciando migração da coluna certificate_date...")
    success = migrate_certificate_date()
    
    if success:
        print("\n✅ Migração concluída com sucesso!")
        print("🔄 Reinicie o servidor Flask para aplicar as mudanças.")
    else:
        print("\n❌ Migração falhou. Verifique os logs acima.")