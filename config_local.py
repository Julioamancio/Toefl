import os
from urllib.parse import urlparse

def normalize_db_url(url: str) -> str:
    """
    Normaliza a URL do banco de dados para compatibilidade com SQLAlchemy e psycopg.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # psycopg3 (psycopg):
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    # força SSL em produção
    if os.getenv("RENDER") and "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    
    return url

def build_sqlalchemy_uri() -> str:
    """
    Constrói a URI do SQLAlchemy de forma robusta com múltiplas estratégias de fallback.
    """
    # DEBUG: Log temporário para verificar a DATABASE_URL no Render
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_EXTERNAL_HOSTNAME"):
        url = os.getenv("DATABASE_URL")
        print(f"DEBUG - DATABASE_URL recebida: {url}")
        print(f"DEBUG - Variáveis de ambiente disponíveis:")
        for key in sorted(os.environ.keys()):
            if any(term in key.upper() for term in ['DATABASE', 'DB_', 'POSTGRES', 'RENDER']):
                value = os.environ[key]
                # Mascarar senhas para segurança
                if 'PASSWORD' in key.upper() or 'SECRET' in key.upper():
                    value = '***MASKED***'
                print(f"DEBUG - {key}: {value}")
    
    # 1) principal: DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        return normalize_db_url(url)
    
    # 2) alternativa: montar com variáveis soltas (se você quiser suportar)
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")
    name = os.getenv("DB_NAME")
    port = os.getenv("DB_PORT", "5432")
    if host and user and pwd and name:
        return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{name}?sslmode=require"
    
    # 3) sem URL em produção: falha clara
    if os.getenv("RENDER"):
        raise ValueError("DATABASE_URL é obrigatória no ambiente Render. Verifique o painel ou o render.yaml.")
    
    # 4) fallback local (DEV)
    return "sqlite:///./dev.db"

def get_database_url():
    """
    Obtém a URL do banco de dados baseada no ambiente.
    Função mantida para compatibilidade com código existente.
    """
    return build_sqlalchemy_uri()