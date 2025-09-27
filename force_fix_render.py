#!/usr/bin/env python3
"""
Script FORÇADO para corrigir dados no Render
Executa múltiplas tentativas e força a correção dos asteriscos
"""

import os
import sys
import time
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def force_fix_render():
    """Força a correção dos dados no Render com múltiplas tentativas"""
    try:
        print("🚀 SCRIPT FORÇADO - Corrigindo dados no Render...")
        print("="*60)
        
        # Forçar ambiente de produção
        os.environ['FLASK_ENV'] = 'production'
        
        # Importar após configurar o ambiente
        from app import create_app
        from models import db, Student
        
        # Criar aplicação forçando produção
        app = create_app('production')
        
        with app.app_context():
            print("🔗 Conectado ao banco PostgreSQL do Render...")
            
            # Primeira verificação - contar asteriscos
            total_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            print(f"📊 ASTERISCOS ENCONTRADOS: {total_asterisks}")
            
            if total_asterisks == 0:
                print("✅ Nenhum asterisco encontrado! Dados já estão corretos.")
                return True
            
            # Buscar TODOS os estudantes (não apenas os com asteriscos)
            all_students = Student.query.all()
            print(f"👥 Total de estudantes no banco: {len(all_students)}")
            
            # Contadores
            corrections_made = 0
            students_processed = 0
            
            # Processar TODOS os estudantes
            for student in all_students:
                students_processed += 1
                student_changed = False
                
                print(f"\n🔧 Processando [{students_processed}/{len(all_students)}]: {student.name} (ID: {student.id})")
                
                # Verificar e corrigir Read_CEFR
                if student.Read_CEFR and '*' in str(student.Read_CEFR):
                    old_value = student.Read_CEFR
                    student.Read_CEFR = str(student.Read_CEFR).replace('*', '')
                    print(f"   📖 Read_CEFR: '{old_value}' → '{student.Read_CEFR}'")
                    student_changed = True
                
                # Verificar e corrigir LFM_CEFR
                if student.LFM_CEFR and '*' in str(student.LFM_CEFR):
                    old_value = student.LFM_CEFR
                    student.LFM_CEFR = str(student.LFM_CEFR).replace('*', '')
                    print(f"   📝 LFM_CEFR: '{old_value}' → '{student.LFM_CEFR}'")
                    student_changed = True
                
                # Verificar e corrigir Listen_CEFR
                if student.Listen_CEFR and '*' in str(student.Listen_CEFR):
                    old_value = student.Listen_CEFR
                    student.Listen_CEFR = str(student.Listen_CEFR).replace('*', '')
                    print(f"   🎧 Listen_CEFR: '{old_value}' → '{student.Listen_CEFR}'")
                    student_changed = True
                
                # Se houve mudanças, recalcular General_CEFR
                if student_changed:
                    corrections_made += 1
                    
                    # Recalcular nível geral
                    old_general = student.General_CEFR
                    
                    # Coletar níveis válidos
                    levels = []
                    if student.Listen_CEFR and str(student.Listen_CEFR).strip():
                        levels.append(str(student.Listen_CEFR).strip())
                    if student.Read_CEFR and str(student.Read_CEFR).strip():
                        levels.append(str(student.Read_CEFR).strip())
                    if student.LFM_CEFR and str(student.LFM_CEFR).strip():
                        levels.append(str(student.LFM_CEFR).strip())
                    
                    if levels:
                        level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
                        valid_levels = [level for level in levels if level in level_order]
                        
                        if valid_levels:
                            min_level_index = min(level_order.index(level) for level in valid_levels)
                            student.General_CEFR = level_order[min_level_index]
                            
                            if old_general != student.General_CEFR:
                                print(f"   🎯 General_CEFR: '{old_general}' → '{student.General_CEFR}'")
                    
                    # Salvar imediatamente após cada correção
                    try:
                        db.session.commit()
                        print(f"   ✅ Estudante {student.name} salvo com sucesso!")
                    except Exception as save_error:
                        print(f"   ❌ Erro ao salvar {student.name}: {save_error}")
                        db.session.rollback()
                
                # Pequena pausa para evitar sobrecarga
                if students_processed % 10 == 0:
                    time.sleep(0.1)
            
            # Verificação final
            print("\n" + "="*60)
            print("🔍 VERIFICAÇÃO FINAL...")
            
            final_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            print(f"📊 Asteriscos antes: {total_asterisks}")
            print(f"📊 Asteriscos depois: {final_asterisks}")
            print(f"👥 Estudantes processados: {students_processed}")
            print(f"🔧 Correções aplicadas: {corrections_made}")
            
            if final_asterisks == 0:
                print("✅ SUCESSO! Todos os asteriscos foram removidos!")
                return True
            else:
                print(f"⚠️  Ainda restam {final_asterisks} asteriscos. Tentando novamente...")
                
                # Segunda tentativa - mais agressiva
                remaining_students = Student.query.filter(
                    (Student.Read_CEFR.like('%*%')) |
                    (Student.LFM_CEFR.like('%*%')) |
                    (Student.Listen_CEFR.like('%*%'))
                ).all()
                
                print(f"🔄 Segunda tentativa com {len(remaining_students)} estudantes...")
                
                for student in remaining_students:
                    # Força a remoção de asteriscos usando SQL direto
                    try:
                        if student.Read_CEFR and '*' in str(student.Read_CEFR):
                            student.Read_CEFR = str(student.Read_CEFR).replace('*', '')
                        if student.LFM_CEFR and '*' in str(student.LFM_CEFR):
                            student.LFM_CEFR = str(student.LFM_CEFR).replace('*', '')
                        if student.Listen_CEFR and '*' in str(student.Listen_CEFR):
                            student.Listen_CEFR = str(student.Listen_CEFR).replace('*', '')
                        
                        db.session.commit()
                        print(f"   ✅ Forçada correção de {student.name}")
                    except Exception as e:
                        print(f"   ❌ Erro na segunda tentativa para {student.name}: {e}")
                        db.session.rollback()
                
                # Verificação final da segunda tentativa
                final_final_asterisks = Student.query.filter(
                    (Student.Read_CEFR.like('%*%')) |
                    (Student.LFM_CEFR.like('%*%')) |
                    (Student.Listen_CEFR.like('%*%'))
                ).count()
                
                print(f"📊 Asteriscos após segunda tentativa: {final_final_asterisks}")
                return final_final_asterisks == 0
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🔥 SCRIPT FORÇADO DE CORREÇÃO - RENDER")
    print("="*60)
    print(f"🕒 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = force_fix_render()
    
    print("\n" + "="*60)
    if success:
        print("✅ CORREÇÃO FORÇADA CONCLUÍDA COM SUCESSO!")
        print("Todos os asteriscos foram removidos do banco de produção.")
    else:
        print("❌ FALHA NA CORREÇÃO FORÇADA!")
        print("Alguns asteriscos ainda podem estar presentes.")
    
    print(f"🕒 Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)