#!/usr/bin/env python3
"""
Script para verificar dados dos estudantes
"""

from models import Student, ComputedLevel, db
from app import app

def check_student_data():
    """Verifica os dados dos estudantes no banco"""
    with app.app_context():
        total_students = Student.query.count()
        print(f"=== VERIFICAÇÃO DE DADOS DOS ESTUDANTES ===")
        print(f"Total de estudantes: {total_students}")
        
        if total_students == 0:
            print("❌ Nenhum estudante encontrado no banco!")
            return
        
        # Pegar alguns estudantes para análise
        students = Student.query.limit(10).all()
        
        print("\n=== AMOSTRA DE ESTUDANTES ===")
        print("Nome | Listening | ListCEFR | Reading | ReadCEFR | LFM | LFMCEFR | Total | CEFR_Geral")
        print("-" * 100)
        
        for student in students:
            listening = student.listening or 'N/A'
            list_cefr = student.list_cefr or 'N/A'
            reading = student.reading or 'N/A'
            read_cefr = student.read_cefr or 'N/A'
            lfm = student.lfm or 'N/A'
            lfm_cefr = student.lfm_cefr or 'N/A'
            total = student.total or 'N/A'
            cefr_geral = student.cefr_geral or 'N/A'
            
            print(f"{student.name[:15]:<15} | {listening:<9} | {list_cefr:<8} | {reading:<7} | {read_cefr:<8} | {lfm:<3} | {lfm_cefr:<7} | {total:<5} | {cefr_geral}")
        
        # Verificar campos nulos
        print("\n=== ANÁLISE DE CAMPOS NULOS ===")
        null_listening = Student.query.filter(Student.listening.is_(None)).count()
        null_list_cefr = Student.query.filter(Student.list_cefr.is_(None)).count()
        null_reading = Student.query.filter(Student.reading.is_(None)).count()
        null_read_cefr = Student.query.filter(Student.read_cefr.is_(None)).count()
        null_lfm = Student.query.filter(Student.lfm.is_(None)).count()
        null_lfm_cefr = Student.query.filter(Student.lfm_cefr.is_(None)).count()
        null_total = Student.query.filter(Student.total.is_(None)).count()
        null_cefr_geral = Student.query.filter(Student.cefr_geral.is_(None)).count()
        
        print(f"Listening nulo: {null_listening}/{total_students}")
        print(f"ListCEFR nulo: {null_list_cefr}/{total_students}")
        print(f"Reading nulo: {null_reading}/{total_students}")
        print(f"ReadCEFR nulo: {null_read_cefr}/{total_students}")
        print(f"LFM nulo: {null_lfm}/{total_students}")
        print(f"LFMCEFR nulo: {null_lfm_cefr}/{total_students}")
        print(f"Total nulo: {null_total}/{total_students}")
        print(f"CEFR_Geral nulo: {null_cefr_geral}/{total_students}")
        
        # Verificar ComputedLevel
        print("\n=== VERIFICAÇÃO DE COMPUTED LEVELS ===")
        total_computed = ComputedLevel.query.count()
        print(f"Total de ComputedLevels: {total_computed}")
        
        if total_computed > 0:
            computed_samples = ComputedLevel.query.limit(5).all()
            print("Estudante | Overall Level")
            print("-" * 30)
            for cl in computed_samples:
                student_name = cl.student.name if cl.student else 'N/A'
                print(f"{student_name[:15]:<15} | {cl.overall_level}")

if __name__ == '__main__':
    check_student_data()