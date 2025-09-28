#!/usr/bin/env python3
"""
Script para corrigir todos os alunos com nível A1 para A2
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Definir DATABASE_URL para SQLite local
os.environ['DATABASE_URL'] = 'sqlite:///toefl_dashboard.db'

# Configuração do banco de dados
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///toefl_dashboard.db')

def fix_a1_to_a2():
    """
    Corrige todos os alunos com níveis A1 para A2 em todos os campos CEFR
    """
    try:
        # Criar engine e sessão
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("🔍 Verificando alunos com nível A1...")
        
        # Buscar alunos com A1 em qualquer campo CEFR
        query = text("""
            SELECT id, name, list_cefr, lfm_cefr, read_cefr, cefr_geral 
            FROM students 
            WHERE list_cefr = 'A1' OR lfm_cefr = 'A1' OR read_cefr = 'A1' OR cefr_geral = 'A1'
        """)
        
        result = session.execute(query)
        students_with_a1 = result.fetchall()
        
        if not students_with_a1:
            print("✅ Nenhum aluno com nível A1 encontrado!")
            return True
        
        print(f"📋 Encontrados {len(students_with_a1)} alunos com nível A1:")
        for student in students_with_a1:
            print(f"   - {student.name} (ID: {student.id})")
            print(f"     Listening: {student.list_cefr}, LFM: {student.lfm_cefr}, Reading: {student.read_cefr}, Geral: {student.cefr_geral}")
        
        print("\n🔄 Corrigindo níveis A1 para A2...")
        
        # Atualizar todos os campos A1 para A2
        update_queries = [
            "UPDATE students SET list_cefr = 'A2' WHERE list_cefr = 'A1'",
            "UPDATE students SET lfm_cefr = 'A2' WHERE lfm_cefr = 'A1'", 
            "UPDATE students SET read_cefr = 'A2' WHERE read_cefr = 'A1'",
            "UPDATE students SET cefr_geral = 'A2' WHERE cefr_geral = 'A1'"
        ]
        
        total_updated = 0
        for update_query in update_queries:
            result = session.execute(text(update_query))
            updated_count = result.rowcount
            total_updated += updated_count
            if updated_count > 0:
                print(f"   ✅ {updated_count} registros atualizados")
        
        # Commit das mudanças
        session.commit()
        
        print(f"\n🎉 Correção concluída com sucesso!")
        print(f"   Total de campos atualizados: {total_updated}")
        
        # Verificar se ainda existem A1
        verification_query = text("""
            SELECT COUNT(*) as count 
            FROM students 
            WHERE list_cefr = 'A1' OR lfm_cefr = 'A1' OR read_cefr = 'A1' OR cefr_geral = 'A1'
        """)
        
        result = session.execute(verification_query)
        remaining_a1 = result.fetchone().count
        
        if remaining_a1 == 0:
            print("✅ Verificação: Nenhum nível A1 restante no banco!")
        else:
            print(f"⚠️  Ainda existem {remaining_a1} registros com A1")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir níveis: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando correção de níveis A1 para A2...")
    success = fix_a1_to_a2()
    
    if success:
        print("\n🎉 Correção concluída com sucesso!")
    else:
        print("\n💥 Falha na correção. Verifique os logs acima.")
        sys.exit(1)