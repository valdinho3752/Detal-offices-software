import os
import secrets
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Base de Datos
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "clinica_dental")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # JWT y Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # Orígenes web autorizados, separados por comas. Vacío si la web y la API comparten dirección.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # Define cuándo empieza y termina el día de la clínica, ej. America/La_Paz
    CLINICA_TIMEZONE: str = os.getenv("CLINICA_TIMEZONE", "")

    # Servidor
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def es_produccion(self) -> bool:
        return self.ENV.strip().lower() == "production"

    @property
    def origenes_cors(self) -> list:
        return [origen.strip() for origen in self.CORS_ORIGINS.split(",") if origen.strip()]

settings = Settings()

# En desarrollo basta una clave temporal; en producción falta y el arranque se detiene
if not settings.SECRET_KEY and not settings.es_produccion:
    settings.SECRET_KEY = secrets.token_urlsafe(48)
