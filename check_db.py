#!/usr/bin/env python3
"""
Script para verificar a estrutura do banco de dados SQLite
"""

import sqlite3
import os

def check_database():
    """Verifica a estrutura do banco de dados"""
    db_file = 'toefl_dashboard.db'
    
    if not os.path.exists(db_file):
        print(f"❌ Arquivo do banco {db_file} não encontrado!")
        return
    
    print(f"✅ Arquivo do banco {db_file} encontrado")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Listar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📋 Tabelas no banco ({len(tables)} encontradas):")
        for table in tables:
            table_name = table[0]
            print(f"  - {table_name}")
            
            # Contar registros em cada tabela
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"    └─ {count} registros")
                
                # Se for tabela de estudantes, mostrar alguns exemplos
                if 'student' in table_name.lower():
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    if rows:
                        print(f"    └─ Primeiros registros:")
                        for row in rows:
                            print(f"       {row}")
                            
            except Exception as e:
                print(f"    └─ Erro ao contar: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao acessar banco: {e}")

if __name__ == '__main__':
    check_database()