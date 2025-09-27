#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para corrigir valores de asterisco (*) no campo List_CEFR
Calcula o CEFR correto baseado na pontuação de listening
"""

from app import app, db
from models import Student
from toefl_calculator import cefr_listening

def fix_asterisk_cefr():
    """Corrige valores de asterisco no List_CEFR"""
    
    with app.app_context():
        print("=== CORREÇÃO DE VALORES ASTERISCO (*) NO LIST_CEFR ===\n")
        
        # Buscar estudantes com List_CEFR = '*'
        asterisk_students = Student.query.filter(Student.list_cefr == '*').all()
        
        if not asterisk_students:
            print("✅ Nenhum estudante com List_CEFR = '*' encontrado!")
            return
        
        print(f"📊 Encontrados {len(asterisk_students)} estudantes com List_CEFR = '*'")
        print("\n=== PROCESSANDO CORREÇÕES ===")
        print("ID    Nome                 Listening  Antigo     Novo")
        print("-" * 60)
        
        corrected_count = 0
        
        for student in asterisk_students:
            if student.listening is not None:
                # Calcular o CEFR correto baseado na pontuação de listening
                correct_cefr = cefr_listening(student.listening)
                old_cefr = student.list_cefr
                
                # Atualizar o campo
                student.list_cefr = correct_cefr
                
                # Mostrar a correção
                name_short = student.name[:20] if student.name else "N/A"
                print(f"{student.id:<5} {name_short:<20} {student.listening:<10} {old_cefr:<10} {correct_cefr}")
                
                corrected_count += 1
            else:
                # Estudante sem pontuação de listening - manter como está mas avisar
                name_short = student.name[:20] if student.name else "N/A"
                print(f"{student.id:<5} {name_short:<20} {'N/A':<10} {'*':<10} {'*'} (sem listening score)")
        
        # Salvar as alterações
        try:
            db.session.commit()
            print(f"\n✅ {corrected_count} estudantes corrigidos com sucesso!")
            
            # Verificar se ainda há asteriscos
            remaining_asterisk = Student.query.filter(Student.list_cefr == '*').count()
            if remaining_asterisk == 0:
                print("🎉 Todos os valores de asterisco foram corrigidos!")
            else:
                print(f"⚠️  Ainda restam {remaining_asterisk} estudantes com asterisco (provavelmente sem listening score)")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar as correções: {e}")
            return
        
        # Mostrar estatísticas finais
        print("\n=== ESTATÍSTICAS FINAIS ===")
        unique_cefr = db.session.query(Student.list_cefr).distinct().all()
        print("Valores únicos de List_CEFR após correção:")
        for value in unique_cefr:
            count = Student.query.filter(Student.list_cefr == value[0]).count()
            print(f"  {value[0]}: {count} estudantes")

def verify_cefr_calculation():
    """Verifica se os cálculos de CEFR estão corretos"""
    
    print("\n=== VERIFICAÇÃO DOS CÁLCULOS CEFR ===")
    
    # Testar algumas pontuações
    test_scores = [200, 205, 220, 245, 250, 265, 280, 300]
    
    print("Score  CEFR Calculado")
    print("-" * 25)
    for score in test_scores:
        cefr = cefr_listening(score)
        print(f"{score:<6} {cefr}")

if __name__ == "__main__":
    verify_cefr_calculation()
    fix_asterisk_cefr()