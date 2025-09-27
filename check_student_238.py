#!/usr/bin/env python3
from app import app
from models import Student

with app.app_context():
    student = Student.query.get(238)
    if student:
        print(f"Estudante 238 encontrado:")
        print(f"Nome: {student.name}")
        print(f"Listening: {student.listening}")
        print(f"Reading: {student.reading}")
        print(f"LFM: {student.lfm}")
        print(f"Total: {student.total}")
        print(f"Created at: {student.created_at}")
    else:
        print("Estudante 238 não encontrado")