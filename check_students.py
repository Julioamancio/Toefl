#!/usr/bin/env python3
"""
Script para verificar estudantes no banco de dados
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Criar app Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inicializar banco
db = SQLAlchemy(app)

# Importar modelos
from models import Student

def check_students():
    """Verifica quantos estudantes existem no banco"""
    with app.app_context():
        try:
            total = Student.query.count()
            print(f"📊 Total de estudantes no banco: {total}")
            
            if total > 0:
                print("\n👥 Primeiros 5 estudantes:")
                students = Student.query.limit(5).all()
                for student in students:
                    print(f"   ID: {student.id} | Nome: {student.name} | Número: {student.student_number}")
                
                # Verificar se há estudante com ID específico para teste
                test_student = Student.query.filter_by(id=497).first()
                if test_student:
                    print(f"\n🎯 Estudante ID 497 encontrado: {test_student.name}")
                else:
                    print(f"\n❌ Estudante ID 497 não encontrado")
                    # Mostrar primeiro estudante disponível
                    first_student = Student.query.first()
                    if first_student:
                        print(f"✅ Use o ID {first_student.id} para testar (Nome: {first_student.name})")
            else:
                print("❌ Nenhum estudante encontrado no banco!")
                print("💡 Você precisa importar dados de estudantes primeiro.")
                
        except Exception as e:
            print(f"❌ Erro ao consultar banco: {e}")

if __name__ == '__main__':
    check_students()