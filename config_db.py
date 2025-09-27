import os
from sqlalchemy.engine.url import make_url

def build_sqlalchemy_uri():
    # Render injeta DATABASE_URL se você vinculou um Postgres ao serviço
    db_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("RENDER_DATABASE_URL")  # só por segurança
        or "sqlite:///data/app.db"  # disco persistente do Render (local: pasta data)
    )

    # Corrige prefixo (Heroku-style)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    url = make_url(db_url)

    # Se for Postgres, garanta SSL
    if url.drivername.startswith("postgresql"):
        q = dict(url.query)
        if "sslmode" not in q:
            q["sslmode"] = "require"
        url = url.set(query=q)

    return str(url)