"""
Restaura una copia en una base NUEVA. Nunca sobrescribe una base existente:
así se puede revisar el resultado antes de cambiar DB_NAME y DATABASE_URL en .env.
Uso: python scripts/restaurar.py ARCHIVO.dump --base NOMBRE_NUEVO
"""
import argparse
from pathlib import Path

from comun import base_existe, conectar, ejecutar_pg, ejecutar_sin_transaccion, validar_nombre_base

TABLAS_CLAVE = ["usuarios", "pacientes", "citas", "planes_tratamiento", "visitas_evolucion", "pagos", "egresos_caja", "cajas_sesiones"]


def contar_filas(base: str) -> dict:
    conexion = conectar(base)
    try:
        with conexion.cursor() as cursor:
            conteos = {}
            for tabla in TABLAS_CLAVE:
                cursor.execute(f"SELECT count(*) FROM {tabla}")
                conteos[tabla] = cursor.fetchone()[0]
            return conteos
    finally:
        conexion.close()


def restaurar(archivo: Path, base: str) -> dict:
    validar_nombre_base(base)
    if not archivo.is_file():
        raise SystemExit(f"No existe el archivo {archivo}")
    if base_existe(base):
        raise SystemExit(f"La base {base} ya existe. Elige otro nombre: la restauración nunca sobrescribe.")

    ejecutar_sin_transaccion(f'CREATE DATABASE "{base}"')
    try:
        ejecutar_pg("pg_restore", "--no-owner", "--exit-on-error", f"--dbname={base}", str(archivo))
    except SystemExit:
        ejecutar_sin_transaccion(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)')
        raise
    return contar_filas(base)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--base", required=True)
    argumentos = parser.parse_args()
    filas = restaurar(argumentos.archivo, argumentos.base)
    print(f"Copia restaurada en la base {argumentos.base}. Filas restauradas:")
    for tabla, cantidad in filas.items():
        print(f"  {tabla}: {cantidad}")
