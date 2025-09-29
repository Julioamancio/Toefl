#!/usr/bin/env python3
"""
Módulo para backup e restauração do banco de dados
"""

import json
import argparse
import os
from datetime import datetime
from app import create_app, promote_a1_levels_to_a2
from models import db, Student, Teacher, Class, User, ComputedLevel


def normalize_cefr_value(value):
    """Promove niveis A1 para A2 ao importar backups."""
    if value == 'A1':
        return 'A2'
    return value

def export_data_json(filename=None):
    """
    Exporta todos os dados do banco para um arquivo JSON
    """
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backups/export_{timestamp}.json'
    
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    with app.app_context():
        data = {
            'export_date': datetime.now().isoformat(),
            'students': [],
            'teachers': [],
            'classes': [],
            'users': [],
            'computed_levels': []
        }
        
        # Exportar estudantes
        students = Student.query.all()
        for student in students:
            student_data = {
                'id': student.id,
                'name': student.name,
                'student_number': student.student_number,
                'class_id': student.class_id,
                'teacher_id': student.teacher_id,
                'listening': student.listening,
                'lfm': student.lfm,
                'reading': student.reading,
                'total': student.total,
                'lexile': student.lexile,
                'list_cefr': student.list_cefr,
                'lfm_cefr': student.lfm_cefr,
                'read_cefr': student.read_cefr,
                'cefr_geral': student.cefr_geral,
                'listening_csa_points': student.listening_csa_points,
                'turma_meta': student.turma_meta,
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'updated_at': student.updated_at.isoformat() if student.updated_at else None
            }
            data['students'].append(student_data)
        
        # Exportar professores
        teachers = Teacher.query.all()
        for teacher in teachers:
            teacher_data = {
                'id': teacher.id,
                'name': teacher.name,
                'created_at': teacher.created_at.isoformat() if teacher.created_at else None
            }
            data['teachers'].append(teacher_data)
        
        # Exportar turmas
        classes = Class.query.all()
        for class_info in classes:
            class_data = {
                'id': class_info.id,
                'name': class_info.name,
                'description': class_info.description,
                'meta_label': class_info.meta_label,
                'is_active': class_info.is_active,
                'created_at': class_info.created_at.isoformat() if class_info.created_at else None
            }
            data['classes'].append(class_data)
        
        # Exportar usuários (sem senhas por segurança)
        users = User.query.all()
        for user in users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
            data['users'].append(user_data)
        
        # Exportar níveis computados
        computed_levels = ComputedLevel.query.all()
        for level in computed_levels:
            level_data = {
                'id': level.id,
                'student_id': level.student_id,
                'reading_level': level.reading_level,
                'listening_level': level.listening_level,
                'lfm_level': level.lfm_level,
                'overall_level': level.overall_level,
                'created_at': level.created_at.isoformat() if level.created_at else None,
                'updated_at': level.updated_at.isoformat() if level.updated_at else None
            }
            data['computed_levels'].append(level_data)
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Salvar arquivo
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dados exportados para: {filename}")
        print(f"   - {len(data['students'])} estudantes")
        print(f"   - {len(data['teachers'])} professores")
        print(f"   - {len(data['classes'])} turmas")
        print(f"   - {len(data['users'])} usuários")
        print(f"   - {len(data['computed_levels'])} níveis computados")
        
        return filename

