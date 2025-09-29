#!/usr/bin/env python3
"""
Script para migrar o banco de dados - adicionar coluna certificate_date
"""

import sqlite3
import os

def migrate_database():
    """Adiciona a coluna certificate_date à tabela student_certificate_layouts"""
    
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
            print("✅ Coluna certificate_date já existe na tabela")
            return True
        
        # Adicionar a coluna
        print("🔧 Adicionando coluna certificate_date...")
        cursor.execute("ALTER TABLE student_certificate_layouts ADD COLUMN certificate_date TEXT")
        
        # Confirmar mudanças
        conn.commit()
        
        # Verificar se foi adicionada
        cursor.execute("PRAGMA table_info(student_certificate_layouts)")
        columns_after = [column[1] for column in cursor.fetchall()]
        
        if 'certificate_date' in columns_after:
            print("✅ Coluna certificate_date adicionada com sucesso!")
            return True
        else:
            print("❌ Falha ao adicionar coluna certificate_date")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante migração: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando migração do banco de dados...")
    success = migrate_database()
    
    if success:
        print("🎉 Migração concluída com sucesso!")
    else:
        print("💥 Migração falhou!")