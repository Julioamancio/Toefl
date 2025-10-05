#!/usr/bin/env python3
import os
import re
from app import create_app

# Função para mascarar senha na URL para logs seguros
def mask_database_url(url):
    if not url:
        return "URL não definida"
    # Mascarar senha na URL: postgresql+psycopg://user:password@host/db -> postgresql+psycopg://user:***@host/db
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)

# Função para validar e corrigir DATABASE_URL
def validate_and_fix_database_url():
    database_url = os.environ.get('DATABASE_URL')
    
    print("🔍 DIAGNÓSTICO DA CONEXÃO DO BANCO:")
    print(f"   DATABASE_URL original: {mask_database_url(database_url)}")
    
    if not database_url:
        print("❌ DATABASE_URL não está definida!")
        return None
    
    # Verificar se a URL precisa de correção
    if database_url.startswith('postgres://'):
        print("🔧 Convertendo postgres:// para postgresql+psycopg://")
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        print("🔧 Convertendo postgresql:// para postgresql+psycopg://")
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    # Adicionar SSL para conexões do Render (tanto internas quanto externas)
    if 'render.com' in database_url and '?sslmode=' not in database_url:
        print("🔧 Adicionando SSL para conexão do Render")
        database_url += '?sslmode=require'
    
    print(f"   DATABASE_URL corrigida: {mask_database_url(database_url)}")
    
    # Extrair componentes da URL para validação
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        print(f"   Host: {parsed.hostname}")
        print(f"   Porta: {parsed.port or 5432}")
        print(f"   Usuário: {parsed.username}")
        print(f"   Banco: {parsed.path[1:] if parsed.path else 'N/A'}")
        print(f"   SSL: {'Sim' if 'sslmode=require' in database_url else 'Não'}")
    except Exception as e:
        print(f"⚠️  Erro ao analisar URL: {e}")
    
    return database_url

print("🚀 INICIANDO APLICAÇÃO TOEFL DASHBOARD...")

# Criar a aplicação Flask - desempacotar a tupla (app, csrf)
app, csrf = create_app()

# Validar e corrigir DATABASE_URL se necessário
corrected_url = validate_and_fix_database_url()
if corrected_url and corrected_url != os.environ.get('DATABASE_URL'):
    print("🔧 Aplicando correção da DATABASE_URL...")
    os.environ['DATABASE_URL'] = corrected_url
    # Recriar a aplicação com a URL corrigida - desempacotar novamente
    app, csrf = create_app()

# Inicializar banco de dados com retry robusto
with app.app_context():
    from models import db
    from sqlalchemy import inspect, text
    import time

    max_retries = 5  # Aumentar tentativas
    retry_delay = 2  # Delay inicial menor para conexões rápidas

    print(f"🔧 Configuração do SQLAlchemy Engine:")
    print(f"   Pool size: {db.engine.pool.size()}")
    print(f"   Max overflow: {db.engine.pool._max_overflow}")
    print(f"   Pool timeout: {db.engine.pool._timeout}")

    for attempt in range(max_retries):
        try:
            print(f"🔧 Tentativa {attempt + 1}/{max_retries} - Conectando ao banco...")
            
            # Testar conexão
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"✅ Conexão estabelecida! PostgreSQL: {version[:50]}...")
            
            # Verificar/criar tabelas
            insp = inspect(db.engine)
            if not insp.has_table("classes"):
                print("🔧 Criando tabelas do banco de dados...")
                db.create_all()
                print("✅ Tabelas criadas com sucesso!")
            else:
                print("✅ Tabelas do banco já existem.")
            
            print("🎉 BANCO DE DADOS INICIALIZADO COM SUCESSO!")
            break
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erro na tentativa {attempt + 1}: {error_msg}")
            
            # Diagnósticos específicos
            if "password authentication failed" in error_msg:
                print("🔍 DIAGNÓSTICO: Falha de autenticação detectada!")
                print("   Possíveis causas:")
                print("   1. Senha incorreta na DATABASE_URL")
                print("   2. Usuário não existe ou foi alterado")
                print("   3. Banco de dados foi resetado/recriado")
                print("   4. Credenciais rotacionadas pelo Render")
            elif "connection refused" in error_msg:
                print("🔍 DIAGNÓSTICO: Conexão recusada!")
                print("   Possíveis causas:")
                print("   1. Banco ainda não está pronto")
                print("   2. Host/porta incorretos")
                print("   3. Firewall bloqueando conexão")
            elif "timeout" in error_msg.lower():
                print("🔍 DIAGNÓSTICO: Timeout de conexão!")
                print("   Possíveis causas:")
                print("   1. Banco sobrecarregado")
                print("   2. Rede lenta")
                print("   3. Pool de conexões esgotado")
            
            if attempt < max_retries - 1:
                print(f"⏳ Aguardando {retry_delay}s antes da próxima tentativa...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 20)  # Backoff com limite menor
            else:
                print("❌ FALHA CRÍTICA: Não foi possível conectar ao banco após todas as tentativas")
                print("🚨 AÇÃO NECESSÁRIA:")
                print("   1. Verificar credenciais do banco no painel do Render")
                print("   2. Confirmar se o banco PostgreSQL está ativo")
                print("   3. Verificar se a DATABASE_URL está correta")
                print("   4. Considerar recriar o banco se necessário")
                print("⚠️  Aplicação iniciará sem inicialização do banco")

print("✅ APLICAÇÃO PRONTA PARA USO!")

# Exportar aplicação para WSGI
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)