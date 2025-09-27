#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar se há problemas similares em outros campos CEFR
"""

from app import app, db
from models import Student

def check_other_cefr_fields():
    """Verifica se há problemas em outros campos CEFR"""
    
    with app.app_context():
        print("=== VERIFICAÇÃO DE OUTROS CAMPOS CEFR ===\n")
        
        total_students = Student.query.count()
        print(f"Total de estudantes: {total_students}")
        
        # Verificar Read_CEFR
        print("\n=== READ_CEFR ===")
        unique_read_cefr = db.session.query(Student.read_cefr).distinct().all()
        print("Valores únicos de Read_CEFR:")
        for value in unique_read_cefr:
            count = Student.query.filter(Student.read_cefr == value[0]).count()
            print(f"  {repr(value[0])}: {count} estudantes")
        
        # Verificar se há asteriscos em Read_CEFR
        asterisk_read = Student.query.filter(Student.read_cefr == '*').count()
        if asterisk_read > 0:
            print(f"⚠️  PROBLEMA: {asterisk_read} estudantes com Read_CEFR = '*'")
        
        # Verificar LFM_CEFR
        print("\n=== LFM_CEFR ===")
        unique_lfm_cefr = db.session.query(Student.lfm_cefr).distinct().all()
        print("Valores únicos de LFM_CEFR:")
        for value in unique_lfm_cefr:
            count = Student.query.filter(Student.lfm_cefr == value[0]).count()
            print(f"  {repr(value[0])}: {count} estudantes")
        
        # Verificar se há asteriscos em LFM_CEFR
        asterisk_lfm = Student.query.filter(Student.lfm_cefr == '*').count()
        if asterisk_lfm > 0:
            print(f"⚠️  PROBLEMA: {asterisk_lfm} estudantes com LFM_CEFR = '*'")
        
        # Verificar CEFR_Geral
        print("\n=== CEFR_GERAL ===")
        unique_cefr_geral = db.session.query(Student.cefr_geral).distinct().all()
        print("Valores únicos de CEFR_Geral:")
        for value in unique_cefr_geral:
            count = Student.query.filter(Student.cefr_geral == value[0]).count()
            print(f"  {repr(value[0])}: {count} estudantes")
        
        # Verificar se há asteriscos em CEFR_Geral
        asterisk_geral = Student.query.filter(Student.cefr_geral == '*').count()
        if asterisk_geral > 0:
            print(f"⚠️  PROBLEMA: {asterisk_geral} estudantes com CEFR_Geral = '*'")
        
        # Verificar valores nulos
        print("\n=== VALORES NULOS ===")
        null_list_cefr = Student.query.filter(Student.list_cefr.is_(None)).count()
        null_read_cefr = Student.query.filter(Student.read_cefr.is_(None)).count()
        null_lfm_cefr = Student.query.filter(Student.lfm_cefr.is_(None)).count()
        null_cefr_geral = Student.query.filter(Student.cefr_geral.is_(None)).count()
        
        print(f"List_CEFR nulo: {null_list_cefr}")
        print(f"Read_CEFR nulo: {null_read_cefr}")
        print(f"LFM_CEFR nulo: {null_lfm_cefr}")
        print(f"CEFR_Geral nulo: {null_cefr_geral}")
        
        # Verificar estudantes com scores mas CEFR nulo
        print("\n=== ESTUDANTES COM SCORES MAS CEFR NULO ===")
        
        # Reading score mas Read_CEFR nulo
        reading_score_no_cefr = Student.query.filter(
            Student.reading.isnot(None),
            Student.read_cefr.is_(None)
        ).count()
        if reading_score_no_cefr > 0:
            print(f"⚠️  {reading_score_no_cefr} estudantes com reading score mas Read_CEFR nulo")
        
        # LFM score mas LFM_CEFR nulo
        lfm_score_no_cefr = Student.query.filter(
            Student.lfm.isnot(None),
            Student.lfm_cefr.is_(None)
        ).count()
        if lfm_score_no_cefr > 0:
            print(f"⚠️  {lfm_score_no_cefr} estudantes com LFM score mas LFM_CEFR nulo")
        
        # Total score mas CEFR_Geral nulo
        total_score_no_cefr = Student.query.filter(
            Student.total.isnot(None),
            Student.cefr_geral.is_(None)
        ).count()
        if total_score_no_cefr > 0:
            print(f"⚠️  {total_score_no_cefr} estudantes com total score mas CEFR_Geral nulo")
        
        # Resumo final
        print("\n=== RESUMO ===")
        total_problems = asterisk_read + asterisk_lfm + asterisk_geral + reading_score_no_cefr + lfm_score_no_cefr + total_score_no_cefr
        
        if total_problems == 0:
            print("✅ Nenhum problema encontrado nos outros campos CEFR!")
        else:
            print(f"⚠️  Total de problemas encontrados: {total_problems}")
            if asterisk_read > 0:
                print(f"   - Read_CEFR com asterisco: {asterisk_read}")
            if asterisk_lfm > 0:
                print(f"   - LFM_CEFR com asterisco: {asterisk_lfm}")
            if asterisk_geral > 0:
                print(f"   - CEFR_Geral com asterisco: {asterisk_geral}")
            if reading_score_no_cefr > 0:
                print(f"   - Reading score sem CEFR: {reading_score_no_cefr}")
            if lfm_score_no_cefr > 0:
                print(f"   - LFM score sem CEFR: {lfm_score_no_cefr}")
            if total_score_no_cefr > 0:
                print(f"   - Total score sem CEFR Geral: {total_score_no_cefr}")

if __name__ == "__main__":
    check_other_cefr_fields()