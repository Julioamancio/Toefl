#!/usr/bin/env python3
"""
Script para criar tabelas e adicionar coluna listening_csa_points usando SQLAlchemy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Student
from listening_csa import compute_listening_csa
from sqlalchemy import text

def create_tables_and_add_column():
    """Cria tabelas e adiciona coluna listening_csa_points"""
    with app.app_context():
        try:
            # Criar todas as tabelas
            print("Criando tabelas...")
            db.create_all()
            print("Tabelas criadas com sucesso!")
            
            # Verificar se a coluna listening_csa_points existe
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('students')]
            
            if 'listening_csa_points' not in columns:
                print("Adicionando coluna listening_csa_points...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE students ADD COLUMN listening_csa_points INTEGER"))
                    conn.commit()
                print("Coluna listening_csa_points adicionada com sucesso!")
            else:
                print("Coluna listening_csa_points já existe.")
            
            return True
            
        except Exception as e:
            print(f"Erro ao criar tabelas/adicionar coluna: {e}")
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
    print("Iniciando processo de criação de tabelas e adição de coluna...")
    
    # Primeiro, criar tabelas e adicionar coluna
    if not create_tables_and_add_column():
        print("Falha ao criar tabelas/adicionar coluna!")
        sys.exit(1)
    
    # Depois, recalcular os valores (se houver estudantes)
    print("\nIniciando recálculo de listening_csa_points...")
    success = recalculate_all_listening_csa()
    if success:
        print("Processo concluído com sucesso!")
    else:
        print("Falha no recálculo!")
        sys.exit(1)