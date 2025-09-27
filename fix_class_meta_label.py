#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir turmas sem meta_label

Este script:
1. Identifica turmas sem meta_label
2. Sugere meta_label baseado no nome da turma
3. Permite correção automática ou manual
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Class, Student

def suggest_meta_label(class_name):
    """
    Sugere um meta_label baseado no nome da turma
    """
    if not class_name:
        return '6.2'  # Padrão
    
    class_name_lower = class_name.lower()
    
    # Verifica se é turma de 6° ano
    if '6' in class_name_lower and ('ano' in class_name_lower or '°' in class_name_lower):
        return '6.2'  # Padrão para 6° ano
    
    # Verifica se é turma de 9° ano  
    if '9' in class_name_lower and ('ano' in class_name_lower or '°' in class_name_lower):
        return '9.2'  # Padrão para 9° ano
    
    # Se não conseguir identificar, usa padrão mais comum
    return '6.2'

def fix_classes_without_meta_label():
    """
    Corrige turmas sem meta_label
    """
    # Criar aplicação Flask
    app_tuple = create_app()
    app = app_tuple[0] if isinstance(app_tuple, tuple) else app_tuple
    
    with app.app_context():
        print("🔍 VERIFICANDO TURMAS SEM META_LABEL")
        print("=" * 50)
        
        # Buscar turmas sem meta_label
        classes_without_meta = Class.query.filter(
            (Class.meta_label == None) | (Class.meta_label == '')
        ).all()
        
        if not classes_without_meta:
            print("✅ Todas as turmas já possuem meta_label configurado!")
            return
        
        print(f"❌ Encontradas {len(classes_without_meta)} turmas sem meta_label:")
        print()
        
        for class_obj in classes_without_meta:
            # Contar estudantes na turma
            student_count = Student.query.filter_by(class_id=class_obj.id).count()
            suggested_label = suggest_meta_label(class_obj.name)
            
            print(f"📚 Turma ID {class_obj.id}: {class_obj.name}")
            print(f"   • Estudantes: {student_count}")
            print(f"   • Meta_label atual: {class_obj.meta_label or 'VAZIO'}")
            print(f"   • Meta_label sugerido: {suggested_label}")
            print()
        
        # Correção automática (sem interação manual para funcionar no Render.com)
        print("\n🔄 APLICANDO CORREÇÕES AUTOMÁTICAS...")
        corrections_made = 0
        
        for class_obj in classes_without_meta:
            suggested_label = suggest_meta_label(class_obj.name)
            class_obj.meta_label = suggested_label
            corrections_made += 1
            print(f"   ✅ {class_obj.name} → meta_label: {suggested_label}")
        
        try:
            db.session.commit()
            print(f"\n💾 {corrections_made} turmas corrigidas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao salvar correções: {str(e)}")
            return
        
        # Verificar se ainda há estudantes com problemas
        print("\n🔍 VERIFICANDO ESTUDANTES AFETADOS...")
        students_with_issues = []
        
        for class_obj in classes_without_meta:
            if class_obj.meta_label:  # Se foi corrigido
                students = Student.query.filter_by(class_id=class_obj.id).all()
                for student in students:
                    if student.listening and not student.listening_csa_points:
                        students_with_issues.append(student)
        
        if students_with_issues:
            print(f"⚠️  {len(students_with_issues)} estudantes precisam recalcular o CSA")
            print("💡 Execute: python fix_listening_csa_automatic.py")
        else:
            print("✅ Todos os estudantes estão OK!")

if __name__ == '__main__':
    fix_classes_without_meta_label()