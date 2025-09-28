import os
from urllib.parse import quote_plus
from sqlalchemy.engine.url import make_url

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
    
    # Configuração do PostgreSQL para produção com SSL e fallbacks automáticos
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        DATABASE_URL = 'postgresql+psycopg://user:password@localhost/toefl_dashboard'
    else:
        # Tratamento robusto da URL com múltiplos fallbacks
        original_url = DATABASE_URL
        
        # 1. Corrige prefixo heroku-like e força driver psycopg v3
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
            print(f"🔧 URL convertida: postgres:// → postgresql+psycopg://")
        elif DATABASE_URL.startswith('postgresql://'):
            DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
            print(f"🔧 URL convertida: postgresql:// → postgresql+psycopg://")
        
        # 2. Adiciona SSL se for PostgreSQL e não tiver sslmode
        try:
            url = make_url(DATABASE_URL)
            if url.drivername.startswith('postgresql'):
                query = dict(url.query)
                
                # Força SSL para conexões externas (render.com)
                if 'render.com' in str(url.host) or 'external' in str(url.host):
                    if 'sslmode' not in query:
                        query['sslmode'] = 'require'
                        print(f"🔧 SSL adicionado para conexão externa")
                
                # Reconstrói URL com parâmetros SSL
                url = url.set(query=query)
                DATABASE_URL = str(url)
                
        except Exception as e:
            print(f"⚠️  Erro ao processar URL do banco: {e}")
            print(f"⚠️  Usando URL original: {original_url[:50]}...")
            DATABASE_URL = original_url
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Configurações do SQLAlchemy otimizadas para Render com retry automático
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 3,  # Reduzido para Render free tier
        'max_overflow': 2,  # Reduzido para evitar timeout
        'pool_recycle': 300,
        'pool_timeout': 30,  # Timeout aumentado
        'connect_args': {
            'connect_timeout': 30,
            'application_name': 'toefl_dashboard',
            'options': '-c statement_timeout=30000'  # 30s timeout para queries
        }
    }
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')  # Allow HTTP during local/internal access
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações para uploads em produção (usar storage temporário)
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
