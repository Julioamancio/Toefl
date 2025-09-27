#!/usr/bin/env python3
"""
Verificar dados de estudante específico na página de detalhes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Student

def check_student_detail():
    """Verificar dados de estudante específico"""
    
    print("🔍 VERIFICAÇÃO DE DADOS DO ESTUDANTE")
    print("=" * 40)
    
    # Configurar a aplicação
    app, csrf = create_app()
    
    with app.app_context():
        # Buscar alguns estudantes para verificar
        print("📊 Verificando dados de estudantes:")
        
        students = Student.query.limit(5).all()
        
        for student in students:
            print(f"\n👤 {student.name} (ID: {student.id})")
            print(f"  - Listening Score: {student.listening}")
            print(f"  - Listening CSA: {student.listening_csa_points}")
            print(f"  - Turma: {student.class_info.name if student.class_info else 'N/A'}")
            print(f"  - Meta Label: {student.class_info.meta_label if student.class_info else 'N/A'}")
            print(f"  - Updated At: {student.updated_at}")
        
        # Verificar se há algum problema de cache
        print("\n🔄 Forçando refresh dos dados...")
        db.session.expire_all()
        
        # Verificar novamente após refresh
        print("\n📊 Dados após refresh:")
        students_refreshed = Student.query.limit(5).all()
        
        for student in students_refreshed:
            print(f"\n👤 {student.name} (ID: {student.id})")
            print(f"  - Listening Score: {student.listening}")
            print(f"  - Listening CSA: {student.listening_csa_points}")
            print(f"  - Turma: {student.class_info.name if student.class_info else 'N/A'}")
            print(f"  - Meta Label: {student.class_info.meta_label if student.class_info else 'N/A'}")
        
        # Verificar estatísticas gerais
        print("\n📈 Estatísticas gerais:")
        total_students = Student.query.count()
        zero_csa = Student.query.filter(Student.listening_csa_points == 0.0).count()
        positive_csa = Student.query.filter(Student.listening_csa_points > 0.0).count()
        null_csa = Student.query.filter(Student.listening_csa_points.is_(None)).count()
        
        print(f"  - Total de estudantes: {total_students}")
        print(f"  - CSA = 0: {zero_csa}")
        print(f"  - CSA > 0: {positive_csa}")
        print(f"  - CSA = NULL: {null_csa}")
    
    print("\n🏁 VERIFICAÇÃO CONCLUÍDA!")

if __name__ == '__main__':
    check_student_detail()