#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Correção Automática para Render.com

Este script é executado via interface administrativa para:
1. Corrigir turmas sem meta_label
2. Verificar e corrigir CSA de Listening para todos os estudantes
3. Gerar relatórios detalhados

Uso via interface administrativa:
    - Acesse /admin
    - Clique no botão "Executar Correções Automáticas"
"""

import os
import sys
from datetime import datetime
from flask import jsonify

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Student, Class
from listening_csa import compute_listening_csa

def suggest_meta_label(class_name):
    """Sugere um meta_label baseado no nome da turma"""
    name_lower = class_name.lower()
    
    # Padrões para 6º ano
    if any(pattern in name_lower for pattern in ['6', 'sexto', 'sixth']):
        if any(pattern in name_lower for pattern in ['a', '1', 'primeira', 'first']):
            return '6.1'
        elif any(pattern in name_lower for pattern in ['b', '2', 'segunda', 'second']):
            return '6.2'
        elif any(pattern in name_lower for pattern in ['c', '3', 'terceira', 'third']):
            return '6.3'
        else:
            return '6.1'  # Default para 6º ano
    
    # Padrões para 9º ano
    elif any(pattern in name_lower for pattern in ['9', 'nono', 'ninth']):
        if any(pattern in name_lower for pattern in ['a', '1', 'primeira', 'first']):
            return '9.1'
        elif any(pattern in name_lower for pattern in ['b', '2', 'segunda', 'second']):
            return '9.2'
        elif any(pattern in name_lower for pattern in ['c', '3', 'terceira', 'third']):
            return '9.3'
        else:
            return '9.1'  # Default para 9º ano
    
    # Se não conseguir identificar, usar 6.1 como padrão
    return '6.1'

def fix_classes_meta_label():
    """Corrige turmas sem meta_label"""
    try:
        # Buscar turmas sem meta_label
        classes_without_meta = Class.query.filter(
            (Class.meta_label == None) | (Class.meta_label == '')
        ).all()
        
        if not classes_without_meta:
            return {
                'success': True,
                'message': 'Todas as turmas já possuem meta_label definido',
                'corrections_made': 0,
                'details': []
            }
        
        corrections_made = 0
        details = []
        
        for class_obj in classes_without_meta:
            suggested_label = suggest_meta_label(class_obj.name)
            old_label = class_obj.meta_label or 'None'
            
            class_obj.meta_label = suggested_label
            corrections_made += 1
            
            details.append({
                'class_name': class_obj.name,
                'class_id': class_obj.id,
                'students_count': len(class_obj.students),
                'old_label': old_label,
                'new_label': suggested_label
            })
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'{corrections_made} turmas corrigidas com sucesso',
            'corrections_made': corrections_made,
            'details': details
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Erro ao corrigir turmas: {str(e)}',
            'corrections_made': 0,
            'details': []
        }

def fix_listening_csa():
    """Verifica e corrige CSA de Listening para todos os estudantes"""
    try:
        # Buscar todos os estudantes
        students = Student.query.all()
        total_students = len(students)
        
        corrections_needed = 0
        corrections_made = 0
        errors = 0
        error_details = []
        correction_details = []
        
        for student in students:
            try:
                # Verificar se tem listening score e turma
                if not student.listening or not student.class_info:
                    continue
                
                # Verificar se a turma tem meta_label
                if not student.class_info.meta_label:
                    error_msg = f"Turma {student.class_info.name} sem meta_label"
                    error_details.append({
                        'student_id': student.id,
                        'student_name': student.name,
                        'class_name': student.class_info.name,
                        'error': error_msg
                    })
                    errors += 1
                    continue
                
                # Calcular CSA esperado
                csa_result = compute_listening_csa(
                    rotulo_escolar=student.class_info.meta_label,
                    listening_score=student.listening
                )
                
                expected_csa = csa_result['points']
                current_csa = student.listening_csa_points or 0
                
                needs_fix = abs(expected_csa - current_csa) > 0.01
                
                if needs_fix:
                    corrections_needed += 1
                    student.listening_csa_points = expected_csa
                    corrections_made += 1
                    
                    correction_details.append({
                        'student_id': student.id,
                        'student_name': student.name,
                        'class_name': student.class_info.name,
                        'listening_score': student.listening,
                        'old_csa': current_csa,
                        'new_csa': expected_csa,
                        'expected_level': csa_result['expected_level'],
                        'obtained_level': csa_result['obtained_level']
                    })
                
            except Exception as e:
                error_msg = f"Erro no cálculo: {str(e)}"
                error_details.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'class_name': student.class_info.name if student.class_info else 'Sem turma',
                    'error': error_msg
                })
                errors += 1
        
        # Salvar alterações
        if corrections_made > 0:
            db.session.commit()
        
        return {
            'success': True,
            'message': f'Verificação concluída: {corrections_made} correções aplicadas',
            'total_students': total_students,
            'corrections_made': corrections_made,
            'errors': errors,
            'correction_details': correction_details[:10],  # Limitar a 10 para não sobrecarregar
            'error_details': error_details[:10],  # Limitar a 10 para não sobrecarregar
            'has_more_corrections': len(correction_details) > 10,
            'has_more_errors': len(error_details) > 10
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Erro durante verificação: {str(e)}',
            'total_students': 0,
            'corrections_made': 0,
            'errors': 0,
            'correction_details': [],
            'error_details': []
        }

def run_auto_fix():
    """Executa todas as correções automáticas"""
    start_time = datetime.now()
    
    results = {
        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': None,
        'duration_seconds': None,
        'overall_success': True,
        'total_corrections': 0,
        'class_fixes': None,
        'csa_fixes': None
    }
    
    try:
        # 1. Corrigir meta_labels das turmas
        print("Iniciando correção de meta_labels das turmas...")
        class_result = fix_classes_meta_label()
        results['class_fixes'] = class_result
        
        if not class_result['success']:
            results['overall_success'] = False
        else:
            results['total_corrections'] += class_result['corrections_made']
        
        # 2. Corrigir CSA de Listening
        print("Iniciando correção de CSA de Listening...")
        csa_result = fix_listening_csa()
        results['csa_fixes'] = csa_result
        
        if not csa_result['success']:
            results['overall_success'] = False
        else:
            results['total_corrections'] += csa_result['corrections_made']
        
        # Finalizar
        end_time = datetime.now()
        results['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        print(f"Correções concluídas em {results['duration_seconds']:.2f} segundos")
        
        return results
        
    except Exception as e:
        end_time = datetime.now()
        results['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        results['overall_success'] = False
        results['error'] = str(e)
        
        print(f"Erro durante execução: {str(e)}")
        return results

if __name__ == '__main__':
    # Para testes locais
    from app import create_app
    
    try:
        app, csrf = create_app()
    except ValueError:
        app = create_app()
    
    with app.app_context():
        result = run_auto_fix()
        print("\n=== RESULTADO FINAL ===")
        print(f"Sucesso: {result['overall_success']}")
        print(f"Total de correções: {result['total_corrections']}")
        print(f"Duração: {result['duration_seconds']:.2f} segundos")
        
        if result['class_fixes']:
            print(f"\nTurmas corrigidas: {result['class_fixes']['corrections_made']}")
        
        if result['csa_fixes']:
            print(f"CSA corrigidos: {result['csa_fixes']['corrections_made']}")
            print(f"Erros encontrados: {result['csa_fixes']['errors']}")