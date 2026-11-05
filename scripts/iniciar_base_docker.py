"""
Deja lista la base al levantar Docker: la instala la primera vez y después solo aplica migraciones.
Se puede ejecutar en cada arranque. La contraseña inicial de admin solo se usa si aún no hay administrador.
"""
import os

from comun import conectar, url
from crear_base_limpia import crear_datos_iniciales, crear_estructura, validar_contrasena
from migrar import aplicar_pendientes


def _consulta(sql: str):
    conexion = conectar(url.database)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()[0]
    finally:
        conexion.close()


def iniciar() -> None:
    if _consulta("SELECT to_regclass('public.usuarios')") is None:
        crear_estructura(url.database)
        print("Base instalada.")
    else:
        conexion = conectar(url.database)
        try:
            aplicadas = aplicar_pendientes(conexion)
        finally:
            conexion.close()
        print(f"Migraciones aplicadas: {', '.join(aplicadas) if aplicadas else 'ninguna, ya estaba al día'}")

    if _consulta("SELECT count(*) FROM usuarios") == 0:
        if not os.getenv("ADMIN_PASSWORD"):
            raise SystemExit("La base no tiene usuarios. Falta ADMIN_PASSWORD en .env.docker.admin")
        crear_datos_iniciales(url.database, validar_contrasena(os.environ["ADMIN_PASSWORD"]))
        print("Usuario inicial creado: admin")


if __name__ == "__main__":
    iniciar()
