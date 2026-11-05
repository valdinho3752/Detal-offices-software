from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Motor de conexión a PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
    # La fecha de hoy y las horas de las citas deben seguir el reloj de la clínica, no el del servidor
    connect_args={"options": f"-c timezone={settings.CLINICA_TIMEZONE}"} if settings.CLINICA_TIMEZONE else {},
)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para todos los modelos ORM
Base = declarative_base()

def get_db() -> Generator:
    """
    Inyector de dependencia para FastAPI.
    Proporciona una sesión de base de datos aislada por petición y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
