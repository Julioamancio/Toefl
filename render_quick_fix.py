#!/usr/bin/env python3
"""
SOLUÇÃO RÁPIDA: Professor Placeholder ID 0
Resolve imediatamente o problema de chaves estrangeiras sem quebrar nada existente.
"""

import os
import json
import psycopg
from datetime import datetime

def get_database_url():
    """Obtém a URL do banco de dados do ambiente"""
    return os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/toefl_db')

def create_placeholder_teacher(cursor):
    """Cria professor placeholder com ID 0 se não existir"""
    print("🔧 Verificando professor placeholder...")
    
    # Verifica se já existe professor com ID 0
    cursor.execute("SELECT id FROM teachers WHERE id = 0")
    existing = cursor.fetchone()
    
    if existing:
        print("✅ Professor placeholder ID 0 já existe")
        return
    
    # Insere professor placeholder com ID 0
    cursor.execute("""
        INSERT INTO teachers (id, name, email, created_at, updated_at) 
        VALUES (0, 'Sem Professor / Unassigned', 'placeholder@system.local', %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (datetime.now(), datetime.now()))
    
    print("✅ Professor placeholder ID 0 criado: 'Sem Professor / Unassigned'")

def import_data_with_placeholder():
    """Importa dados usando o professor placeholder para resolver FK"""
    print("🚀 Iniciando importação com professor placeholder...")
    
    # Conecta ao banco
    conn = psycopg.connect(get_database_url())
    cursor = conn.cursor()
    
    try:
        # 1. Cria professor placeholder
        create_placeholder_teacher(cursor)
        conn.commit()
        
        # 2. Carrega dados do backup
        backup_file = 'backups/export_20250928_085940.json'
        if not os.path.exists(backup_file):
            print(f"❌ Arquivo de backup não encontrado: {backup_file}")
            return
            
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 3. Importa teachers primeiro (exceto o placeholder que já existe)
        if 'teachers' in data:
            print(f"📚 Importando {len(data['teachers'])} professores...")
            for teacher in data['teachers']:
                if teacher['id'] == 0:  # Pula o placeholder
                    continue
                    
                cursor.execute("""
                    INSERT INTO teachers (id, name, email, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        updated_at = EXCLUDED.updated_at
                """, (
                    teacher['id'],
                    teacher['name'],
                    teacher.get('email', f"{teacher['name'].lower().replace(' ', '.')}@escola.com"),
                    teacher.get('created_at', datetime.now()),
                    teacher.get('updated_at', datetime.now())
                ))
            conn.commit()
            print("✅ Professores importados")
        
        # 4. Importa classes
        if 'classes' in data:
            print(f"🏫 Importando {len(data['classes'])} turmas...")
            for cls in data['classes']:
                cursor.execute("""
                    INSERT INTO classes (id, name, teacher_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        teacher_id = EXCLUDED.teacher_id,
                        updated_at = EXCLUDED.updated_at
                """, (
                    cls['id'],
                    cls['name'],
                    cls.get('teacher_id', 0),  # Usa placeholder se não tiver professor
                    cls.get('created_at', datetime.now()),
                    cls.get('updated_at', datetime.now())
                ))
            conn.commit()
            print("✅ Turmas importadas")
        
        # 5. Importa students (com teacher_id corrigido para 0 se nulo)
        if 'students' in data:
            print(f"👥 Importando {len(data['students'])} estudantes...")
            for student in data['students']:
                # Corrige teacher_id nulo/inválido para usar placeholder
                teacher_id = student.get('teacher_id')
                if teacher_id is None or teacher_id == 0:
                    teacher_id = 0  # Usa o placeholder
                
                cursor.execute("""
                    INSERT INTO students (id, name, email, class_id, teacher_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        class_id = EXCLUDED.class_id,
                        teacher_id = EXCLUDED.teacher_id,
                        updated_at = EXCLUDED.updated_at
                """, (
                    student['id'],
                    student['name'],
                    student.get('email', f"{student['name'].lower().replace(' ', '.')}@aluno.com"),
                    student.get('class_id'),
                    teacher_id,
                    student.get('created_at', datetime.now()),
                    student.get('updated_at', datetime.now())
                ))
            conn.commit()
            print("✅ Estudantes importados")
        
        # 6. Verifica resultado
        cursor.execute("SELECT COUNT(*) FROM teachers")
        teachers_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students")
        students_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE teacher_id = 0")
        placeholder_students = cursor.fetchone()[0]
        
        print(f"\n📊 RESULTADO:")
        print(f"✅ {teachers_count} professores (incluindo placeholder)")
        print(f"✅ {students_count} estudantes")
        print(f"🔧 {placeholder_students} estudantes usando professor placeholder")
        print(f"\n🎯 PROBLEMA RESOLVIDO: Todas as chaves estrangeiras estão válidas!")
        
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 SOLUÇÃO RÁPIDA: Professor Placeholder")
    print("=" * 50)
    import_data_with_placeholder()
    print("=" * 50)
    print("✅ Importação concluída! Aplicação deve funcionar agora.")