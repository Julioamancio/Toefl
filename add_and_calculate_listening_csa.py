#!/usr/bin/env python3
"""
Script para adicionar coluna listening_csa_points e recalcular valores para todos os estudantes
"""

import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Student
from listening_csa import compute_listening_csa

def add_listening_csa_column():
    """Adiciona a coluna listening_csa_points se não existir"""
    try:
        # Usar a configuração do Flask para obter o caminho do banco
        with app.app_context():
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
            else:
                print("Este script funciona apenas com SQLite")
                return False
            
            # Conectar diretamente ao SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar se a coluna já existe
            cursor.execute("PRAGMA table_info(students)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'listening_csa_points' not in columns:
                print("Adicionando coluna listening_csa_points...")
                cursor.execute("ALTER TABLE students ADD COLUMN listening_csa_points INTEGER")
                conn.commit()
                print("Coluna listening_csa_points adicionada com sucesso!")
            else:
                print("Coluna listening_csa_points já existe.")
            
            conn.close()
            return True
        
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
        return False

def recalculate_all_listening_csa():
    """Recalcula listening_csa_points para todos os estudantes"""
    with app.app_context():
        try:
            # Buscar todos os estudantes
            students = Student.query.all()
            updated_count = 0
            skipped_count = 0
            
            print(f"Encontrados {len(students)} estudantes para processar...")
            
            for student in students:
                try:
                    # Verificar se temos os dados necessários
                    if student.class_info and student.class_info.meta_label and student.listening is not None:
                        rotulo_escolar = float(student.class_info.meta_label)
                        csa_result = compute_listening_csa(rotulo_escolar, student.listening)
                        
                        # Atualizar o campo listening_csa_points
                        old_value = getattr(student, 'listening_csa_points', None)
                        student.listening_csa_points = csa_result['points']
                        
                        print(f"Estudante {student.name} (ID: {student.id}): {old_value} -> {csa_result['points']}")
                        updated_count += 1
                    else:
                        print(f"Estudante {student.name} (ID: {student.id}): dados insuficientes - pulando")
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"Erro ao processar estudante {student.name} (ID: {student.id}): {e}")
                    skipped_count += 1
            
            # Salvar todas as alterações
            db.session.commit()
            
            print(f"\nRecálculo concluído!")
            print(f"- Estudantes atualizados: {updated_count}")
            print(f"- Estudantes pulados: {skipped_count}")
            print(f"- Total processado: {len(students)}")
            
        except Exception as e:
            print(f"Erro durante o recálculo: {e}")
            db.session.rollback()
            return False
            
    return True

if __name__ == "__main__":
    print("Iniciando processo de adição de coluna e recálculo...")
    
    # Primeiro, adicionar a coluna
    if not add_listening_csa_column():
        print("Falha ao adicionar coluna!")
        sys.exit(1)
    
    # Depois, recalcular os valores
    print("\nIniciando recálculo de listening_csa_points...")
    success = recalculate_all_listening_csa()
    if success:
        print("Processo concluído com sucesso!")
    else:
        print("Falha no recálculo!")
        sys.exit(1)