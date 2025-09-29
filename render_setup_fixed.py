#!/usr/bin/env python3
"""
Script para setup completo do Render.com com correção de chaves estrangeiras
Resolve o problema de teacher_id nulo/inválido nos students
"""

import os
import sys
import json
from datetime import datetime

# Adicionar o diretório atual ao path para importar módulos locais
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_database_config():
    """Mostra a configuração do banco que será usada"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print("✅ DATABASE_URL encontrada!")
        # Extrair informações da URL (sem mostrar senha)
        if 'postgresql' in database_url:
            parts = database_url.split('@')
            if len(parts) > 1:
                host_part = parts[1].split('/')[0]
                db_part = parts[1].split('/')[-1] if '/' in parts[1] else 'unknown'
                user_part = parts[0].split('://')[-1].split(':')[0] if '://' in parts[0] else 'unknown'
                
                print("🔧 CONFIGURAÇÃO DO BANCO:")
                print(f"   Driver: postgresql+psycopg")
                print(f"   Host: {host_part}")
                print(f"   Usuário: {user_part}")
                print(f"   Banco: {db_part}")
                print(f"   SSL: configurado")
    else:
        print("❌ DATABASE_URL não definida!")
        print("🔧 CONFIGURAÇÃO FINAL DO BANCO:")
        print(f"   Driver: postgresql+psycopg")
        print(f"   Host: localhost:5432")
        print(f"   Usuário: user")
        print(f"   Banco: toefl_dashboard")
        print(f"   SSL: não configurado")

def main():
    """Função principal do setup"""
    print("🚀 SETUP COMPLETO DO RENDER.COM (VERSÃO CORRIGIDA)")
    print("=" * 60)
    
    # Mostrar configuração do banco
    print_database_config()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("⚠️  DATABASE_URL não definida - usando configuração padrão")
    
    try:
        # Importar após configurar o path
        from app import create_app
        from models import db, Student, Teacher, Class, User, StudentCertificateLayout
        from services.importer import import_data_json
        
        # Criar aplicação (create_app retorna tupla (app, csrf))
        app, csrf = create_app('production')
        
        with app.app_context():
            print("✅ Aplicação Flask criada")
            
            # 1. Criar tabelas
            print("\n🔄 Criar tabelas...")
            try:
                print("📋 Criando tabelas...")
                db.create_all()
                print("✅ Tabelas criadas/verificadas com sucesso")
            except Exception as e:
                print(f"❌ Erro ao criar tabelas: {e}")
                print("❌ Falha em: Criar tabelas")
                return False
            
            # 2. Verificar usuário admin
            print("\n👤 Verificar usuário admin...")
            try:
                admin_username = os.getenv("ADMIN_USERNAME", "admin")
                existing_admin = User.query.filter_by(username=admin_username).first()
                
                if existing_admin:
                    print(f"✅ Usuário admin '{admin_username}' já existe")
                else:
                    print(f"📝 Criando usuário admin '{admin_username}'...")
                    admin_user = User(
                        username=admin_username,
                        email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
                        is_admin=True,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    admin_user.set_password(os.getenv("ADMIN_PASSWORD", "admin123"))
                    db.session.add(admin_user)
                    db.session.commit()
                    print("✅ Usuário admin criado com sucesso")
            except Exception as e:
                print(f"❌ Erro ao verificar/criar admin: {e}")
                print("❌ Falha em: Verificar usuário admin")
                return False
            
            # 3. Verificar se já existem dados
            print("\n📊 Verificar dados existentes...")
            try:
                student_count = Student.query.count()
                teacher_count = Teacher.query.count()
                class_count = Class.query.count()
                
                print(f"📈 Dados atuais:")
                print(f"   - Estudantes: {student_count}")
                print(f"   - Professores: {teacher_count}")
                print(f"   - Turmas: {class_count}")
                
                if student_count > 0:
                    print("⚠️  Dados já existem. Pulando importação.")
                    print("✅ Setup concluído - dados já presentes")
                    return True
                    
            except Exception as e:
                print(f"❌ Erro ao verificar dados: {e}")
                # Continuar mesmo com erro na verificação
            
            # 4. Importar dados com correção de chaves estrangeiras
            print("\n📥 Importar dados do backup...")
            try:
                backup_file = "backups/export_20250928_085940.json"
                
                if not os.path.exists(backup_file):
                    print(f"❌ Arquivo de backup não encontrado: {backup_file}")
                    print("❌ Falha em: Importar dados")
                    return False
                
                print(f"📂 Carregando backup: {backup_file}")
                
                # Carregar e corrigir dados do backup
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                # CORREÇÃO: Importar teachers primeiro
                print("👨‍🏫 Importando professores primeiro...")
                if 'teachers' in backup_data:
                    for teacher_data in backup_data['teachers']:
                        existing_teacher = Teacher.query.filter_by(id=teacher_data['id']).first()
                        if not existing_teacher:
                            teacher = Teacher(
                                id=teacher_data['id'],
                                name=teacher_data['name'],
                                created_at=datetime.fromisoformat(teacher_data['created_at'].replace('Z', '+00:00'))
                            )
                            db.session.add(teacher)
                    
                    db.session.commit()
                    print(f"✅ {len(backup_data['teachers'])} professores importados")
                
                # CORREÇÃO: Corrigir teacher_id nulos nos students
                print("🔧 Corrigindo teacher_id nulos nos estudantes...")
                if 'students' in backup_data:
                    # Pegar o primeiro professor disponível como padrão
                    default_teacher = Teacher.query.first()
                    if default_teacher:
                        default_teacher_id = default_teacher.id
                        print(f"📌 Usando professor padrão: {default_teacher.name} (ID: {default_teacher_id})")
                        
                        # Corrigir students com teacher_id nulo
                        corrected_count = 0
                        for student_data in backup_data['students']:
                            if student_data.get('teacher_id') is None or student_data.get('teacher_id') == 0:
                                student_data['teacher_id'] = default_teacher_id
                                corrected_count += 1
                        
                        print(f"🔧 {corrected_count} estudantes corrigidos com teacher_id padrão")
                    else:
                        print("❌ Nenhum professor encontrado para usar como padrão")
                        return False
                
                # Agora importar usando o método padrão com dados corrigidos
                print("📥 Importando dados corrigidos...")
                
                # Salvar dados corrigidos temporariamente
                corrected_backup_file = "backups/temp_corrected_backup.json"
                with open(corrected_backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                # Importar dados corrigidos
                success = import_data_json(corrected_backup_file)
                
                # Limpar arquivo temporário
                if os.path.exists(corrected_backup_file):
                    os.remove(corrected_backup_file)
                
                if success:
                    print("✅ Dados importados com sucesso")
                else:
                    print("❌ Falha na importação dos dados")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao importar dados: {e}")
                print("❌ Falha em: Importar dados")
                return False
            
            # 5. Verificar importação
            print("\n🔍 Verificar importação...")
            try:
                final_student_count = Student.query.count()
                final_teacher_count = Teacher.query.count()
                final_class_count = Class.query.count()
                
                print(f"📊 ESTATÍSTICAS FINAIS:")
                print(f"   ✅ Estudantes: {final_student_count}")
                print(f"   ✅ Professores: {final_teacher_count}")
                print(f"   ✅ Turmas: {final_class_count}")
                
                if final_student_count > 0 and final_teacher_count > 0:
                    print("\n🎉 SETUP CONCLUÍDO COM SUCESSO!")
                    print("🌐 Sua aplicação no Render agora tem todos os dados!")
                    return True
                else:
                    print("❌ Importação incompleta - dados insuficientes")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao verificar importação: {e}")
                return False
    
    except Exception as e:
        print(f"❌ Erro geral no setup: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Script executado com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Script falhou!")
        sys.exit(1)