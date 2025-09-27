#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Automático de Correção do Banco de Dados

Este script foi projetado para rodar automaticamente no Render.com
sem necessidade de interação manual. Ele:

1. Corrige turmas sem meta_label
2. Verifica e corrige CSA de Listening para todos os estudantes
3. Gera relatórios detalhados

Uso no Render.com:
    python auto_fix_database.py

Uso local com dry-run:
    python auto_fix_database.py --dry-run
"""

import os
import sys
import argparse
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
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

def fix_classes_meta_label(dry_run=False):
    """Corrige turmas sem meta_label"""
    print("\n" + "="*60)
    print("🏫 VERIFICAÇÃO DE META_LABEL DAS TURMAS")
    print("="*60)
    
    # Buscar turmas sem meta_label
    classes_without_meta = Class.query.filter(
        (Class.meta_label == None) | (Class.meta_label == '')
    ).all()
    
    if not classes_without_meta:
        print("✅ Todas as turmas possuem meta_label definido!")
        return 0
    
    print(f"\n⚠️  ENCONTRADAS {len(classes_without_meta)} TURMAS SEM META_LABEL:")
    
    corrections_made = 0
    for class_obj in classes_without_meta:
        suggested_label = suggest_meta_label(class_obj.name)
        
        print(f"\n📚 Turma: {class_obj.name} (ID: {class_obj.id})")
        print(f"   📊 Estudantes: {len(class_obj.students)}")
        print(f"   🏷️  Meta_label atual: {class_obj.meta_label or 'None'}")
        print(f"   💡 Sugestão: {suggested_label}")
        
        if not dry_run:
            class_obj.meta_label = suggested_label
            corrections_made += 1
            print(f"   ✅ Corrigido para: {suggested_label}")
        else:
            print(f"   🔍 [DRY RUN] Seria corrigido para: {suggested_label}")
    
    if not dry_run and corrections_made > 0:
        try:
            db.session.commit()
            print(f"\n💾 {corrections_made} turmas corrigidas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao salvar correções: {str(e)}")
            return 0
    
    return corrections_made

def fix_listening_csa(dry_run=False):
    """Verifica e corrige CSA de Listening para todos os estudantes"""
    print("\n" + "="*60)
    print("🎧 VERIFICAÇÃO DE LISTENING CSA")
    print("="*60)
    
    # Buscar todos os estudantes
    students = Student.query.all()
    total_students = len(students)
    
    print(f"\n📊 Total de estudantes: {total_students}")
    
    results = []
    students_processed = 0
    errors = 0
    corrections_needed = 0
    
    for student in students:
        students_processed += 1
        
        try:
            # Verificar se tem listening score e turma
            if not student.listening or not student.class_info:
                continue
            
            # Verificar se a turma tem meta_label
            if not student.class_info.meta_label:
                error_msg = f"Turma {student.class_info.name} sem meta_label"
                results.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'class_name': student.class_info.name,
                    'listening_score': student.listening,
                    'current_csa': student.listening_csa_points,
                    'expected_csa': None,
                    'needs_fix': False,
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
                if not dry_run:
                    student.listening_csa_points = expected_csa
            
            results.append({
                'student_id': student.id,
                'student_name': student.name,
                'class_name': student.class_info.name,
                'listening_score': student.listening,
                'current_csa': current_csa,
                'expected_csa': expected_csa,
                'needs_fix': needs_fix,
                'error': None,
                'expected_level': csa_result['expected_level'],
                'obtained_level': csa_result['obtained_level']
            })
            
        except Exception as e:
            error_msg = f"Erro no cálculo: {str(e)}"
            results.append({
                'student_id': student.id,
                'student_name': student.name,
                'class_name': student.class_info.name if student.class_info else 'Sem turma',
                'listening_score': student.listening,
                'current_csa': student.listening_csa_points,
                'expected_csa': None,
                'needs_fix': False,
                'error': error_msg
            })
            errors += 1
    
    # Relatório de resultados
    print(f"\n📈 RELATÓRIO DE VERIFICAÇÃO:")
    print(f"   👥 Estudantes processados: {students_processed}")
    print(f"   ✅ CSA corretos: {students_processed - corrections_needed - errors}")
    print(f"   🔧 Correções necessárias: {corrections_needed}")
    print(f"   ❌ Erros encontrados: {errors}")
    
    # Mostrar erros
    if errors > 0:
        print(f"\n⚠️  ERROS ENCONTRADOS ({errors}):")
        error_summary = {}
        for result in results:
            if result['error']:
                error_type = result['error']
                if error_type not in error_summary:
                    error_summary[error_type] = 0
                error_summary[error_type] += 1
        
        for error_type, count in error_summary.items():
            print(f"   • {error_type}: {count} estudantes")
    
    # Aplicar correções se necessário
    if corrections_needed > 0:
        print(f"\n🔧 CORREÇÕES NECESSÁRIAS: {corrections_needed} estudantes")
        
        if not dry_run:
            print("\n🔄 APLICANDO CORREÇÕES AUTOMATICAMENTE...")
            try:
                db.session.commit()
                print(f"💾 {corrections_needed} correções aplicadas com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar correções: {str(e)}")
                return 0
        else:
            print("\n[DRY RUN] Correções seriam aplicadas se não fosse modo de simulação")
    
    return corrections_needed

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Script automático de correção do banco de dados'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Executar em modo de simulação (não faz alterações)'
    )
    
    args = parser.parse_args()
    
    print("🚀 SCRIPT AUTOMÁTICO DE CORREÇÃO DO BANCO DE DADOS")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🔍 MODO: Simulação (Dry Run) - Nenhuma alteração será feita")
    else:
        print("💾 MODO: Produção - Alterações serão aplicadas")
    
    # Criar contexto da aplicação
    try:
        app, csrf = create_app()
    except ValueError:
        app = create_app()
    
    with app.app_context():
        total_fixes = 0
        
        # 1. Corrigir meta_labels das turmas
        class_fixes = fix_classes_meta_label(dry_run=args.dry_run)
        total_fixes += class_fixes
        
        # 2. Corrigir CSA de Listening
        csa_fixes = fix_listening_csa(dry_run=args.dry_run)
        total_fixes += csa_fixes
        
        # Resumo final
        print("\n" + "="*60)
        print("📋 RESUMO FINAL")
        print("="*60)
        print(f"🏫 Turmas corrigidas: {class_fixes}")
        print(f"🎧 CSA corrigidos: {csa_fixes}")
        print(f"📊 Total de correções: {total_fixes}")
        
        if args.dry_run:
            print("\n🔍 Este foi um DRY RUN - nenhuma alteração foi feita")
            print("   Para aplicar as correções, execute sem --dry-run")
        elif total_fixes > 0:
            print("\n✅ Todas as correções foram aplicadas com sucesso!")
        else:
            print("\n✅ Banco de dados já está correto - nenhuma correção necessária")
        
        print(f"\n⏰ Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()