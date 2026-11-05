"""
Genera las claves para Docker en .env.docker y .env.docker.admin. No sobrescribe archivos existentes.
Uso: python scripts/preparar_docker.py --zona America/La_Paz
Solo usa la biblioteca estándar: no necesita el entorno virtual.
"""
import argparse
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / ".env.docker.example"
CONFIGURACION = RAIZ / ".env.docker"
ADMIN = RAIZ / ".env.docker.admin"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zona", required=True, help="Zona horaria de la clínica, ej. America/La_Paz")
    zona = parser.parse_args().zona

    existentes = [archivo.name for archivo in (CONFIGURACION, ADMIN) if archivo.exists()]
    if existentes:
        raise SystemExit(f"Ya existe {', '.join(existentes)} y no se modificó. Si quieres regenerarlo, bórralo primero.")

    # Hexadecimal: la contraseña va dentro de la dirección de conexión y no admite otros símbolos
    clave_bd = secrets.token_hex(24)
    contenido = (
        PLANTILLA.read_text(encoding="utf-8")
        .replace("CAMBIAR_CLAVE_BD", clave_bd)
        .replace("CAMBIAR_CLAVE_JWT", secrets.token_urlsafe(48))
        .replace("CAMBIAR_ZONA", zona)
    )
    contrasena_admin = secrets.token_urlsafe(15)
    CONFIGURACION.write_text(contenido, encoding="utf-8")
    ADMIN.write_text(f"ADMIN_PASSWORD={contrasena_admin}\n", encoding="utf-8")

    print(f"Configuración creada. Zona horaria: {zona}")
    print(f"Usuario: admin  Contraseña inicial: {contrasena_admin}")
    print("Guárdala en un lugar seguro. Después inicia con: docker compose up --build -d")


if __name__ == "__main__":
    main()