def import_data_json(filename):
    """
    Importa dados de um arquivo JSON para o banco
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Arquivo não encontrado: {filename}")
    
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    with app.app_context():
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        try:
            # Limpar dados existentes (cuidado!)
            print("🗑️  Limpando dados existentes...")
            ComputedLevel.query.delete()
            Student.query.delete()
            Teacher.query.delete()
            Class.query.delete()
            # Não limpar usuários por segurança
            
            # Importar professores
            print("👨‍🏫 Importando professores...")
            for teacher_data in data.get('teachers', []):
                # Converter string de data de volta para datetime se necessário
                created_at = None
                if teacher_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(teacher_data['created_at'])
                    except:
                        created_at = None
                
                teacher = Teacher(
                    id=teacher_data['id'],
                    name=teacher_data['name'],
                    created_at=created_at
                )
                db.session.add(teacher)
            
            # Importar turmas
            print("🏫 Importando turmas...")
            for class_data in data.get('classes', []):
                # Converter string de data de volta para datetime se necessário
                created_at = None
                if class_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(class_data['created_at'])
                    except:
                        created_at = None
                
                class_info = Class(
                    id=class_data['id'],
                    name=class_data['name'],
                    description=class_data.get('description'),
                    meta_label=class_data.get('meta_label'),
                    is_active=class_data.get('is_active', True),
                    created_at=created_at
                )
                db.session.add(class_info)
            
            # Importar estudantes
            print("👨‍🎓 Importando estudantes...")
            for student_data in data.get('students', []):
                # Converter strings de data de volta para datetime se necessário
                created_at = None
                updated_at = None
                if student_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(student_data['created_at'])
                    except:
                        created_at = None
                if student_data.get('updated_at'):
                    try:
                        updated_at = datetime.fromisoformat(student_data['updated_at'])
                    except:
                        updated_at = None
                
                student = Student(
                    id=student_data['id'],
                    name=student_data['name'],
                    student_number=student_data['student_number'],
                    class_id=student_data.get('class_id'),
                    teacher_id=student_data.get('teacher_id'),
                    listening=student_data.get('listening'),
                    lfm=student_data.get('lfm'),
                    reading=student_data.get('reading'),
                    total=student_data.get('total'),
                    lexile=student_data.get('lexile'),
                    list_cefr=normalize_cefr_value(student_data.get('list_cefr')),
                    lfm_cefr=normalize_cefr_value(student_data.get('lfm_cefr')),
                    read_cefr=normalize_cefr_value(student_data.get('read_cefr')),
                    cefr_geral=normalize_cefr_value(student_data.get('cefr_geral')),
                    listening_csa_points=student_data.get('listening_csa_points'),
                    turma_meta=student_data.get('turma_meta'),
                    created_at=created_at,
                    updated_at=updated_at
                )
                db.session.add(student)
            
            # Importar níveis computados
            print("📊 Importando níveis computados...")
            for level_data in data.get('computed_levels', []):
                level = ComputedLevel(
                    id=level_data['id'],
                    student_id=level_data['student_id'],
                    reading_level=normalize_cefr_value(level_data.get('reading_level')),
                    listening_level=normalize_cefr_value(level_data.get('listening_level')),
                    lfm_level=normalize_cefr_value(level_data.get('lfm_level')),
                    overall_level=normalize_cefr_value(level_data.get('overall_level'))
                )
                if level_data.get('created_at'):
                    level.created_at = datetime.fromisoformat(level_data['created_at'])
                if level_data.get('updated_at'):
                    level.updated_at = datetime.fromisoformat(level_data['updated_at'])
                db.session.add(level)
            
            db.session.commit()

            promoted_total = 0
            try:
                promoted_total = promote_a1_levels_to_a2()
                if promoted_total:
                    print(f"   - Ajustados {promoted_total} campos CEFR de A1 para A2")
            except Exception as promote_error:
                print(f"Aviso: falha ao ajustar niveis A1 -> A2 durante import: {promote_error}")

            
            print("✅ Importação concluída com sucesso!")
            print(f"   - {len(data.get('students', []))} estudantes")
            print(f"   - {len(data.get('teachers', []))} professores")
            print(f"   - {len(data.get('classes', []))} turmas")
            print(f"   - {len(data.get('computed_levels', []))} níveis computados")
            
            details = {
                'students': len(data.get('students', [])),
                'teachers': len(data.get('teachers', [])),
                'classes': len(data.get('classes', [])),
                'computed_levels': len(data.get('computed_levels', [])),
            }

            if promoted_total:
                details['cefr_a1_promoted_to_a2'] = promoted_total

            return {
                'success': True,
                'message': 'Importacao concluida com sucesso',
                'details': details
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro durante a importação: {e}")
            return {
                'success': False,
                'message': f'Erro durante a importação: {e}'
            }

def main():
    """Função principal para linha de comando"""
    parser = argparse.ArgumentParser(description='Backup e restauração do banco de dados')
    parser.add_argument('action', choices=['export', 'import'], help='Ação a ser executada')
    parser.add_argument('--file', required=True, help='Arquivo de backup')
    
    args = parser.parse_args()
    
    if args.action == 'export':
        export_data_json(args.file)
    elif args.action == 'import':
        import_data_json(args.file)

if __name__ == '__main__':
    main()
