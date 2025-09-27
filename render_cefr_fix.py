#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para correção automática de níveis CEFR
Para ser executado via botão administrativo
"""

import time
from datetime import datetime
from app import app
from models import db, Student, ComputedLevel, calculate_student_levels

def run_cefr_fix():
    """
    Executa a correção automática de níveis CEFR
    Retorna um dicionário com o resultado da operação
    """
    start_time = time.time()
    
    try:
        with app.app_context():
            print("🔄 Iniciando correção automática de níveis CEFR...")
            
            # Buscar todos os estudantes
            students = Student.query.all()
            total_students = len(students)
            
            print(f"📊 Total de estudantes encontrados: {total_students}")
            
            updated_count = 0
            created_count = 0
            error_count = 0
            
            for i, student in enumerate(students, 1):
                try:
                    # Calcular níveis usando a função do modelo
                    levels, applied_rules = calculate_student_levels(student)
                    
                    # Buscar ou criar ComputedLevel
                    computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
                    
                    if computed_level:
                        # Atualizar existente
                        old_overall = computed_level.overall_level
                        computed_level.school_level = levels.get('school_level')
                        computed_level.listening_level = levels.get('listening_level')
                        computed_level.lfm_level = levels.get('lfm_level')
                        computed_level.reading_level = levels.get('reading_level')
                        computed_level.overall_level = levels.get('overall_level')
                        computed_level.applied_rules = '; '.join(applied_rules)
                        computed_level.updated_at = datetime.utcnow()
                        
                        if old_overall != computed_level.overall_level:
                            print(f"  ✅ {student.name} ({student.student_number}): {old_overall} → {computed_level.overall_level}")
                            updated_count += 1
                    else:
                        # Criar novo
                        computed_level = ComputedLevel(
                            student_id=student.id,
                            school_level=levels.get('school_level'),
                            listening_level=levels.get('listening_level'),
                            lfm_level=levels.get('lfm_level'),
                            reading_level=levels.get('reading_level'),
                            overall_level=levels.get('overall_level'),
                            applied_rules='; '.join(applied_rules)
                        )
                        db.session.add(computed_level)
                        print(f"  🆕 {student.name} ({student.student_number}): Novo → {computed_level.overall_level}")
                        created_count += 1
                    
                    # Commit a cada 50 estudantes para evitar problemas de memória
                    if i % 50 == 0:
                        db.session.commit()
                        print(f"  📈 Progresso: {i}/{total_students} estudantes processados")
                        
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Erro ao processar {student.name}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            end_time = time.time()
            execution_time = round(end_time - start_time, 2)
            
            print("\n✅ Correção de níveis CEFR concluída!")
            print(f"📊 Total de estudantes processados: {total_students}")
            print(f"🔄 Níveis atualizados: {updated_count}")
            print(f"🆕 Níveis criados: {created_count}")
            print(f"❌ Erros encontrados: {error_count}")
            print(f"⏱️ Tempo de execução: {execution_time}s")
            
            return {
                'success': True,
                'message': 'Correção de níveis CEFR executada com sucesso!',
                'details': {
                    'total_students': total_students,
                    'updated_count': updated_count,
                    'created_count': created_count,
                    'error_count': error_count,
                    'execution_time': execution_time
                }
            }
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro durante a correção de níveis CEFR: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            'success': False,
            'message': error_msg,
            'details': {}
        }

if __name__ == "__main__":
    result = run_cefr_fix()
    if result['success']:
        print("\n🎉 Script executado com sucesso!")
    else:
        print(f"\n💥 Falha na execução: {result['message']}")