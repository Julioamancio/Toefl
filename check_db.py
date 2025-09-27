#!/usr/bin/env python3
"""
Script para inspecionar a estrutura do banco de dados
"""

import sqlite3
import os

def check_database_structure():
    """Verifica a estrutura do banco de dados"""
    db_path = 'toefl_dashboard.db'
    
    if not os.path.exists(db_path):
        print(f"Banco de dados {db_path} não encontrado!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tabelas encontradas:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Verificar estrutura da tabela students
    print("\nEstrutura da tabela 'students':")
    try:
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        if columns:
            print("Colunas:")
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - PK: {col[5]}, NOT NULL: {col[3]}")
        else:
            print("  Tabela 'students' não encontrada ou vazia")
    except Exception as e:
        print(f"  Erro ao verificar tabela students: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database_structure()