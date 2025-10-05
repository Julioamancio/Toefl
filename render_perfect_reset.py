#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar reset perfeito do banco de dados no Render
Recria completamente o banco com dados do backup
"""

import os
import json
import sqlite3
from datetime import datetime

def get_database_url():
    """Obtém a URL do banco de dados do ambiente"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Se não há DATABASE_URL, usar SQLite local
        return 'sqlite:///toefl_dashboard.db'
    return database_url

def is_sqlite_database():
    """Verifica se está usando SQLite"""
    url = get_database_url()
    return url.startswith('sqlite:')

def drop_all_tables(cursor):
    """Remove todas as tabelas existentes"""
    print("🗑️ Removendo todas as tabelas existentes...")
    
    # Lista de tabelas na ordem correta para remoção (dependências primeiro)
    tables = [
        'students', 'classes', 'teachers', 'users', 
        'certificate_layouts', 'alembic_version'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"   ✅ Tabela {table} removida")
        except Exception as e:
            print(f"   ⚠️ Erro ao remover {table}: {e}")

def create_perfect_schema(cursor):
    """Cria schema perfeito com regras corretas"""
    print("🏗️ Criando schema perfeito...")
    
    # 1. Tabela Users (admin)
    cursor.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_teacher BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    print("   ✅ Tabela users criada")
    
    # 2. Tabela Teachers (PRIMEIRO - sem dependências)
    cursor.execute("""
        CREATE TABLE teachers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(120),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Tabela teachers criada")
    
    # 3. Tabela Classes (depende de teachers)
    cursor.execute("""
        CREATE TABLE classes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            meta_label VARCHAR(10),
            teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Tabela classes criada")
    
    # 4. Tabela Students (depende de teachers e classes) - COM REGRA CORRETA
    cursor.execute("""
        CREATE TABLE students (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            student_number VARCHAR(50) UNIQUE NOT NULL,
            
            -- Campos de notas/resultados
            listening INTEGER,
            list_cefr VARCHAR(10),
            lfm INTEGER,
            lfm_cefr VARCHAR(10),
            reading INTEGER,
            read_cefr VARCHAR(10),
            lexile VARCHAR(20),
            total INTEGER,
            cefr_geral VARCHAR(10),
            listening_csa_points FLOAT,
            
            -- Campo individual para rótulo escolar
            turma_meta VARCHAR(10),
            
            -- Relacionamentos - TEACHER_ID OPCIONAL (permite NULL)
            class_id INTEGER REFERENCES classes(id) ON DELETE SET NULL,
            teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
            
            -- Auditoria
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Tabela students criada (teacher_id OPCIONAL)")
    
    # 5. Tabela Certificate Layouts
    cursor.execute("""
        CREATE TABLE certificate_layouts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            layout_data TEXT NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Tabela certificate_layouts criada")

def create_admin_user(cursor):
    """Cria usuário admin padrão"""
    print("👤 Criando usuário admin...")
    
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash('admin123')
    
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_admin, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
    """, ('admin', 'admin@escola.com', password_hash, True, True))
    
    print("   ✅ Admin criado: username=admin, password=admin123")

def import_perfect_data(cursor):
    """Importa dados na ordem perfeita com validações"""
    print("📊 Importando dados na ordem perfeita...")
    
    # Carrega backup
    backup_file = 'backups/export_20250928_085940.json'
    if not os.path.exists(backup_file):
        print(f"❌ Arquivo de backup não encontrado: {backup_file}")
        return
        
    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. TEACHERS PRIMEIRO (base de tudo)
    if 'teachers' in data:
        print(f"   📚 Importando {len(data['teachers'])} professores...")
        for teacher in data['teachers']:
            cursor.execute("""
                INSERT INTO teachers (id, name, email, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    email = EXCLUDED.email,
                    updated_at = EXCLUDED.updated_at
            """, (
                teacher['id'],
                teacher['name'],
                teacher.get('email', f"{teacher['name'].lower().replace(' ', '.')}@escola.com"),
                teacher.get('created_at', datetime.now()),
                teacher.get('updated_at', datetime.now())
            ))
        print("   ✅ Professores importados")
    
    # 2. CLASSES (com teacher_id válido)
    if 'classes' in data:
        print(f"   🏫 Importando {len(data['classes'])} turmas...")
        for cls in data['classes']:
            # Valida se teacher_id existe
            teacher_id = cls.get('teacher_id')
            if teacher_id:
                cursor.execute("SELECT id FROM teachers WHERE id = %s", (teacher_id,))
                if not cursor.fetchone():
                    print(f"   ⚠️ Teacher ID {teacher_id} não encontrado, definindo como NULL")
                    teacher_id = None
            
            cursor.execute("""
                INSERT INTO classes (id, name, description, meta_label, teacher_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    meta_label = EXCLUDED.meta_label,
                    teacher_id = EXCLUDED.teacher_id,
                    updated_at = EXCLUDED.updated_at
            """, (
                cls['id'],
                cls['name'],
                cls.get('description'),
                cls.get('meta_label'),
                teacher_id,
                cls.get('created_at', datetime.now()),
                cls.get('updated_at', datetime.now())
            ))
        print("   ✅ Turmas importadas")
    
    # 3. STUDENTS (com validação de FKs)
    if 'students' in data:
        print(f"   👥 Importando {len(data['students'])} estudantes...")
        
        valid_students = 0
        invalid_teachers = 0
        invalid_classes = 0
        
        for student in data['students']:
            # Valida teacher_id (OPCIONAL - pode ser NULL)
            teacher_id = student.get('teacher_id')
            if teacher_id is not None and teacher_id != 0:
                cursor.execute("SELECT id FROM teachers WHERE id = %s", (teacher_id,))
                if not cursor.fetchone():
                    print(f"   ⚠️ Student {student['name']}: teacher_id {teacher_id} inválido, definindo como NULL")
                    teacher_id = None
                    invalid_teachers += 1
            else:
                teacher_id = None  # NULL é permitido
            
            # Valida class_id (OPCIONAL)
            class_id = student.get('class_id')
            if class_id:
                cursor.execute("SELECT id FROM classes WHERE id = %s", (class_id,))
                if not cursor.fetchone():
                    print(f"   ⚠️ Student {student['name']}: class_id {class_id} inválido, definindo como NULL")
                    class_id = None
                    invalid_classes += 1
            
            # Gera student_number se não existir
            student_number = student.get('student_number', f"STU{student['id']:04d}")
            
            cursor.execute("""
                INSERT INTO students (
                    id, name, student_number,
                    listening, list_cefr, lfm, lfm_cefr, reading, read_cefr,
                    lexile, total, cefr_geral, listening_csa_points, turma_meta,
                    class_id, teacher_id, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    student_number = EXCLUDED.student_number,
                    listening = EXCLUDED.listening,
                    list_cefr = EXCLUDED.list_cefr,
                    lfm = EXCLUDED.lfm,
                    lfm_cefr = EXCLUDED.lfm_cefr,
                    reading = EXCLUDED.reading,
                    read_cefr = EXCLUDED.read_cefr,
                    lexile = EXCLUDED.lexile,
                    total = EXCLUDED.total,
                    cefr_geral = EXCLUDED.cefr_geral,
                    listening_csa_points = EXCLUDED.listening_csa_points,
                    turma_meta = EXCLUDED.turma_meta,
                    class_id = EXCLUDED.class_id,
                    teacher_id = EXCLUDED.teacher_id,
                    updated_at = EXCLUDED.updated_at
            """, (
                student['id'],
                student['name'],
                student_number,
                student.get('listening'),
                student.get('list_cefr'),
                student.get('lfm'),
                student.get('lfm_cefr'),
                student.get('reading'),
                student.get('read_cefr'),
                student.get('lexile'),
                student.get('total'),
                student.get('cefr_geral'),
                student.get('listening_csa_points'),
                student.get('turma_meta'),
                class_id,
                teacher_id,
                student.get('created_at', datetime.now()),
                student.get('updated_at', datetime.now())
            ))
            valid_students += 1
        
        print(f"   ✅ {valid_students} estudantes importados")
        if invalid_teachers > 0:
            print(f"   ⚠️ {invalid_teachers} estudantes com teacher_id corrigido para NULL")
        if invalid_classes > 0:
            print(f"   ⚠️ {invalid_classes} estudantes com class_id corrigido para NULL")

def create_default_certificate_layout(cursor):
    """Cria layout de certificado padrão"""
    print("📜 Criando layout de certificado padrão...")
    
    default_layout = {
        "template": "default",
        "fields": {
            "student_name": {"x": 400, "y": 300, "font_size": 24},
            "course_name": {"x": 400, "y": 350, "font_size": 18},
            "date": {"x": 400, "y": 400, "font_size": 16}
        }
    }
    
    cursor.execute("""
        INSERT INTO certificate_layouts (name, layout_data, is_default)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, ('Layout Padrão', json.dumps(default_layout), True))
    
    print("   ✅ Layout padrão criado")

def verify_perfect_import(cursor):
    """Verifica se a importação foi perfeita"""
    print("🔍 Verificando importação perfeita...")
    
    # Conta registros
    cursor.execute("SELECT COUNT(*) FROM teachers")
    teachers_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM classes")
    classes_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM students")
    students_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM students WHERE teacher_id IS NULL")
    students_no_teacher = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM students WHERE class_id IS NULL")
    students_no_class = cursor.fetchone()[0]
    
    # Verifica integridade referencial
    cursor.execute("""
        SELECT COUNT(*) FROM students s 
        WHERE s.teacher_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM teachers t WHERE t.id = s.teacher_id)
    """)
    invalid_teacher_refs = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM students s 
        WHERE s.class_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM classes c WHERE c.id = s.class_id)
    """)
    invalid_class_refs = cursor.fetchone()[0]
    
    print(f"\n📊 RESULTADO DA IMPORTAÇÃO PERFEITA:")
    print(f"   ✅ {teachers_count} professores")
    print(f"   ✅ {classes_count} turmas")
    print(f"   ✅ {students_count} estudantes")
    print(f"   📝 {students_no_teacher} estudantes sem professor (permitido)")
    print(f"   📝 {students_no_class} estudantes sem turma (permitido)")
    
    if invalid_teacher_refs == 0 and invalid_class_refs == 0:
        print(f"   🎯 INTEGRIDADE PERFEITA: Todas as chaves estrangeiras válidas!")
        return True
    else:
        print(f"   ❌ {invalid_teacher_refs} referências inválidas para teachers")
        print(f"   ❌ {invalid_class_refs} referências inválidas para classes")
        return False

def perfect_reset():
    """Executa reset perfeito completo"""
    print("🚀 INICIANDO RESET PERFEITO DO BANCO DE DADOS")
    print("=" * 60)
    
    # Usar Flask app para reset em vez de conexão direta
    try:
        from app import create_app
        from models import db
        
        # Criar aplicação Flask
        app, csrf = create_app()
        
        with app.app_context():
            print("🗑️ Removendo todas as tabelas...")
            db.drop_all()
            
            print("🏗️ Criando schema do banco...")
            db.create_all()
            
            print("👤 Criando usuário admin...")
            create_admin_user()
            
            print("📥 Importando dados do backup...")
            success = import_backup_data()
            
            if success:
                print("✅ RESET PERFEITO CONCLUÍDO COM SUCESSO!")
                print("🎉 Banco de dados recriado e dados importados!")
                return True
            else:
                print("❌ Erro durante a importação dos dados")
                return False
    except Exception as e:
        print(f"❌ ERRO DURANTE O RESET: {e}")
        return False

def create_admin_user():
    """Cria usuário admin usando Flask models"""
    from models import User, db
    from datetime import datetime
    
    # Verificar se admin já existe
    existing_admin = User.query.filter_by(username='admin').first()
    if existing_admin:
        print("ℹ️ Usuário admin já existe")
        return
    
    # Criar novo admin
    admin = User(
        username='admin',
        email='admin@toefl.com',
        is_admin=True,
        is_active=True,
        created_at=datetime.utcnow()
    )
    admin.set_password('admin123')
    
    db.session.add(admin)
    db.session.commit()
    print("✅ Usuário admin criado com sucesso")

def import_backup_data():
    """Importa dados do backup usando o sistema existente"""
    try:
        # Procurar arquivo de backup mais recente
        backup_files = []
        if os.path.exists('backups'):
            for file in os.listdir('backups'):
                if file.endswith('.json'):
                    backup_files.append(os.path.join('backups', file))
        
        if not backup_files:
            print("⚠️ Nenhum arquivo de backup encontrado")
            return True  # Não é erro crítico
        
        # Usar o backup mais recente
        latest_backup = max(backup_files, key=os.path.getmtime)
        print(f"📂 Usando backup: {latest_backup}")
        
        # Importar usando o sistema existente
        from database_backup import import_data_json
        result = import_data_json(latest_backup)
        
        if result.get('success', False):
            print("✅ Dados importados com sucesso")
            return True
        else:
            print(f"❌ Erro na importação: {result.get('message', 'Erro desconhecido')}")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        return False

if __name__ == "__main__":
    success = perfect_reset()
    if success:
        print("🎉 Reset perfeito concluído com sucesso!")
    else:
        print("❌ Reset falhou")
        exit(1)