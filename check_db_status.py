#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar o status do banco de dados
"""

import sqlite3
import os

def check_database_status():
    """Verifica o status do banco de dados"""
    
    db_file = 'toefl_database.db'
    
    if not os.path.exists(db_file):
        print(f"❌ Arquivo de banco de dados '{db_file}' não encontrado!")
        return
    
    print(f"✓ Arquivo de banco de dados '{db_file}' encontrado")
    print(f"  Tamanho: {os.path.getsize(db_file)} bytes")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Listar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Tabelas encontradas: {tables}")
        
        # Verificar cada tabela
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} registros")
        
        # Verificar estudantes com listening_score
        if 'students' in tables:
            cursor.execute("SELECT COUNT(*) FROM students WHERE listening_score IS NOT NULL")
            listening_count = cursor.fetchone()[0]
            print(f"\n🎧 Estudantes com Listening score: {listening_count}")
            
            if listening_count > 0:
                cursor.execute("""
                SELECT s.name, s.listening_score, c.meta_label, s.grade_listening
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE s.listening_score IS NOT NULL
                LIMIT 5
                """)
                examples = cursor.fetchall()
                
                print("\n📊 Exemplos de estudantes:")
                print("Nome                 Score  Label  Nota")
                print("-" * 45)
                for example in examples:
                    name, score, meta_label, grade = example
                    name_short = name[:20] if len(name) > 20 else name
                    print(f"{name_short:<20} {score:<6} {meta_label:<6} {grade}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    check_database_status()