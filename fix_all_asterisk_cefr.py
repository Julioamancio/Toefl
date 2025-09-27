#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para corrigir todos os valores de asterisco (*) nos campos CEFR
Calcula os valores CEFR corretos baseados nas pontuações
"""

from app import app, db
from models import Student
from toefl_calculator import cefr_listening

def cefr_reading(score):
    """
    Classifica uma pontuação de Reading (200-300) em nível CEFR
    Baseado nas mesmas faixas do listening
    """
    if score is None or score < 200:
        return 'A1'
    
    score = float(score)
    
    if 200 <= score <= 245:
        return 'A2'
    elif 246 <= score <= 265:
        return 'A2+'
    elif 266 <= score <= 285:
        return 'B1'
    elif 286 <= score <= 300:
        return 'B2'
    elif score >= 301:
        return 'B2+'
    else:
        return 'A1'

def cefr_lfm(score):
    """
    Classifica uma pontuação de LFM (200-300) em nível CEFR
    Baseado nas mesmas faixas do listening
    """
    if score is None or score < 200:
        return 'A1'
    
    score = float(score)
    
    if 200 <= score <= 245:
        return 'A2'
    elif 246 <= score <= 265:
        return 'A2+'
    elif 266 <= score <= 285:
        return 'B1'
    elif 286 <= score <= 300:
        return 'B2'
    elif score >= 301:
        return 'B2+'
    else:
        return 'A1'

def fix_all_asterisk_cefr():
    """Corrige todos os valores de asterisco nos campos CEFR"""
    
    with app.app_context():
        print("=== CORREÇÃO DE TODOS OS VALORES ASTERISCO (*) ===\n")
        
        # Corrigir Read_CEFR
        print("=== CORRIGINDO READ_CEFR ===")
        asterisk_read = Student.query.filter(Student.read_cefr == '*').all()
        
        if asterisk_read:
            print(f"Encontrados {len(asterisk_read)} estudantes com Read_CEFR = '*'")
            print("ID    Nome                 Reading    Antigo     Novo")
            print("-" * 60)
            
            read_corrected = 0
            for student in asterisk_read:
                if student.reading is not None:
                    correct_cefr = cefr_reading(student.reading)
                    old_cefr = student.read_cefr
                    student.read_cefr = correct_cefr
                    
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {student.reading:<10} {old_cefr:<10} {correct_cefr}")
                    read_corrected += 1
                else:
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {'N/A':<10} {'*':<10} {'*'} (sem reading score)")
            
            print(f"✅ {read_corrected} Read_CEFR corrigidos")
        else:
            print("✅ Nenhum Read_CEFR com asterisco encontrado")
        
        # Corrigir LFM_CEFR
        print("\n=== CORRIGINDO LFM_CEFR ===")
        asterisk_lfm = Student.query.filter(Student.lfm_cefr == '*').all()
        
        if asterisk_lfm:
            print(f"Encontrados {len(asterisk_lfm)} estudantes com LFM_CEFR = '*'")
            print("ID    Nome                 LFM        Antigo     Novo")
            print("-" * 60)
            
            lfm_corrected = 0
            for student in asterisk_lfm:
                if student.lfm is not None:
                    correct_cefr = cefr_lfm(student.lfm)
                    old_cefr = student.lfm_cefr
                    student.lfm_cefr = correct_cefr
                    
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {student.lfm:<10} {old_cefr:<10} {correct_cefr}")
                    lfm_corrected += 1
                else:
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {'N/A':<10} {'*':<10} {'*'} (sem LFM score)")
            
            print(f"✅ {lfm_corrected} LFM_CEFR corrigidos")
        else:
            print("✅ Nenhum LFM_CEFR com asterisco encontrado")
        
        # Corrigir CEFR_Geral nulo
        print("\n=== CORRIGINDO CEFR_GERAL NULO ===")
        null_cefr_geral = Student.query.filter(Student.cefr_geral.is_(None)).all()
        
        if null_cefr_geral:
            print(f"Encontrados {len(null_cefr_geral)} estudantes com CEFR_Geral nulo")
            print("ID    Nome                 Total      CEFR_Geral")
            print("-" * 50)
            
            geral_corrected = 0
            for student in null_cefr_geral:
                if student.total is not None:
                    # Usar o método do modelo para calcular CEFR geral
                    correct_cefr = student.calculate_final_cefr()
                    student.cefr_geral = correct_cefr
                    
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {student.total:<10} {correct_cefr}")
                    geral_corrected += 1
                else:
                    name_short = student.name[:20] if student.name else "N/A"
                    print(f"{student.id:<5} {name_short:<20} {'N/A':<10} N/A (sem total score)")
            
            print(f"✅ {geral_corrected} CEFR_Geral corrigidos")
        else:
            print("✅ Nenhum CEFR_Geral nulo encontrado")
        
        # Salvar todas as alterações
        try:
            db.session.commit()
            print(f"\n🎉 TODAS AS CORREÇÕES FORAM SALVAS COM SUCESSO!")
            
            # Verificar estatísticas finais
            print("\n=== ESTATÍSTICAS FINAIS ===")
            
            remaining_asterisk_read = Student.query.filter(Student.read_cefr == '*').count()
            remaining_asterisk_lfm = Student.query.filter(Student.lfm_cefr == '*').count()
            remaining_null_geral = Student.query.filter(Student.cefr_geral.is_(None)).count()
            
            print(f"Read_CEFR com asterisco restantes: {remaining_asterisk_read}")
            print(f"LFM_CEFR com asterisco restantes: {remaining_asterisk_lfm}")
            print(f"CEFR_Geral nulos restantes: {remaining_null_geral}")
            
            if remaining_asterisk_read == 0 and remaining_asterisk_lfm == 0 and remaining_null_geral == 0:
                print("🎉 TODOS OS PROBLEMAS FORAM CORRIGIDOS!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar as correções: {e}")

if __name__ == "__main__":
    fix_all_asterisk_cefr()