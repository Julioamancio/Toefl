#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para popular a tabela ComputedLevel com dados dos estudantes existentes
"""

from app import app
from models import db, Student, ComputedLevel
from models import calculate_student_levels

def populate_computed_levels():
    """Popula a tabela ComputedLevel para todos os estudantes existentes"""
    
    with app.app_context():
        print("🔄 Iniciando população da tabela ComputedLevel...")
        
        # Buscar todos os estudantes
        students = Student.query.all()
        total_students = len(students)
        
        print(f"📊 Encontrados {total_students} estudantes")
        
        # Verificar quantos já têm ComputedLevel
        existing_computed = ComputedLevel.query.count()
        print(f"📋 Já existem {existing_computed} registros em ComputedLevel")
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for i, student in enumerate(students, 1):
            try:
                # Verificar se já existe ComputedLevel para este estudante
                existing = ComputedLevel.query.filter_by(student_id=student.id).first()
                
                # Calcular níveis
                levels, applied_rules = calculate_student_levels(student)
                
                if existing:
                    # Atualizar existente
                    existing.school_level = levels.get('school_level')
                    existing.listening_level = levels.get('listening_level')
                    existing.lfm_level = levels.get('lfm_level')
                    existing.reading_level = levels.get('reading_level')
                    existing.overall_level = levels.get('overall_level')
                    existing.applied_rules = '; '.join(applied_rules)
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
                    created_count += 1
                
                # Commit a cada 50 estudantes para evitar problemas de memória
                if i % 50 == 0:
                    db.session.commit()
                    print(f"   ✅ Processados {i}/{total_students} estudantes...")
                    
            except Exception as e:
                error_count += 1
                print(f"   ❌ Erro ao processar estudante {student.name} (ID: {student.id}): {str(e)}")
                continue
        
        # Commit final
        try:
            db.session.commit()
            print(f"\n✅ População concluída!")
            print(f"   • Criados: {created_count} registros")
            print(f"   • Atualizados: {updated_count} registros")
            print(f"   • Erros: {error_count} registros")
            
            # Verificar resultado final
            final_count = ComputedLevel.query.count()
            print(f"   • Total final em ComputedLevel: {final_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro no commit final: {str(e)}")

if __name__ == "__main__":
    populate_computed_levels()