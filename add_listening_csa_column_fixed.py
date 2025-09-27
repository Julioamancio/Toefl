"""
Script para adicionar coluna listening_csa_points ao banco de dados SQLite existente
"""

import sqlite3
import os
from listening_csa import compute_listening_csa

def add_listening_csa_column():
    """
    Adiciona a coluna listening_csa_points ao banco de dados SQLite
    """
    # Caminho do banco de dados
    db_path = 'toefl_dashboard.db'
    
    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado: {db_path}")
        return False
        
    print(f"Conectando ao banco de dados: {db_path}")
    
    try:
        # Conectar diretamente ao SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(students)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'listening_csa_points' in columns:
            print("✓ Coluna listening_csa_points já existe")
        else:
            # Adicionar a coluna
            cursor.execute("ALTER TABLE students ADD COLUMN listening_csa_points REAL")
            print("✓ Coluna listening_csa_points adicionada")
        
        # Buscar estudantes com dados necessários
        cursor.execute("""
            SELECT s.id, s.listening, c.meta_label 
            FROM students s 
            LEFT JOIN classes c ON s.class_id = c.id 
            WHERE s.listening IS NOT NULL AND c.meta_label IS NOT NULL
        """)
        
        students_data = cursor.fetchall()
        print(f"Encontrados {len(students_data)} estudantes com dados completos")
        
        updated_count = 0
        
        for student_id, listening_score, meta_label in students_data:
            try:
                rotulo_escolar = float(meta_label)
                csa_result = compute_listening_csa(rotulo_escolar, listening_score)
                
                cursor.execute(
                    "UPDATE students SET listening_csa_points = ? WHERE id = ?",
                    (csa_result['points'], student_id)
                )
                updated_count += 1
                
                if updated_count % 50 == 0:
                    print(f"Processados {updated_count} estudantes...")
                    
            except Exception as e:
                print(f"Erro ao processar estudante ID {student_id}: {e}")
        
        # Definir NULL para estudantes sem dados suficientes
        cursor.execute("""
            UPDATE students 
            SET listening_csa_points = NULL 
            WHERE listening IS NULL OR class_id IS NULL OR 
                  class_id NOT IN (SELECT id FROM classes WHERE meta_label IS NOT NULL)
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✓ {updated_count} estudantes atualizados com listening_csa_points")
        
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    success = add_listening_csa_column()
    if success:
        print("\n🎉 Coluna listening_csa_points adicionada e valores calculados com sucesso!")
    else:
        print("\n❌ Falha ao adicionar coluna listening_csa_points")