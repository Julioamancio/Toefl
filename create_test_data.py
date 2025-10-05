#!/usr/bin/env python3
"""
Script para criar dados de teste no banco de dados
"""

import sqlite3
from datetime import datetime

def create_test_data():
    """Cria dados de teste no banco"""
    try:
        conn = sqlite3.connect('toefl_dashboard.db')
        cursor = conn.cursor()
        
        # Verificar se já existem estudantes
        cursor.execute("SELECT COUNT(*) FROM students")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"✅ Já existem {existing_count} estudantes no banco")
            # Mostrar alguns exemplos
            cursor.execute("SELECT id, name, student_number FROM students LIMIT 5")
            students = cursor.fetchall()
            print("📋 Estudantes existentes:")
            for student in students:
                print(f"   ID: {student[0]} | Nome: {student[1]} | Número: {student[2]}")
        else:
            print("📝 Criando dados de teste...")
            
            # Criar estudantes de teste
            test_students = [
                (497, "João Silva", "2024001", "joao.silva@email.com", "A1", "2024-01-15"),
                (498, "Maria Santos", "2024002", "maria.santos@email.com", "A2", "2024-01-16"),
                (499, "Pedro Costa", "2024003", "pedro.costa@email.com", "B1", "2024-01-17"),
                (500, "Ana Oliveira", "2024004", "ana.oliveira@email.com", "B2", "2024-01-18"),
                (501, "Carlos Lima", "2024005", "carlos.lima@email.com", "C1", "2024-01-19")
            ]
            
            for student_id, name, number, email, level, date in test_students:
                cursor.execute("""
                    INSERT OR REPLACE INTO students 
                    (id, name, student_number, email, level, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, name, number, email, level, date))
            
            conn.commit()
            print(f"✅ {len(test_students)} estudantes de teste criados!")
            
            # Verificar criação
            cursor.execute("SELECT COUNT(*) FROM students")
            total = cursor.fetchone()[0]
            print(f"📊 Total de estudantes no banco: {total}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar dados de teste: {e}")

if __name__ == '__main__':
    create_test_data()