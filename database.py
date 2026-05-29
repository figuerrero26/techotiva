from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# ─── Engine PostgreSQL ────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # verifica conexión antes de usarla
    pool_size=10,             # conexiones en pool
    max_overflow=20,          # conexiones extra bajo demanda
    echo=settings.app_env == "development",  # muestra SQL solo en dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ─── Dependencia FastAPI ──────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()