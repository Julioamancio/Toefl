"""
Script para adicionar coluna listening_csa_points ao banco de dados SQLite existente
"""

import sqlite3
import os
from app import app
from models import db, Student
from listening_csa import compute_listening_csa

def add_listening_csa_column():
    """
    Adiciona a coluna listening_csa_points ao banco de dados SQLite
    """
    with app.app_context():
        # Obter o caminho do banco de dados
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        
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
            
            conn.commit()
            conn.close()
            
            # Agora calcular os valores usando SQLAlchemy
            print("Calculando valores de listening_csa_points...")
            
            students = Student.query.all()
            print(f"Encontrados {len(students)} estudantes para processar")
            
            updated_count = 0
            
            for student in students:
                try:
                    if student.class_info and student.class_info.meta_label and student.listening is not None:
                        rotulo_escolar = float(student.class_info.meta_label)
                        csa_result = compute_listening_csa(rotulo_escolar, student.listening)
                        student.listening_csa_points = csa_result['points']
                        updated_count += 1
                        
                        if updated_count % 50 == 0:
                            print(f"Processados {updated_count} estudantes...")
                    else:
                        student.listening_csa_points = None
                        
                except Exception as e:
                    print(f"Erro ao processar estudante {student.name}: {e}")
                    student.listening_csa_points = None
            
            # Salvar alterações
            db.session.commit()
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