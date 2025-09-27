#!/usr/bin/env python3
"""
Script para corrigir dados no ambiente de produção (Render)
Corrige níveis CEFR asteriscados e recalcula níveis gerais
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fix_production_data():
    """Corrige os dados no ambiente de produção"""
    try:
        # Importar após configurar o path
        from app import create_app
        from models import db, Student
        
        print("🚀 Iniciando correção de dados no ambiente de produção...")
        
        # Criar aplicação em modo produção
        app = create_app('production')
        
        with app.app_context():
            print("🔗 Conectado ao banco de dados de produção...")
            
            # Buscar todos os estudantes com asteriscos nos níveis CEFR
            students_with_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).all()
            
            print(f"📊 Encontrados {len(students_with_asterisks)} estudantes com asteriscos nos níveis CEFR")
            
            if len(students_with_asterisks) == 0:
                print("✅ Nenhum estudante com asteriscos encontrado. Dados já estão corretos!")
                return True
            
            # Contadores para relatório
            read_fixed = 0
            lfm_fixed = 0
            listen_fixed = 0
            general_recalculated = 0
            
            # Corrigir cada estudante
            for student in students_with_asterisks:
                print(f"🔧 Corrigindo estudante: {student.name} (ID: {student.id})")
                
                # Corrigir Read_CEFR
                if student.Read_CEFR and '*' in student.Read_CEFR:
                    old_value = student.Read_CEFR
                    student.Read_CEFR = student.Read_CEFR.replace('*', '')
                    print(f"   📖 Read_CEFR: {old_value} → {student.Read_CEFR}")
                    read_fixed += 1
                
                # Corrigir LFM_CEFR
                if student.LFM_CEFR and '*' in student.LFM_CEFR:
                    old_value = student.LFM_CEFR
                    student.LFM_CEFR = student.LFM_CEFR.replace('*', '')
                    print(f"   📝 LFM_CEFR: {old_value} → {student.LFM_CEFR}")
                    lfm_fixed += 1
                
                # Corrigir Listen_CEFR
                if student.Listen_CEFR and '*' in student.Listen_CEFR:
                    old_value = student.Listen_CEFR
                    student.Listen_CEFR = student.Listen_CEFR.replace('*', '')
                    print(f"   🎧 Listen_CEFR: {old_value} → {student.Listen_CEFR}")
                    listen_fixed += 1
                
                # Recalcular nível geral
                old_general = student.General_CEFR
                
                # Coletar níveis válidos (não vazios e não None)
                levels = []
                if student.Listen_CEFR and student.Listen_CEFR.strip():
                    levels.append(student.Listen_CEFR.strip())
                if student.Read_CEFR and student.Read_CEFR.strip():
                    levels.append(student.Read_CEFR.strip())
                if student.LFM_CEFR and student.LFM_CEFR.strip():
                    levels.append(student.LFM_CEFR.strip())
                
                if levels:
                    # Definir ordem dos níveis CEFR
                    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
                    
                    # Filtrar apenas níveis válidos
                    valid_levels = [level for level in levels if level in level_order]
                    
                    if valid_levels:
                        # Encontrar o nível mais baixo (mais conservador)
                        min_level_index = min(level_order.index(level) for level in valid_levels)
                        student.General_CEFR = level_order[min_level_index]
                        
                        if old_general != student.General_CEFR:
                            print(f"   🎯 General_CEFR: {old_general} → {student.General_CEFR}")
                            general_recalculated += 1
                    else:
                        print(f"   ⚠️  Nenhum nível CEFR válido encontrado para {student.name}")
                else:
                    print(f"   ⚠️  Nenhum nível CEFR disponível para {student.name}")
            
            # Salvar todas as alterações
            print("💾 Salvando alterações no banco de dados...")
            db.session.commit()
            
            # Relatório final
            print("\n" + "="*60)
            print("📋 RELATÓRIO DE CORREÇÕES APLICADAS")
            print("="*60)
            print(f"📖 Read_CEFR corrigidos: {read_fixed}")
            print(f"📝 LFM_CEFR corrigidos: {lfm_fixed}")
            print(f"🎧 Listen_CEFR corrigidos: {listen_fixed}")
            print(f"🎯 General_CEFR recalculados: {general_recalculated}")
            print(f"👥 Total de estudantes processados: {len(students_with_asterisks)}")
            print("="*60)
            
            # Verificação final
            remaining_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            print(f"🔍 Asteriscos restantes após correção: {remaining_asterisks}")
            
            if remaining_asterisks == 0:
                print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO! Todos os asteriscos foram removidos.")
            else:
                print("⚠️  Ainda existem asteriscos no banco. Verifique os dados.")
            
            print(f"🕒 Correção finalizada em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return remaining_asterisks == 0
            
    except Exception as e:
        print(f"❌ Erro durante correção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🔧 SCRIPT DE CORREÇÃO DE DADOS - AMBIENTE DE PRODUÇÃO")
    print("="*60)
    
    success = fix_production_data()
    
    if success:
        print("\n✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("Os dados no ambiente de produção foram corrigidos.")
    else:
        print("\n❌ FALHA NA CORREÇÃO DOS DADOS!")
        print("Verifique os logs de erro acima.")
        sys.exit(1)