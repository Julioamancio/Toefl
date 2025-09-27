#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para investigar o estudante ID 259 que tem CEFR_Geral nulo
"""

from app import app, db
from models import Student

def check_student_259():
    """Investiga o estudante ID 259 com CEFR_Geral nulo"""
    
    with app.app_context():
        print("=== INVESTIGAÇÃO DO ESTUDANTE ID 259 ===\n")
        
        student = Student.query.get(259)
        
        if not student:
            print("❌ Estudante ID 259 não encontrado")
            return
        
        print(f"Nome: {student.name}")
        print(f"ID: {student.id}")
        print()
        
        print("=== PONTUAÇÕES ===")
        print(f"Listening: {student.listening}")
        print(f"Reading: {student.reading}")
        print(f"LFM: {student.lfm}")
        print(f"Total: {student.total}")
        print()
        
        print("=== NÍVEIS CEFR ===")
        print(f"List_CEFR: {student.list_cefr}")
        print(f"Read_CEFR: {student.read_cefr}")
        print(f"LFM_CEFR: {student.lfm_cefr}")
        print(f"CEFR_Geral: {student.cefr_geral}")
        print()
        
        print("=== OUTROS CAMPOS ===")
        print(f"Student Number: {student.student_number}")
        print(f"Class ID: {student.class_id}")
        print(f"Teacher ID: {student.teacher_id}")
        print(f"Lexile: {student.lexile}")
        print(f"Created At: {student.created_at}")
        print(f"Updated At: {student.updated_at}")
        print()
        
        # Verificar se pode calcular o total
        if student.listening and student.reading and student.lfm:
            calculated_total = student.listening + student.reading + student.lfm
            print(f"Total calculado: {calculated_total}")
            
            # Tentar calcular CEFR_Geral
            try:
                calculated_cefr = student.calculate_final_cefr()
                print(f"CEFR_Geral calculado: {calculated_cefr}")
                
                # Atualizar o estudante
                student.total = calculated_total
                student.cefr_geral = calculated_cefr
                
                db.session.commit()
                print("✅ Estudante atualizado com sucesso!")
                
            except Exception as e:
                print(f"❌ Erro ao calcular CEFR_Geral: {e}")
        else:
            print("❌ Não é possível calcular o total - pontuações em falta:")
            if not student.listening:
                print("  - Listening em falta")
            if not student.reading:
                print("  - Reading em falta")
            if not student.lfm:
                print("  - LFM em falta")

if __name__ == "__main__":
    check_student_259()