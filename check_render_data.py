#!/usr/bin/env python3
"""
Script para verificar se os dados estão sendo carregados corretamente
Pode ser usado tanto localmente quanto no Render
"""

import os
import sys
from app import create_app
from models import db, Student, Teacher, Class, User

def check_database_connection():
    """Verifica se a conexão com o banco está funcionando"""
    try:
        app = create_app('production')  # Usar configuração de produção
        with app.app_context():
            # Tenta fazer uma query simples
            result = db.session.execute(db.text("SELECT 1")).fetchone()
            print("✅ Conexão com banco de dados: OK")
            return True
    except Exception as e:
        print(f"❌ Erro na conexão com banco: {e}")
        return False

def check_tables():
    """Verifica se as tabelas existem"""
    try:
        app = create_app('production')  # Usar configuração de produção
        with app.app_context():
            # Verificar se as tabelas principais existem
            tables = ['students', 'teachers', 'classes', 'users', 'student_certificate_layouts']
            
            for table in tables:
                try:
                    result = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    count = result[0] if result else 0
                    print(f"✅ Tabela {table}: {count} registros")
                except Exception as e:
                    print(f"❌ Tabela {table}: Erro - {e}")
            
            return True
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return False

def check_data_counts():
    """Verifica a quantidade de dados em cada tabela"""
    try:
        app = create_app('production')  # Usar configuração de produção
        with app.app_context():
            # Contar registros usando os modelos
            student_count = Student.query.count()
            teacher_count = Teacher.query.count()
            class_count = Class.query.count()
            user_count = User.query.count()
            
            print(f"\n📊 CONTAGEM DE DADOS:")
            print(f"   Estudantes: {student_count}")
            print(f"   Professores: {teacher_count}")
            print(f"   Turmas: {class_count}")
            print(f"   Usuários: {user_count}")
            
            # Verificar se há dados
            if student_count == 0:
                print("⚠️  ATENÇÃO: Nenhum estudante encontrado!")
                return False
            
            return True
    except Exception as e:
        print(f"❌ Erro ao contar dados: {e}")
        return False

def check_sample_data():
    """Verifica alguns dados de exemplo"""
    try:
        app = create_app('production')  # Usar configuração de produção
        with app.app_context():
            # Pegar alguns estudantes de exemplo
            students = Student.query.limit(3).all()
            
            print(f"\n👥 EXEMPLOS DE ESTUDANTES:")
            for student in students:
                print(f"   ID: {student.id}, Nome: {student.name}, Turma: {student.turma}")
            
            # Verificar se há admin
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print(f"✅ Usuário admin encontrado")
            else:
                print(f"❌ Usuário admin NÃO encontrado")
            
            return True
    except Exception as e:
        print(f"❌ Erro ao verificar dados de exemplo: {e}")
        return False

def main():
    """Função principal"""
    print("🔍 VERIFICANDO DADOS NO RENDER/PRODUÇÃO")
    print("=" * 50)
    
    # Verificar variáveis de ambiente
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL definida")
    else:
        print(f"❌ DATABASE_URL não definida - usando configuração local")
    
    # Executar verificações
    checks = [
        ("Conexão com banco", check_database_connection),
        ("Estrutura das tabelas", check_tables),
        ("Contagem de dados", check_data_counts),
        ("Dados de exemplo", check_sample_data)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 {name}...")
        result = check_func()
        results.append((name, result))
    
    # Resumo final
    print(f"\n📋 RESUMO:")
    print("=" * 30)
    
    all_ok = True
    for name, result in results:
        status = "✅ OK" if result else "❌ FALHOU"
        print(f"{status} {name}")
        if not result:
            all_ok = False
    
    if all_ok:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"   Os dados estão sendo carregados corretamente.")
    else:
        print(f"\n⚠️  ALGUNS TESTES FALHARAM!")
        print(f"   Pode haver problema com os dados no Render.")
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())