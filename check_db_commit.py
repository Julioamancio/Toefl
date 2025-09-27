#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Student
from listening_csa import compute_listening_csa

def check_and_fix_db():
    with app.app_context():
        # Buscar estudante Abdala Victor
        student = Student.query.filter_by(name='Abdala Victor').first()
        
        if not student:
            print("Estudante não encontrado")
            return
            
        print(f"Nome: {student.name}")
        print(f"Listening Score: {student.listening}")
        print(f"CSA Atual (antes): {student.listening_csa_points}")
        
        if student.class_info and student.class_info.meta_label and student.listening:
            # Calcular CSA correto
            csa_result = compute_listening_csa(student.class_info.meta_label, student.listening)
            expected_csa = csa_result['points']
            
            print(f"CSA Esperado: {expected_csa}")
            
            # Atualizar manualmente
            student.listening_csa_points = expected_csa
            
            try:
                db.session.commit()
                print(f"CSA atualizado com sucesso para: {expected_csa}")
                
                # Verificar se foi salvo
                db.session.refresh(student)
                print(f"CSA Atual (depois): {student.listening_csa_points}")
                
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao salvar: {e}")

if __name__ == '__main__':
    check_and_fix_db()