#!/usr/bin/env python3
import os
from app import create_app

# Criar a aplicação usando a factory function
app = create_app()

# Inicializar banco de dados para produção
with app.app_context():
    from models import db
    from sqlalchemy import inspect
    
    try:
        # Verificar se as tabelas existem
        insp = inspect(db.engine)
        if not insp.has_table("classes"):
            print("Criando tabelas do banco de dados...")
            db.create_all()
            print("Tabelas criadas com sucesso!")
        else:
            print("Tabelas do banco já existem.")
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")

# Gunicorn padrão procura por "application"
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)