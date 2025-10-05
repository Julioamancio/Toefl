#!/usr/bin/env python3
"""
Script para importar dados no Render.com
Este script deve ser executado no ambiente do Render para popular o banco de dados
"""

import os
import sys
from app import create_app
from models import db
from database_backup import import_data_json

def main():
    """Função principal para importar dados no Render"""
    print("🚀 IMPORTANDO DADOS NO RENDER.COM")
    print("=" * 50)
    
    # Verificar se estamos no Render
    if not os.environ.get('DATABASE_URL'):
        print("❌ Este script deve ser executado no Render.com")
        print("   DATABASE_URL não encontrada!")
        return 1
    
    try:
        # Criar aplicação (create_app retorna tupla (app, csrf))
        app, csrf = create_app('production')
        
        with app.app_context():
            print("✅ Aplicação criada com sucesso")
            
            # Verificar se já existem dados
            from models import Student
            existing_students = Student.query.count()
            
            if existing_students > 0:
                print(f"ℹ️  Já existem {existing_students} estudantes no banco")
                print("   Continuando com a importação...")
            
            # Importar dados do backup
            backup_file = 'backups/export_20250928_085940.json'
            
            if not os.path.exists(backup_file):
                print(f"❌ Arquivo de backup não encontrado: {backup_file}")
                return 1
            
            print(f"📥 Importando dados de: {backup_file}")
            
            # Executar importação
            import_data_json(backup_file)
            
            # Verificar resultado
            final_students = Student.query.count()
            print(f"✅ Importação concluída!")
            print(f"   Total de estudantes: {final_students}")
            
            return 0
            
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())