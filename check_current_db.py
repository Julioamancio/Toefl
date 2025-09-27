#!/usr/bin/env python3
"""
Script para verificar o status atual do banco de dados Flask
"""

import os
import sys
from flask import Flask
from models import db, Student, Class, Teacher, User

def check_flask_database():
    """Verifica o banco de dados Flask atual"""
    
    # Configurar Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///toefl_dashboard.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        print("🔍 VERIFICANDO BANCO DE DADOS FLASK")
        print("=" * 50)
        
        # Verificar se o arquivo existe
        db_file = 'toefl_dashboard.db'
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"✅ Arquivo: {db_file}")
            print(f"📏 Tamanho: {size} bytes")
        else:
            print(f"❌ Arquivo {db_file} não encontrado!")
            return
        
        try:
            # Contar registros
            users_count = User.query.count()
            teachers_count = Teacher.query.count()
            classes_count = Class.query.count()
            students_count = Student.query.count()
            
            print(f"\n📊 CONTAGEM DE REGISTROS:")
            print(f"   👥 Usuários: {users_count}")
            print(f"   👨‍🏫 Professores: {teachers_count}")
            print(f"   🏫 Turmas: {classes_count}")
            print(f"   👨‍🎓 Estudantes: {students_count}")
            
            # Verificar estudantes com pontuações
            students_with_scores = Student.query.filter(Student.listening_score.isnot(None)).count()
            students_with_grades = Student.query.filter(Student.listening_grade.isnot(None)).count()
            
            print(f"\n🎯 ESTUDANTES COM DADOS:")
            print(f"   🎧 Com pontuação Listening: {students_with_scores}")
            print(f"   📝 Com nota calculada: {students_with_grades}")
            
            # Mostrar alguns exemplos
            print(f"\n📋 PRIMEIROS 10 ESTUDANTES:")
            students = Student.query.limit(10).all()
            for student in students:
                class_name = student.class_info.name if student.class_info else "Sem turma"
                score = student.listening_score or "N/A"
                grade = student.listening_grade or "N/A"
                print(f"   👤 {student.name} → {class_name} (Score: {score}, Nota: {grade})")
                
        except Exception as e:
            print(f"❌ Erro ao acessar banco: {e}")

if __name__ == "__main__":
    check_flask_database()