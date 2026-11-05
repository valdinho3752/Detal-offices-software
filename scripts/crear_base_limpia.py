"""
Crea una base nueva y vacía para empezar a usar el sistema. Nunca toca una base existente.
La contraseña del administrador se toma de ADMIN_PASSWORD o se pide por pantalla.
Uso: python scripts/crear_base_limpia.py NOMBRE
"""
import argparse
import getpass
import os
import subprocess
import sys

from comun import RAIZ, base_existe, conectar, ejecutar_sin_transaccion, url, validar_nombre_base

sys.path.insert(0, str(RAIZ / "database"))
from migrar import marcar_todas  # noqa: E402

LARGO_MINIMO = 12


def validar_contrasena(contrasena: str) -> str:
    if len(contrasena or "") < LARGO_MINIMO or contrasena == "admin123":
        raise SystemExit(f"La contraseña del administrador debe tener al menos {LARGO_MINIMO} caracteres")
    return contrasena


def _pedir_contrasena() -> str:
    contrasena = os.getenv("ADMIN_PASSWORD")
    if not contrasena:
        contrasena = getpass.getpass("Contraseña del usuario admin: ")
        if contrasena != getpass.getpass("Repítela: "):
            raise SystemExit("Las contraseñas no coinciden")
    return validar_contrasena(contrasena)


def crear_estructura(nombre: str) -> None:
    """Todo en una transacción: un fallo no deja una base a medias."""
    conexion = conectar(nombre)
    try:
        with conexion.cursor() as cursor:
            cursor.execute((RAIZ / "database" / "schema.sql").read_text(encoding="utf-8"))
        conexion.commit()
        marcar_todas(conexion)
    finally:
        conexion.close()


def crear_datos_iniciales(nombre: str, contrasena: str) -> None:
    entorno = {
        **os.environ,
        "DATABASE_URL": url.set(database=nombre).render_as_string(hide_password=False),
        "ADMIN_PASSWORD": contrasena,
        "DEBUG": "False",
        "PYTHONIOENCODING": "utf-8",
    }
    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "database" / "seed.py")], env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if resultado.returncode != 0:
        raise SystemExit(f"No se pudieron crear los datos iniciales: {resultado.stderr.strip()[-500:]}")


def crear(nombre: str, contrasena: str) -> None:
    validar_nombre_base(nombre)
    if base_existe(nombre):
        raise SystemExit(f"La base {nombre} ya existe y no se modificó.")

    ejecutar_sin_transaccion(f'CREATE DATABASE "{nombre}"')
    try:
        crear_estructura(nombre)
        crear_datos_iniciales(nombre, contrasena)
    except BaseException:
        ejecutar_sin_transaccion(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nombre")
    argumentos = parser.parse_args()
    validar_nombre_base(argumentos.nombre)
    crear(argumentos.nombre, _pedir_contrasena())
    print(f"Base {argumentos.nombre} creada, sin pacientes ni datos de prueba. Usuario inicial: admin")
    print(f"Siguiente paso: indica DB_NAME={argumentos.nombre} y DATABASE_URL en el archivo .env de producción.")
