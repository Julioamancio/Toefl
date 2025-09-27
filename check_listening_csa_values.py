#!/usr/bin/env python3
"""
Script para verificar os valores de Listening CSA dos estudantes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Student
from listening_csa import compute_listening_csa

def check_listening_csa_values():
    """Verifica os valores de Listening CSA dos estudantes"""
    with app.app_context():
        try:
            students = Student.query.limit(20).all()
            print('=== VERIFICAÇÃO LISTENING CSA ===')
            print(f"{'Nome':<20} {'Listening':<10} {'Meta':<6} {'CSA DB':<8} {'CSA Calc':<8} {'Status':<10}")
            print('-' * 80)
            
            problemas = 0
            total_verificados = 0
            
            for student in students:
                if student.listening and student.class_info and student.class_info.meta_label:
                    try:
                        # CSA do banco de dados
                        csa_db = student.listening_csa_points
                        csa_db_str = str(csa_db) if csa_db is not None else 'None'
                        
                        # CSA calculado em tempo real
                        rotulo = float(student.class_info.meta_label)
                        csa_calc = compute_listening_csa(rotulo, student.listening)
                        csa_calc_points = csa_calc['points']
                        
                        # Status
                        status = 'OK' if csa_db == csa_calc_points else 'DIFERENTE'
                        if status == 'DIFERENTE':
                            problemas += 1
                        
                        total_verificados += 1
                        
                        print(f"{student.name[:19]:<20} {student.listening:<10} {student.class_info.meta_label:<6} {csa_db_str:<8} {csa_calc_points:<8} {status:<10}")
                        
                        # Mostrar detalhes se houver diferença
                        if status == 'DIFERENTE':
                            print(f"  -> Esperado: {csa_calc['expected_level']}, Obtido: {csa_calc['obtained_level']}")
                        
                    except Exception as e:
                        print(f"{student.name[:19]:<20} {student.listening:<10} ERROR: {str(e)}")
                else:
                    dados_faltando = []
                    if not student.listening:
                        dados_faltando.append("listening")
                    if not student.class_info:
                        dados_faltando.append("class_info")
                    elif not student.class_info.meta_label:
                        dados_faltando.append("meta_label")
                    
                    print(f"{student.name[:19]:<20} {student.listening or 'N/A':<10} FALTAM: {', '.join(dados_faltando)}")
            
            print(f"\n=== RESUMO ===")
            print(f"Total verificados: {total_verificados}")
            print(f"Problemas encontrados: {problemas}")
            
            if problemas > 0:
                print(f"\n⚠️  Encontrados {problemas} estudantes com valores de CSA incorretos!")
                return False
            else:
                print(f"\n✅ Todos os valores de CSA estão corretos!")
                return True
                
        except Exception as e:
            print(f"Erro durante verificação: {str(e)}")
            return False

if __name__ == "__main__":
    success = check_listening_csa_values()
    sys.exit(0 if success else 1)