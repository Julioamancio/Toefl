#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação e Correção Automática do Listening CSA

Este script:
1. Verifica todos os estudantes no banco de dados
2. Identifica estudantes com Listening CSA faltante ou incorreto
3. Recalcula automaticamente o CSA quando possível
4. Gera relatório detalhado das correções
5. Pode ser executado periodicamente para manutenção

Uso:
    python fix_listening_csa_automatic.py [--dry-run] [--class-id ID]
"""

import sys
import os
import argparse
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Student, Class
from listening_csa import compute_listening_csa

def check_and_fix_student_csa(student, dry_run=False):
    """
    Verifica e corrige o Listening CSA de um estudante específico
    
    Args:
        student: Objeto Student
        dry_run: Se True, apenas simula as correções sem salvar
    
    Returns:
        dict: Resultado da verificação/correção
    """
    result = {
        'student_id': student.id,
        'student_number': student.student_number,
        'name': student.name,
        'listening_score': student.listening,
        'class_id': student.class_id,
        'current_csa': student.listening_csa_points,
        'calculated_csa': None,
        'needs_fix': False,
        'fixed': False,
        'error': None
    }
    
    try:
        # Verificar se tem dados necessários
        if not student.listening:
            result['error'] = 'Sem pontuação de Listening'
            return result
            
        if not student.class_id:
            result['error'] = 'Sem turma associada'
            return result
            
        # Buscar informações da turma
        class_info = Class.query.get(student.class_id)
        if not class_info:
            result['error'] = f'Turma {student.class_id} não encontrada'
            return result
            
        if not class_info.meta_label:
            result['error'] = f'Turma {student.class_id} sem meta_label'
            return result
            
        # Calcular CSA esperado
        try:
            rotulo_escolar = float(class_info.meta_label)
            csa_result = compute_listening_csa(rotulo_escolar, student.listening)
            calculated_csa = csa_result['points'] if isinstance(csa_result, dict) else csa_result
            result['calculated_csa'] = calculated_csa
            
            # Verificar se precisa correção
            if student.listening_csa_points != calculated_csa:
                result['needs_fix'] = True
                
                if not dry_run:
                    # Aplicar correção
                    student.listening_csa_points = calculated_csa
                    db.session.add(student)
                    result['fixed'] = True
                    
        except (ValueError, TypeError) as e:
            result['error'] = f'Erro no cálculo CSA: {str(e)}'
            
    except Exception as e:
        result['error'] = f'Erro inesperado: {str(e)}'
        
    return result

def generate_report(results):
    """
    Gera relatório detalhado dos resultados
    """
    total = len(results)
    needs_fix = sum(1 for r in results if r['needs_fix'])
    fixed = sum(1 for r in results if r['fixed'])
    errors = sum(1 for r in results if r['error'])
    
    print("\n" + "="*60)
    print("RELATÓRIO DE VERIFICAÇÃO E CORREÇÃO DO LISTENING CSA")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nResumo:")
    print(f"  - Total de estudantes verificados: {total}")
    print(f"  - Estudantes que precisavam correção: {needs_fix}")
    print(f"  - Estudantes corrigidos: {fixed}")
    print(f"  - Estudantes com erro: {errors}")
    
    if needs_fix > 0:
        print(f"\n📋 ESTUDANTES QUE PRECISAVAM CORREÇÃO:")
        print("-" * 60)
        for result in results:
            if result['needs_fix']:
                status = "✅ CORRIGIDO" if result['fixed'] else "⏳ SIMULAÇÃO"
                print(f"  {result['student_number']} - {result['name']}")
                print(f"    CSA Atual: {result['current_csa']} → CSA Correto: {result['calculated_csa']}")
                print(f"    Listening: {result['listening_score']} | Status: {status}")
                print()
    
    if errors > 0:
        print(f"\n❌ ESTUDANTES COM ERRO:")
        print("-" * 60)
        for result in results:
            if result['error']:
                print(f"  {result['student_number']} - {result['name']}")
                print(f"    Erro: {result['error']}")
                print()
    
    if needs_fix == 0 and errors == 0:
        print(f"\n✅ TODOS OS ESTUDANTES ESTÃO COM CSA CORRETO!")

def main():
    parser = argparse.ArgumentParser(description='Verificar e corrigir Listening CSA automaticamente')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Apenas simular correções sem salvar no banco')
    parser.add_argument('--class-id', type=int, 
                       help='Verificar apenas estudantes de uma turma específica')
    parser.add_argument('--student-number', type=str,
                       help='Verificar apenas um estudante específico')
    
    args = parser.parse_args()
    
    # Criar aplicação Flask
    app_tuple = create_app()
    app = app_tuple[0] if isinstance(app_tuple, tuple) else app_tuple
    
    with app.app_context():
        print("🔍 INICIANDO VERIFICAÇÃO DO LISTENING CSA")
        
        if args.dry_run:
            print("⚠️  MODO SIMULAÇÃO - Nenhuma alteração será salva")
        
        # Construir query
        query = Student.query
        
        if args.class_id:
            query = query.filter(Student.class_id == args.class_id)
            print(f"📚 Verificando apenas turma ID: {args.class_id}")
            
        if args.student_number:
            query = query.filter(Student.student_number == args.student_number)
            print(f"👤 Verificando apenas estudante: {args.student_number}")
        
        students = query.all()
        
        if not students:
            print("❌ Nenhum estudante encontrado com os critérios especificados")
            return
            
        print(f"📊 Encontrados {len(students)} estudantes para verificação")
        print("\n🔄 Processando...")
        
        results = []
        
        for i, student in enumerate(students, 1):
            if i % 50 == 0:  # Progress indicator
                print(f"   Processados: {i}/{len(students)}")
                
            result = check_and_fix_student_csa(student, dry_run=args.dry_run)
            results.append(result)
        
        # Salvar alterações se não for dry-run
        corrections_needed = sum(1 for r in results if r['needs_fix'])
        
        # Aplicar correções automaticamente (sem interação manual para funcionar no Render.com)
        if corrections_needed > 0:
            print(f"\n🔧 CORREÇÕES NECESSÁRIAS: {corrections_needed} estudantes")
            
            if not args.dry_run:
                apply_corrections = True
                print("\n🔄 APLICANDO CORREÇÕES AUTOMATICAMENTE...")
            else:
                print("\n[DRY RUN] Correções seriam aplicadas se não fosse modo de simulação")
                apply_corrections = False
        
        if not args.dry_run and corrections_needed > 0:
            try:
                db.session.commit()
                print("💾 Alterações salvas no banco de dados")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar alterações: {str(e)}")
                return
        
        # Gerar relatório
        generate_report(results)
        
        print("\n✅ Verificação concluída!")
        
        if args.dry_run:
            print("\n💡 Para aplicar as correções, execute novamente sem --dry-run")

if __name__ == '__main__':
    main()