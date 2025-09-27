#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para investigar valores de asterisco (*) no campo List_CEFR
"""

from app import app, db
from models import Student

def check_asterisk_values():
    """Verifica valores de asterisco no List_CEFR"""
    
    with app.app_context():
        print("=== INVESTIGAÇÃO DE VALORES ASTERISCO (*) ===\n")
        
        # Buscar todos os valores únicos de List_CEFR
        unique_list_cefr = db.session.query(Student.list_cefr).distinct().all()
        print("Valores únicos de List_CEFR:")
        for value in unique_list_cefr:
            print(f"  {repr(value[0])}")
        
        # Contar quantos estudantes têm asterisco
        asterisk_count = Student.query.filter(Student.list_cefr == '*').count()
        print(f"\nEstudantes com List_CEFR = '*': {asterisk_count}")
        
        # Contar total de estudantes
        total_students = Student.query.count()
        print(f"Total de estudantes: {total_students}")
        
        if asterisk_count > 0:
            # Mostrar alguns exemplos
            asterisk_students = Student.query.filter(Student.list_cefr == '*').limit(10).all()
            print("\nExemplos de estudantes com asterisco:")
            print("ID    Nome                 Listening  List_CEFR  Total")
            print("-" * 60)
            for student in asterisk_students:
                name_short = student.name[:20] if student.name else "N/A"
                print(f"{student.id:<5} {name_short:<20} {student.listening or 'N/A':<10} {student.list_cefr or 'N/A':<10} {student.total or 'N/A'}")
        
        # Verificar estudantes com listening score mas List_CEFR como asterisco
        problematic = Student.query.filter(
            Student.listening.isnot(None),
            Student.list_cefr == '*'
        ).all()
        
        if problematic:
            print(f"\n=== ESTUDANTES PROBLEMÁTICOS ===")
            print(f"Estudantes com listening score mas List_CEFR = '*': {len(problematic)}")
            print("\nPrimeiros 10 casos:")
            print("ID    Nome                 Listening  List_CEFR")
            print("-" * 50)
            for student in problematic[:10]:
                name_short = student.name[:20] if student.name else "N/A"
                print(f"{student.id:<5} {name_short:<20} {student.listening:<10} {student.list_cefr}")
        
        # Verificar estudantes sem listening score
        no_listening = Student.query.filter(Student.listening.is_(None)).count()
        print(f"\nEstudantes sem listening score: {no_listening}")
        
        # Verificar estudantes com listening score válido
        with_listening = Student.query.filter(Student.listening.isnot(None)).count()
        print(f"Estudantes com listening score: {with_listening}")

if __name__ == "__main__":
    check_asterisk_values()