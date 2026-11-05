"""
Recupera el acceso de un administrador: lo reactiva, cambia su contraseña y cierra sus sesiones.
Toma la contraseña de ADMIN_PASSWORD o la pide por pantalla.
Uso: python scripts/restablecer_admin.py [usuario]
"""
import argparse
import getpass
import os

from comun import conectar, url

from app.core.contrasenas import validar_contrasena
from app.core.security import hash_password


def restablecer(usuario: str, contrasena: str) -> None:
    try:
        validar_contrasena(contrasena)
    except ValueError as error:
        raise SystemExit(str(error))

    conexion = conectar(url.database)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE usuarios u
                SET password_hash = %s, activo = true, debe_cambiar_contrasena = false, version_sesion = version_sesion + 1
                FROM roles r
                WHERE r.id = u.rol_id AND r.codigo = 'ADMIN' AND u.username = %s
                """,
                (hash_password(contrasena), usuario),
            )
            if cursor.rowcount != 1:
                raise SystemExit(f"No existe un administrador con el usuario {usuario}")
        conexion.commit()
    finally:
        conexion.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usuario", nargs="?", default="admin")
    nombre = parser.parse_args().usuario
    contrasena = os.getenv("ADMIN_PASSWORD")
    if not contrasena:
        contrasena = getpass.getpass("Contraseña nueva: ")
        if contrasena != getpass.getpass("Repítela: "):
            raise SystemExit("Las contraseñas no coinciden")
    restablecer(nombre, contrasena)
    print(f"Acceso de {nombre} restablecido. Sus sesiones anteriores quedaron cerradas.")
