#!/usr/bin/env python3
"""
Script para ser executado automaticamente no deploy do Render
Integra com o processo de inicialização para corrigir asteriscos
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def auto_fix_on_deploy():
    """Executa correção automática durante o deploy"""
    try:
        print("🔧 AUTO-FIX: Verificando e corrigindo asteriscos durante deploy...")
        
        # Forçar ambiente de produção
        os.environ['FLASK_ENV'] = 'production'
        
        from app import create_app
        from models import db, Student
        
        app = create_app('production')
        
        with app.app_context():
            # Verificar se existem asteriscos
            asterisk_count = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            if asterisk_count == 0:
                print("✅ AUTO-FIX: Nenhum asterisco encontrado. Dados OK!")
                return True
            
            print(f"🔍 AUTO-FIX: Encontrados {asterisk_count} registros com asteriscos")
            print("🔧 AUTO-FIX: Aplicando correções...")
            
            # Buscar e corrigir estudantes com asteriscos
            students_with_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).all()
            
            corrections = 0
            for student in students_with_asterisks:
                changed = False
                
                if student.Read_CEFR and '*' in str(student.Read_CEFR):
                    student.Read_CEFR = str(student.Read_CEFR).replace('*', '')
                    changed = True
                
                if student.LFM_CEFR and '*' in str(student.LFM_CEFR):
                    student.LFM_CEFR = str(student.LFM_CEFR).replace('*', '')
                    changed = True
                
                if student.Listen_CEFR and '*' in str(student.Listen_CEFR):
                    student.Listen_CEFR = str(student.Listen_CEFR).replace('*', '')
                    changed = True
                
                if changed:
                    # Recalcular General_CEFR
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
                    
                    corrections += 1
            
            # Salvar todas as correções
            db.session.commit()
            
            # Verificação final
            final_asterisks = Student.query.filter(
                (Student.Read_CEFR.like('%*%')) |
                (Student.LFM_CEFR.like('%*%')) |
                (Student.Listen_CEFR.like('%*%'))
            ).count()
            
            print(f"✅ AUTO-FIX: {corrections} estudantes corrigidos")
            print(f"📊 AUTO-FIX: Asteriscos restantes: {final_asterisks}")
            
            return final_asterisks == 0
            
    except Exception as e:
        print(f"❌ AUTO-FIX ERROR: {e}")
        return False

if __name__ == '__main__':
    print("🚀 RENDER AUTO-FIX DEPLOY")
    print("="*40)
    
    success = auto_fix_on_deploy()
    
    if success:
        print("✅ AUTO-FIX: Correções aplicadas com sucesso!")
    else:
        print("⚠️  AUTO-FIX: Algumas correções podem não ter sido aplicadas")
    
    print("="*40)