#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para completar as turmas faltantes de 6º e 9º ano
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Student, Class, Teacher

def complete_missing_classes():
    """Completa as turmas faltantes de 6º e 9º ano"""
    
    with app.app_context():
        print("🏫 Completando turmas faltantes...")
        
        # Verificar turmas existentes
        existing_classes = Class.query.all()
        existing_names = [c.name for c in existing_classes]
        print(f"📊 Turmas existentes ({len(existing_classes)}): {existing_names}")
        
        # Turmas faltantes de 6º ano
        missing_6th = []
        for letter in ['E', 'F', 'G', 'H']:
            class_name = f"6° ano {letter}"
            if class_name not in existing_names:
                missing_6th.append(letter)
        
        # Turmas faltantes de 9º ano
        missing_9th = []
        for letter in ['E', 'F', 'G']:
            class_name = f"9° ano {letter}"
            if class_name not in existing_names:
                missing_9th.append(letter)
        
        print(f"🔍 Faltam criar:")
        print(f"   • 6º ano: {missing_6th}")
        print(f"   • 9º ano: {missing_9th}")
        
        # Criar turmas faltantes de 6º ano
        created_6th = 0
        for letter in missing_6th:
            class_name = f"6° ano {letter}"
            class_info = Class(
                name=class_name,
                description=f"Turma de 6º ano - {letter}"
            )
            db.session.add(class_info)
            created_6th += 1
            print(f"   ✅ Turma {class_name} criada")
        
        # Criar turmas faltantes de 9º ano
        created_9th = 0
        for letter in missing_9th:
            class_name = f"9° ano {letter}"
            class_info = Class(
                name=class_name,
                description=f"Turma de 9º ano - {letter}"
            )
            db.session.add(class_info)
            created_9th += 1
            print(f"   ✅ Turma {class_name} criada")
        
        db.session.commit()
        
        # Verificar resultado final
        final_classes = Class.query.all()
        final_names = sorted([c.name for c in final_classes])
        
        print(f"\n🎉 Turmas criadas com sucesso!")
        print(f"   • {created_6th} novas turmas de 6º ano")
        print(f"   • {created_9th} novas turmas de 9º ano")
        print(f"   • Total final: {len(final_classes)} turmas")
        
        print(f"\n📋 Todas as turmas ({len(final_classes)}):")
        sixth_grade = [name for name in final_names if '6°' in name]
        ninth_grade = [name for name in final_names if '9°' in name]
        
        print(f"   6º ano ({len(sixth_grade)}): {sixth_grade}")
        print(f"   9º ano ({len(ninth_grade)}): {ninth_grade}")
        
        # Verificar se temos todas as turmas esperadas
        expected_6th = [f"6° ano {letter}" for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']]
        expected_9th = [f"9° ano {letter}" for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G']]
        
        missing_final_6th = [name for name in expected_6th if name not in final_names]
        missing_final_9th = [name for name in expected_9th if name not in final_names]
        
        if missing_final_6th or missing_final_9th:
            print(f"\n⚠️  AINDA FALTAM:")
            if missing_final_6th:
                print(f"   • 6º ano: {missing_final_6th}")
            if missing_final_9th:
                print(f"   • 9º ano: {missing_final_9th}")
        else:
            print(f"\n✅ PERFEITO! Todas as 15 turmas foram criadas:")
            print(f"   • 8 turmas de 6º ano (A-H)")
            print(f"   • 7 turmas de 9º ano (A-G)")

if __name__ == '__main__':
    complete_missing_classes()