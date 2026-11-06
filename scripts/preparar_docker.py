"""
Deja lista la configuración de Docker con la zona horaria de este equipo, que es el servidor de la clínica.
La primera vez genera las claves en .env.docker y .env.docker.admin. Después solo actualiza la zona: las claves no cambian.

Uso:
  python scripts/preparar_docker.py --levantar          Toma la zona del equipo, construye e inicia el sistema
  python scripts/preparar_docker.py                     Solo prepara la configuración
  python scripts/preparar_docker.py --zona America/La_Paz --levantar   Usa otra zona

Solo usa la biblioteca estándar: no necesita el entorno virtual.
"""
import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Optional

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / ".env.docker.example"
CONFIGURACION = RAIZ / ".env.docker"
ADMIN = RAIZ / ".env.docker.admin"
ZONA_VALIDA = re.compile(r"^[A-Za-z_]+(/[A-Za-z0-9_+-]+)+$")


def _zona_de_windows() -> Optional[str]:
    # Windows nombra sus zonas a su manera; su propia biblioteca ICU da el nombre estándar
    import ctypes

    icu = ctypes.WinDLL("icu.dll")
    texto = ctypes.create_unicode_buffer(128)
    error = ctypes.c_int(0)
    icu.ucal_getDefaultTimeZone(texto, 128, ctypes.byref(error))
    return texto.value if error.value <= 0 else None


def _zona_de_unix() -> Optional[str]:
    archivo = Path("/etc/timezone")
    if archivo.exists():
        return archivo.read_text(encoding="utf-8").strip()
    enlace = Path("/etc/localtime")
    if enlace.is_symlink():
        return str(enlace.resolve()).split("zoneinfo/")[-1]
    return None


def detectar_zona() -> str:
    try:
        zona = os.environ.get("TZ") or (_zona_de_windows() if sys.platform == "win32" else _zona_de_unix())
    except OSError:
        zona = None
    if not zona or not ZONA_VALIDA.match(zona):
        raise SystemExit("No se pudo detectar la zona horaria de este equipo. Indícala con --zona, ej. --zona America/La_Paz")
    return zona


def crear_configuracion(zona: str) -> None:
    if ADMIN.exists():
        raise SystemExit(f"Existe {ADMIN.name}, pero falta {CONFIGURACION.name}. Si quieres regenerarlos, borra {ADMIN.name} primero.")
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
    print("Guárdala en un lugar seguro.")


def actualizar_zona(zona: str) -> None:
    contenido = CONFIGURACION.read_text(encoding="utf-8")
    actual = re.search(r"^CLINICA_TIMEZONE=(.*)$", contenido, re.M)
    if actual and actual.group(1).strip() == zona:
        print(f"Zona horaria: {zona}")
        return
    linea = f"CLINICA_TIMEZONE={zona}"
    nuevo = re.sub(r"^CLINICA_TIMEZONE=.*$", linea, contenido, flags=re.M) if actual else f"{contenido.rstrip()}\n{linea}\n"
    CONFIGURACION.write_text(nuevo, encoding="utf-8")
    anterior = actual.group(1).strip() if actual else "sin definir"
    print(f"Zona horaria actualizada: {anterior} -> {zona}. Todos los equipos pasarán a mostrar esta hora.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zona", help="Zona horaria, ej. America/La_Paz. Sin indicarla se usa la de este equipo")
    parser.add_argument("--levantar", action="store_true", help="Construye e inicia el sistema: docker compose up --build -d")
    argumentos = parser.parse_args()

    zona = argumentos.zona or detectar_zona()
    if not ZONA_VALIDA.match(zona):
        raise SystemExit(f"La zona {zona!r} no es válida. Ejemplo: America/La_Paz")
    if CONFIGURACION.exists():
        actualizar_zona(zona)
    else:
        crear_configuracion(zona)

    if argumentos.levantar:
        sys.exit(subprocess.call(["docker", "compose", "up", "--build", "-d"], cwd=RAIZ))
    print("Para iniciar el sistema: docker compose up --build -d")


if __name__ == "__main__":
    main()
