#!/usr/bin/env python3
"""
Script para verificar tabelas no banco de dados
"""

import sqlite3
import os

def check_tables():
    """Verifica quais tabelas existem no banco"""
    
    db_path = 'toefl_dashboard.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Listar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Tabelas encontradas no banco ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
            
        # Verificar especificamente a tabela student_certificate_layouts
        if 'student_certificate_layouts' in tables:
            print(f"\n🔍 Estrutura da tabela student_certificate_layouts:")
            cursor.execute("PRAGMA table_info(student_certificate_layouts)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print(f"\n❌ Tabela student_certificate_layouts não encontrada")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_tables()