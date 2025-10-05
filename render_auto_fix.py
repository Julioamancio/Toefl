#!/usr/bin/env python3
"""
Script de correção automática para o sistema TOEFL
Combina correção de turma_meta e recálculo de Listening CSA
"""

import time
from app import create_app
from models import Student, db
from listening_csa import compute_listening_csa

def run_auto_fix():
    """
    Executa todas as correções automáticas necessárias
    Retorna um dicionário com os resultados
    """
    start_time = time.time()
    
    # Criar contexto da aplicação
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    results = {
        'overall_success': True,
        'total_corrections': 0,
        'duration_seconds': 0,
        'details': {
            'turma_meta_fixed': 0,
            'csa_recalculated': 0,
            'errors': []
        }
    }
    
    try:
        with app.app_context():
            print("🔄 Iniciando correção automática...")
            
            # 1. Corrigir turma_meta
            print("📝 Corrigindo turma_meta...")
            turma_meta_result = fix_turma_meta()
            results['details']['turma_meta_fixed'] = turma_meta_result['fixed_count']
            results['total_corrections'] += turma_meta_result['fixed_count']
            
            if turma_meta_result['errors']:
                results['details']['errors'].extend(turma_meta_result['errors'])
            
            # 2. Recalcular Listening CSA
            print("🔢 Recalculando Listening CSA...")
            csa_result = recalculate_listening_csa()
            results['details']['csa_recalculated'] = csa_result['updated_count']
            results['total_corrections'] += csa_result['updated_count']
            
            if csa_result['errors']:
                results['details']['errors'].extend(csa_result['errors'])
            
            # Verificar se houve erros
            if results['details']['errors']:
                results['overall_success'] = False
            
            results['duration_seconds'] = time.time() - start_time
            
            print(f"✅ Correção automática concluída em {results['duration_seconds']:.2f}s")
            print(f"📊 Total de correções: {results['total_corrections']}")
            
            return results
            
    except Exception as e:
        results['overall_success'] = False
        results['details']['errors'].append(f"Erro geral: {str(e)}")
        results['duration_seconds'] = time.time() - start_time
        print(f"❌ Erro durante correção automática: {e}")
        return results

def fix_turma_meta():
    """Corrige o turma_meta dos alunos baseado no meta_label da classe"""
    
    result = {
        'fixed_count': 0,
        'errors': []
    }
    
    try:
        # Buscar alunos sem turma_meta
        students_without_meta = Student.query.filter(
            (Student.turma_meta.is_(None)) | (Student.turma_meta == '')
        ).all()
        
        print(f"📊 Encontrados {len(students_without_meta)} alunos sem turma_meta")
        
        for student in students_without_meta:
            try:
                if student.class_info and student.class_info.meta_label:
                    student.turma_meta = student.class_info.meta_label
                    result['fixed_count'] += 1
                    print(f"✅ {student.name}: turma_meta definido como {student.turma_meta}")
                else:
                    print(f"⚠️ {student.name}: Sem classe ou meta_label")
                    
            except Exception as e:
                error_msg = f"Erro ao corrigir {student.name}: {e}"
                result['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        if result['fixed_count'] > 0:
            db.session.commit()
            print(f"✅ {result['fixed_count']} alunos corrigidos com sucesso")
        else:
            print("ℹ️ Nenhum aluno precisou de correção de turma_meta")
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao corrigir turma_meta: {e}"
        result['errors'].append(error_msg)
        print(f"❌ {error_msg}")
    
    return result

def recalculate_listening_csa():
    """Recalcula os pontos CSA para todos os alunos"""
    
    result = {
        'updated_count': 0,
        'errors': []
    }
    
    try:
        # Buscar todos os alunos com listening e turma_meta
        students = Student.query.filter(
            Student.listening.isnot(None),
            Student.turma_meta.isnot(None),
            Student.turma_meta != ''
        ).all()
        
        print(f"📊 Encontrados {len(students)} alunos para recálculo de CSA")
        
        for student in students:
            try:
                # Calcular CSA
                csa_result = compute_listening_csa(student.turma_meta, student.listening)
                old_points = student.listening_csa_points
                new_points = csa_result['points']
                
                student.listening_csa_points = new_points
                result['updated_count'] += 1
                
                if result['updated_count'] <= 5:  # Mostrar apenas os primeiros 5
                    print(f"✅ {student.name}: {old_points} → {new_points}")
                elif result['updated_count'] == 6:
                    print("... (continuando recálculo)")
                    
            except Exception as e:
                error_msg = f"Erro ao recalcular CSA para {student.name}: {e}"
                result['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        if result['updated_count'] > 0:
            db.session.commit()
            print(f"✅ {result['updated_count']} alunos recalculados com sucesso")
        else:
            print("ℹ️ Nenhum aluno precisou de recálculo de CSA")
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao recalcular CSA: {e}"
        result['errors'].append(error_msg)
        print(f"❌ {error_msg}")
    
    return result

if __name__ == "__main__":
    result = run_auto_fix()
    print(f"\n📋 Resultado final:")
    print(f"Sucesso geral: {result['overall_success']}")
    print(f"Total de correções: {result['total_corrections']}")
    print(f"Duração: {result['duration_seconds']:.2f}s")
    if result['details']['errors']:
        print(f"Erros: {len(result['details']['errors'])}")