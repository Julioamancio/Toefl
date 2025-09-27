#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular as notas de Listening dos estudantes existentes
usando a nova lógica baseada em CEFR e rótulos escolares
"""

import sqlite3
from listening_csa import compute_listening_csa

def grade_listening(score, meta_label):
    """Wrapper para usar compute_listening_csa"""
    if not score or not meta_label:
        return 0.0
    try:
        if isinstance(meta_label, str):
            rotulo_escolar = float(meta_label)
        else:
            rotulo_escolar = meta_label
        return compute_listening_csa(rotulo_escolar, score)
    except (ValueError, TypeError):
        return 0.0

def recalculate_all_student_grades():
    """Recalcula as notas de Listening de todos os estudantes"""
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('toefl_database.db')
    cursor = conn.cursor()
    
    try:
        # Buscar todos os estudantes com suas pontuações e turmas
        query = """
        SELECT s.id, s.student_number, s.name, s.listening_score, 
               c.meta_label, s.grade_listening as old_grade
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.listening_score IS NOT NULL
        ORDER BY c.meta_label, s.student_number
        """
        
        cursor.execute(query)
        students = cursor.fetchall()
        
        if not students:
            print("Nenhum estudante encontrado com pontuação de Listening.")
            return
        
        print(f"=== RECALCULANDO NOTAS DE {len(students)} ESTUDANTES ===\n")
        print("ID   Número  Nome                 Score  Label  Nota Antiga  Nota Nova  Diferença")
        print("-" * 85)
        
        updated_count = 0
        total_difference = 0
        
        for student in students:
            student_id, student_number, name, listening_score, meta_label, old_grade = student
            
            # Calcular nova nota usando a nova lógica
            new_grade = grade_listening(listening_score, meta_label)
            
            # Calcular diferença
            old_grade_val = float(old_grade) if old_grade is not None else 0.0
            difference = new_grade - old_grade_val
            total_difference += abs(difference)
            
            # Mostrar resultado
            name_short = name[:20] if len(name) > 20 else name
            diff_str = f"{difference:+.1f}" if difference != 0 else "0.0"
            
            print(f"{student_id:<4} {student_number:<7} {name_short:<20} {listening_score:<6} "
                  f"{meta_label:<6} {old_grade_val:<11.1f} {new_grade:<9.1f} {diff_str}")
            
            # Atualizar no banco de dados
            update_query = "UPDATE students SET grade_listening = ? WHERE id = ?"
            cursor.execute(update_query, (new_grade, student_id))
            updated_count += 1
        
        # Commit das alterações
        conn.commit()
        
        print("-" * 85)
        print(f"✓ {updated_count} estudantes atualizados com sucesso!")
        print(f"✓ Diferença média absoluta: {total_difference/len(students):.2f}")
        
        # Estatísticas por rótulo
        print("\n=== ESTATÍSTICAS POR RÓTULO ===")
        
        stats_query = """
        SELECT c.meta_label, 
               COUNT(*) as total_students,
               AVG(s.grade_listening) as avg_grade,
               MIN(s.grade_listening) as min_grade,
               MAX(s.grade_listening) as max_grade
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.listening_score IS NOT NULL
        GROUP BY c.meta_label
        ORDER BY c.meta_label
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchall()
        
        print("Rótulo  Estudantes  Nota Média  Nota Min  Nota Max")
        print("-" * 50)
        
        for stat in stats:
            meta_label, total, avg_grade, min_grade, max_grade = stat
            print(f"{meta_label:<7} {total:<11} {avg_grade:<10.1f} {min_grade:<9.1f} {max_grade:.1f}")
        
    except Exception as e:
        print(f"Erro durante o recálculo: {e}")
        conn.rollback()
    
    finally:
        conn.close()

def verify_calculation_examples():
    """Verifica alguns exemplos específicos no banco de dados"""
    
    conn = sqlite3.connect('toefl_database.db')
    cursor = conn.cursor()
    
    try:
        print("\n=== VERIFICAÇÃO DE EXEMPLOS ESPECÍFICOS ===")
        
        # Buscar alguns estudantes para verificação manual
        query = """
        SELECT s.name, s.listening_score, c.meta_label, s.grade_listening
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.listening_score IS NOT NULL
        LIMIT 10
        """
        
        cursor.execute(query)
        examples = cursor.fetchall()
        
        print("Nome                 Score  Label  Nota DB  Nota Calc  Status")
        print("-" * 65)
        
        for example in examples:
            name, score, meta_label, db_grade = example
            calc_grade = grade_listening(score, meta_label)
            
            name_short = name[:20] if len(name) > 20 else name
            status = "✓" if abs(float(db_grade) - calc_grade) < 0.01 else "✗"
            
            print(f"{name_short:<20} {score:<6} {meta_label:<6} {db_grade:<7.1f} "
                  f"{calc_grade:<9.1f} {status}")
    
    except Exception as e:
        print(f"Erro na verificação: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    recalculate_all_student_grades()
    verify_calculation_examples()