import os
import re
from urllib.parse import quote_plus, urlparse, parse_qs
from sqlalchemy.engine.url import make_url

def get_render_database_urls():
    """
    Retorna possíveis URLs de banco do Render em ordem de prioridade
    """
    base_url = os.environ.get('DATABASE_URL', '')
    
    if not base_url:
        return []
    
    urls = []
    
    # URL original
    urls.append(base_url)
    
    # Variações com diferentes drivers
    for prefix in ['postgres://', 'postgresql://']:
        if base_url.startswith(prefix):
            # Versão com psycopg
            psycopg_url = base_url.replace(prefix, 'postgresql+psycopg://', 1)
            urls.append(psycopg_url)
            
            # Versão com psycopg e SSL
            if '?sslmode=' not in psycopg_url:
                ssl_url = psycopg_url + ('&' if '?' in psycopg_url else '?') + 'sslmode=require'
                urls.append(ssl_url)
    
    # Remover duplicatas mantendo ordem
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls

def validate_database_url(url):
    """
    Valida se uma URL de banco está bem formada
    """
    try:
        parsed = urlparse(url)
        
        # Verificações básicas
        if not parsed.scheme:
            return False, "Esquema não definido"
        
        if not parsed.hostname:
            return False, "Host não definido"
        
        if not parsed.username:
            return False, "Usuário não definido"
        
        if not parsed.password:
            return False, "Senha não definida"
        
        if not parsed.path or parsed.path == '/':
            return False, "Nome do banco não definido"
        
        # Verificar se é PostgreSQL
        if not parsed.scheme.startswith('postgresql'):
            return False, f"Esquema não suportado: {parsed.scheme}"
        
        return True, "URL válida"
        
    except Exception as e:
        return False, f"Erro ao analisar URL: {e}"

class Config:
    """Configurações base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Configurações de segurança
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Configurações de arquivos estáticos
    STATIC_FOLDER = 'static'
    STATIC_URL_PATH = '/static'

class DevelopmentConfig(Config):
    """Configurações para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///toefl_dashboard.db'

class ProductionConfig(Config):
    """Configurações para produção"""
    DEBUG = False
    
    # Configuração do PostgreSQL para produção com múltiplos fallbacks
    DATABASE_URL = None
    
    # Tentar múltiplas variações da DATABASE_URL
    possible_urls = get_render_database_urls()
    
    if possible_urls:
        print("🔍 TESTANDO URLS DE BANCO DISPONÍVEIS:")
        
        for i, url in enumerate(possible_urls, 1):
            # Mascarar senha para log seguro
            masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
            print(f"   {i}. {masked_url}")
            
            # Validar URL
            is_valid, message = validate_database_url(url)
            if is_valid:
                DATABASE_URL = url
                print(f"   ✅ URL {i} selecionada: {message}")
                break
            else:
                print(f"   ❌ URL {i} inválida: {message}")
        
        if not DATABASE_URL:
            print("❌ NENHUMA URL VÁLIDA ENCONTRADA!")
            print("🔧 Usando primeira URL disponível como fallback...")
            DATABASE_URL = possible_urls[0]
    else:
        print("❌ DATABASE_URL não definida!")
        DATABASE_URL = 'postgresql+psycopg://user:password@localhost/toefl_dashboard'
    
    # Análise detalhada da URL final
    try:
        parsed = urlparse(DATABASE_URL)
        print("🔧 CONFIGURAÇÃO FINAL DO BANCO:")
        print(f"   Driver: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}:{parsed.port or 5432}")
        print(f"   Usuário: {parsed.username}")
        print(f"   Banco: {parsed.path[1:] if parsed.path else 'N/A'}")
        
        # Verificar parâmetros SSL
        if parsed.query:
            params = parse_qs(parsed.query)
            ssl_mode = params.get('sslmode', ['não definido'])[0]
            print(f"   SSL: {ssl_mode}")
        else:
            print(f"   SSL: não configurado")
            
    except Exception as e:
        print(f"⚠️  Erro ao analisar URL final: {e}")
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Configurações do SQLAlchemy otimizadas para Render com retry automático
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 2,  # Reduzido ainda mais para evitar timeout
        'max_overflow': 1,  # Mínimo overflow
        'pool_recycle': 300,
        'pool_timeout': 45,  # Timeout aumentado para dar mais tempo
        'connect_args': {
            'connect_timeout': 45,  # Timeout de conexão aumentado
            'application_name': 'toefl_dashboard',
            'options': '-c statement_timeout=45000',  # 45s timeout para queries
            'keepalives_idle': 600,  # Keep-alive para conexões longas
            'keepalives_interval': 30,
            'keepalives_count': 3
        }
    }
    
    # Configurações de sessão para produção
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')  # Allow HTTP during local/internal access
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Pasta de upload para produção (Render usa /tmp)
    UPLOAD_FOLDER = '/tmp/uploads'

class TestingConfig(Config):
    """Configurações para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
