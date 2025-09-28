#!/usr/bin/env python3
import os
from app import create_app

# Criar a aplicação usando a factory function
app = create_app()

# Inicializar banco de dados para produção com tratamento robusto
with app.app_context():
    from models import db
    from sqlalchemy import inspect, text
    import time
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔧 Tentativa {attempt + 1}/{max_retries} - Conectando ao banco...")
            
            # Testar conexão primeiro
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Conexão com banco estabelecida!")
            
            # Verificar se as tabelas existem
            insp = inspect(db.engine)
            if not insp.has_table("classes"):
                print("🔧 Criando tabelas do banco de dados...")
                db.create_all()
                print("✅ Tabelas criadas com sucesso!")
            else:
                print("✅ Tabelas do banco já existem.")
            break
            
        except Exception as e:
            print(f"❌ Erro na tentativa {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Aguardando {retry_delay}s antes da próxima tentativa...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Backoff exponencial
            else:
                print("❌ Falha ao conectar ao banco após todas as tentativas")
                print("⚠️  Aplicação iniciará sem inicialização do banco")

# Gunicorn padrão procura por "application"
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)