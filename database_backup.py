#!/usr/bin/env python3
"""
Script para backup e restore do banco de dados TOEFL Dashboard
Suporta SQLite (desenvolvimento) e PostgreSQL (produção)
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
import argparse

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def get_database_type():
    """Detecta o tipo de banco de dados baseado na configuração"""
    app, csrf = create_app()
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite'):
            return 'sqlite'
        elif db_uri.startswith('postgresql'):
            return 'postgresql'
        else:
            raise ValueError(f"Tipo de banco não suportado: {db_uri}")

def backup_sqlite(backup_path):
    """Faz backup do banco SQLite"""
    app, csrf = create_app()
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            print(f"Erro: Banco de dados não encontrado em {db_path}")
            return False
        
        # Criar diretório de backup se não existir
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copiar arquivo do banco
        import shutil
        shutil.copy2(db_path, backup_path)
        
        print(f"Backup SQLite criado: {backup_path}")
        return True

def restore_sqlite(backup_path):
    """Restaura backup do banco SQLite"""
    if not os.path.exists(backup_path):
        print(f"Erro: Arquivo de backup não encontrado: {backup_path}")
        return False
    
    app, csrf = create_app()
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '')
        
        # Fazer backup do banco atual antes de restaurar
        if os.path.exists(db_path):
            backup_current = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(db_path, backup_current)
            print(f"Backup do banco atual criado: {backup_current}")
        
        # Restaurar o backup
        import shutil
        shutil.copy2(backup_path, db_path)
        
        print(f"Banco restaurado de: {backup_path}")
        return True

def backup_postgresql(backup_path):
    """Faz backup do banco PostgreSQL usando pg_dump"""
    try:
        app, csrf = create_app()
        with app.app_context():
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            
            # Extrair informações da URI do PostgreSQL
            # postgresql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(db_uri)
            
            # Criar diretório de backup se não existir
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Comando pg_dump
            cmd = [
                'pg_dump',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path[1:],  # Remove a barra inicial
                '-f', backup_path,
                '--verbose'
            ]
            
            # Definir senha via variável de ambiente
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Backup PostgreSQL criado: {backup_path}")
                return True
            else:
                print(f"Erro ao criar backup PostgreSQL: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"Erro ao fazer backup PostgreSQL: {str(e)}")
        return False

def restore_postgresql(backup_path):
    """Restaura backup do banco PostgreSQL usando psql"""
    try:
        if not os.path.exists(backup_path):
            print(f"Erro: Arquivo de backup não encontrado: {backup_path}")
            return False
        
        app, csrf = create_app()
        with app.app_context():
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            
            # Extrair informações da URI do PostgreSQL
            import urllib.parse
            parsed = urllib.parse.urlparse(db_uri)
            
            # Comando psql
            cmd = [
                'psql',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path[1:],  # Remove a barra inicial
                '-f', backup_path,
                '--verbose'
            ]
            
            # Definir senha via variável de ambiente
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Banco PostgreSQL restaurado de: {backup_path}")
                return True
            else:
                print(f"Erro ao restaurar PostgreSQL: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"Erro ao restaurar PostgreSQL: {str(e)}")
        return False

def export_data_json(export_path):
    """Exporta dados para um arquivo JSON"""
    try:
        # Criar contexto da aplicação
        app, csrf = create_app()
        
        # Importar e inicializar db dentro do contexto
        from models import db
        
        with app.app_context():
            # Importar modelos dentro do contexto da aplicação
            from models import Student, Teacher, Class, ComputedLevel
            
            # Coletar dados
            students = []
            for student in Student.query.all():
                students.append({
                    'id': student.id,
                    'name': student.name,
                    'student_number': student.student_number,
                    'listening': student.listening,
                    'list_cefr': student.list_cefr,
                    'lfm': student.lfm,
                    'lfm_cefr': student.lfm_cefr,
                    'reading': student.reading,
                    'read_cefr': student.read_cefr,
                    'lexile': student.lexile,
                    'total': student.total,
                    'cefr_geral': student.cefr_geral,
                    'listening_csa_points': student.listening_csa_points,
                    'class_id': student.class_id,
                    'teacher_id': student.teacher_id,
                    'created_at': student.created_at.isoformat() if student.created_at else None,
                    'updated_at': student.updated_at.isoformat() if student.updated_at else None
                })
            
            teachers = []
            for teacher in Teacher.query.all():
                teachers.append({
                    'id': teacher.id,
                    'name': teacher.name,
                    'created_at': teacher.created_at.isoformat() if teacher.created_at else None
                })
            
            classes = []
            for class_obj in Class.query.all():
                classes.append({
                    'id': class_obj.id,
                    'name': class_obj.name,
                    'description': class_obj.description,
                    'meta_label': class_obj.meta_label,
                    'is_active': class_obj.is_active,
                    'created_at': class_obj.created_at.isoformat() if class_obj.created_at else None
                })
            
            computed_levels = []
            for level in ComputedLevel.query.all():
                computed_levels.append({
                    'id': level.id,
                    'student_id': level.student_id,
                    'school_level': level.school_level,
                    'listening_level': level.listening_level,
                    'lfm_level': level.lfm_level,
                    'reading_level': level.reading_level,
                    'overall_level': level.overall_level,
                    'applied_rules': level.applied_rules,
                    'created_at': level.created_at.isoformat() if level.created_at else None,
                    'updated_at': level.updated_at.isoformat() if level.updated_at else None
                })
            
            # Criar estrutura de dados
            data = {
                'export_date': datetime.now().isoformat(),
                'students': students,
                'teachers': teachers,
                'classes': classes,
                'computed_levels': computed_levels
            }
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            # Salvar arquivo JSON
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Dados exportados para: {export_path}")
            print(f"Estudantes: {len(students)}")
            print(f"Professores: {len(teachers)}")
            print(f"Classes: {len(classes)}")
            print(f"Níveis computados: {len(computed_levels)}")
            return True
            
    except Exception as e:
        print(f"Erro ao exportar dados: {str(e)}")
        return False

def import_data_json(import_path):
    """Importa dados de um arquivo JSON"""
    try:
        print(f"DEBUG: Iniciando importação de {import_path}")
        
        # Criar contexto da aplicação
        app, csrf = create_app()
        
        # Importar e inicializar db dentro do contexto
        from models import db
        
        with app.app_context():
            print("DEBUG: Contexto da aplicação criado")
            
            # Importar modelos dentro do contexto da aplicação
            from models import Student, Teacher, Class, ComputedLevel
            
            if not os.path.exists(import_path):
                print(f"Arquivo não encontrado: {import_path}")
                return False
            
            print("DEBUG: Carregando arquivo JSON")
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"DEBUG: Dados carregados - Students: {len(data.get('students', []))}, Teachers: {len(data.get('teachers', []))}, Classes: {len(data.get('classes', []))}")
            
            # Limpar dados existentes
            print("DEBUG: Limpando dados existentes")
            ComputedLevel.query.delete()
            Student.query.delete()
            Class.query.delete()
            Teacher.query.delete()
            
            # Importar professores primeiro (devido às chaves estrangeiras)
            print("DEBUG: Importando professores")
            for teacher_data in data.get('teachers', []):
                teacher = Teacher(
                    name=teacher_data['name'],
                    created_at=datetime.fromisoformat(teacher_data['created_at']) if teacher_data.get('created_at') else None
                )
                teacher.id = teacher_data['id']
                db.session.add(teacher)
            
            # Importar classes
            print("DEBUG: Importando classes")
            for class_data in data.get('classes', []):
                class_obj = Class(
                    name=class_data['name'],
                    description=class_data.get('description'),
                    meta_label=class_data.get('meta_label'),
                    is_active=class_data.get('is_active', True),
                    created_at=datetime.fromisoformat(class_data['created_at']) if class_data.get('created_at') else None
                )
                class_obj.id = class_data['id']
                db.session.add(class_obj)
            
            # Importar estudantes
            print("DEBUG: Importando estudantes")
            for student_data in data.get('students', []):
                student = Student(
                    name=student_data['name'],
                    student_number=student_data.get('student_number'),
                    listening=student_data.get('listening'),
                    list_cefr=student_data.get('list_cefr'),
                    lfm=student_data.get('lfm'),
                    lfm_cefr=student_data.get('lfm_cefr'),
                    reading=student_data.get('reading'),
                    read_cefr=student_data.get('read_cefr'),
                    lexile=student_data.get('lexile'),
                    total=student_data.get('total'),
                    cefr_geral=student_data.get('cefr_geral'),
                    listening_csa_points=student_data.get('listening_csa_points'),
                    class_id=student_data.get('class_id'),
                    teacher_id=student_data.get('teacher_id'),
                    created_at=datetime.fromisoformat(student_data['created_at']) if student_data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(student_data['updated_at']) if student_data.get('updated_at') else None
                )
                student.id = student_data['id']
                db.session.add(student)
            
            # Importar níveis computados
            print("DEBUG: Importando níveis computados")
            for level_data in data.get('computed_levels', []):
                level = ComputedLevel(
                    student_id=level_data['student_id'],
                    school_level=level_data.get('school_level'),
                    listening_level=level_data.get('listening_level'),
                    lfm_level=level_data.get('lfm_level'),
                    reading_level=level_data.get('reading_level'),
                    overall_level=level_data.get('overall_level'),
                    applied_rules=level_data.get('applied_rules'),
                    created_at=datetime.fromisoformat(level_data['created_at']) if level_data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(level_data['updated_at']) if level_data.get('updated_at') else None
                )
                level.id = level_data['id']
                db.session.add(level)
            
            print("DEBUG: Fazendo commit das alterações")
            db.session.commit()
            
            print(f"Dados importados com sucesso de {import_path}")
            print(f"Estudantes: {len(data.get('students', []))}")
            print(f"Professores: {len(data.get('teachers', []))}")
            print(f"Classes: {len(data.get('classes', []))}")
            print(f"Níveis computados: {len(data.get('computed_levels', []))}")
            return True
            
    except Exception as e:
        print(f"Erro ao importar dados: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Backup e Restore do banco de dados TOEFL Dashboard')
    parser.add_argument('action', choices=['backup', 'restore', 'export', 'import'], 
                       help='Ação a ser executada')
    parser.add_argument('--file', '-f', required=True, 
                       help='Caminho do arquivo de backup/restore')
    parser.add_argument('--format', choices=['native', 'json'], default='native',
                       help='Formato do backup (native=SQLite/PostgreSQL, json=universal)')
    
    args = parser.parse_args()
    
    # Criar diretório backups se não existir
    backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)
    
    if args.action == 'backup':
        if args.format == 'json':
            success = export_data_json(args.file)
        else:
            db_type = get_database_type()
            if db_type == 'sqlite':
                success = backup_sqlite(args.file)
            elif db_type == 'postgresql':
                success = backup_postgresql(args.file)
            else:
                print(f"Tipo de banco não suportado: {db_type}")
                success = False
    
    elif args.action == 'restore':
        if args.format == 'json':
            success = import_data_json(args.file)
        else:
            db_type = get_database_type()
            if db_type == 'sqlite':
                success = restore_sqlite(args.file)
            elif db_type == 'postgresql':
                success = restore_postgresql(args.file)
            else:
                print(f"Tipo de banco não suportado: {db_type}")
                success = False
    
    elif args.action == 'export':
        success = export_data_json(args.file)
    
    elif args.action == 'import':
        success = import_data_json(args.file)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()