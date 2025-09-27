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
    
    # Configuração do PostgreSQL para produção com SSL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        DATABASE_URL = 'postgresql://user:password@localhost/toefl_dashboard'
    else:
        # Corrige prefixo heroku-like e força SSL no Render
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # Adiciona SSL se for PostgreSQL e não tiver sslmode
        try:
            url = make_url(DATABASE_URL)
            if url.drivername.startswith('postgresql'):
                query = dict(url.query)
                if 'sslmode' not in query:
                    query['sslmode'] = 'require'
                url = url.set(query=query)
                DATABASE_URL = str(url)
        except Exception:
            # Se falhar o parsing, mantém a URL original
            pass
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Configurações do SQLAlchemy otimizadas para Render
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 0,
        'pool_recycle': 300,
    }
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True
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