#!/usr/bin/env python3
"""
Script para recalcular listening_csa_points para todos os estudantes existentes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Student
from listening_csa import compute_listening_csa

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
                        old_value = student.listening_csa_points
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
    print("Iniciando recálculo de listening_csa_points...")
    success = recalculate_all_listening_csa()
    if success:
        print("Recálculo concluído com sucesso!")
    else:
        print("Falha no recálculo!")
        sys.exit(1)