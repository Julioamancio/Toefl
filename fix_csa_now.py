#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from render_auto_fix import run_auto_fix

def fix_csa_now():
    with app.app_context():
        print("Executando correção automática do CSA...")
        result = run_auto_fix()
        
        print(f"\nResultados:")
        print(f"Sucesso geral: {result['overall_success']}")
        print(f"Total de correções: {result['total_corrections']}")
        print(f"Duração: {result['duration_seconds']:.2f} segundos")
        
        if result['class_fixes']:
            print(f"\nCorreções de turmas: {result['class_fixes']['corrections_made']}")
            print(f"Mensagem: {result['class_fixes']['message']}")
        
        if result['csa_fixes']:
            print(f"\nCorreções de CSA: {result['csa_fixes']['corrections_made']}")
            print(f"Mensagem: {result['csa_fixes']['message']}")
            print(f"Total de estudantes: {result['csa_fixes']['total_students']}")
            print(f"Erros: {result['csa_fixes']['errors']}")
            
            if result['csa_fixes']['correction_details']:
                print("\nDetalhes das correções (primeiros 5):")
                for detail in result['csa_fixes']['correction_details'][:5]:
                    print(f"  - {detail['student_name']}: {detail['old_csa']} → {detail['new_csa']} (Score: {detail['listening_score']})")
            
            if result['csa_fixes']['error_details']:
                print("\nDetalhes dos erros (primeiros 5):")
                for error in result['csa_fixes']['error_details'][:5]:
                    print(f"  - {error['student_name']}: {error['error']}")

if __name__ == '__main__':
    fix_csa_now()