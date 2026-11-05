"""Condiciones mínimas de seguridad para arrancar en producción."""
from typing import List

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Usuario

# Publicada en versiones anteriores del código: ya no sirve como secreto
CLAVE_JWT_PUBLICADA = "dental_clinic_super_secret_jwt_key_2026"
CLAVES_BD_INSEGURAS = {None, "", "1234", "postgres", "admin", "password"}
LARGO_MINIMO_CLAVE_JWT = 32


def problemas_de_configuracion(config) -> List[str]:
    problemas = []
    if config.DEBUG:
        problemas.append("DEBUG debe ser False")
    if config.SECRET_KEY == CLAVE_JWT_PUBLICADA or len(config.SECRET_KEY or "") < LARGO_MINIMO_CLAVE_JWT:
        problemas.append(f"SECRET_KEY debe ser una clave propia de al menos {LARGO_MINIMO_CLAVE_JWT} caracteres")
    if make_url(config.DATABASE_URL).password in CLAVES_BD_INSEGURAS:
        problemas.append("La contraseña de PostgreSQL es insegura")
    if not config.CLINICA_TIMEZONE.strip():
        problemas.append("CLINICA_TIMEZONE es obligatoria, ej. America/La_Paz")
    if "*" in config.origenes_cors:
        problemas.append("CORS_ORIGINS no puede ser *")
    return problemas


def exigir_configuracion_segura(config) -> None:
    problemas = problemas_de_configuracion(config)
    if problemas:
        raise RuntimeError("No se puede arrancar en producción: " + "; ".join(problemas))


def exigir_contrasena_admin_propia(db: Session) -> None:
    admin = db.query(Usuario).filter(Usuario.username == "admin").first()
    if admin and verify_password("admin123", admin.password_hash):
        raise RuntimeError("No se puede arrancar en producción: el usuario admin conserva la contraseña de demostración")
