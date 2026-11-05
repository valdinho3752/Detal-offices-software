"""Conexión y herramientas de PostgreSQL que comparten los scripts de operación."""
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import settings  # noqa: E402

url = make_url(settings.DATABASE_URL)


def validar_nombre_base(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", nombre):
        raise SystemExit(f"Nombre de base no válido: {nombre}. Usa minúsculas, números y guion bajo.")
    return nombre


def conectar(base: str):
    return psycopg2.connect(host=url.host, port=url.port, user=url.username, password=url.password, dbname=base)


def base_existe(nombre: str) -> bool:
    conexion = conectar("postgres")
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre,))
            return cursor.fetchone() is not None
    finally:
        conexion.close()


def ejecutar_sin_transaccion(sql: str) -> None:
    conexion = conectar("postgres")
    conexion.autocommit = True
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
    finally:
        conexion.close()


def herramienta_pg(nombre: str) -> str:
    """Busca pg_dump o pg_restore en PG_BIN, en el PATH o en la instalación habitual de Windows."""
    if os.getenv("PG_BIN"):
        return str(Path(os.environ["PG_BIN"]) / nombre)
    encontrada = shutil.which(nombre)
    if encontrada:
        return encontrada
    instaladas = sorted(glob.glob(rf"C:\Program Files\PostgreSQL\*\bin\{nombre}.exe"))
    if instaladas:
        return instaladas[-1]
    raise SystemExit(f"No se encontró {nombre}. Indica su carpeta en la variable PG_BIN.")


def ejecutar_pg(nombre: str, *argumentos: str) -> str:
    entorno = {**os.environ, "PGPASSWORD": url.password or ""}
    conexion = ["--host", url.host or "localhost", "--port", str(url.port or 5432), "--username", url.username or "postgres"]
    resultado = subprocess.run(
        [herramienta_pg(nombre), *conexion, *argumentos], env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if resultado.returncode != 0:
        raise SystemExit(f"{nombre} falló: {resultado.stderr.strip()}")
    return resultado.stdout
