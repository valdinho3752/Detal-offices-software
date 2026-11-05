"""
Aplica las migraciones pendientes, en orden y cada una en su propia transacción.
Uso: python database/migrar.py [--solo-marcar]
  --solo-marcar registra todas como aplicadas sin ejecutarlas, para una base que ya las tiene.
"""
import argparse
import sys
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

CARPETA = Path(__file__).resolve().parent / "migraciones"
CREAR_REGISTRO = """
    CREATE TABLE IF NOT EXISTS migraciones_aplicadas (
        nombre VARCHAR(200) PRIMARY KEY,
        aplicada_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
"""


def archivos_migracion():
    return sorted(CARPETA.glob("*.sql"))


def _aplicadas(cursor) -> set:
    cursor.execute(CREAR_REGISTRO)
    cursor.execute("SELECT nombre FROM migraciones_aplicadas")
    return {fila[0] for fila in cursor.fetchall()}


def _registrar(cursor, nombre: str) -> None:
    cursor.execute("INSERT INTO migraciones_aplicadas (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nombre,))


def marcar_todas(conexion) -> list:
    with conexion.cursor() as cursor:
        ya_aplicadas = _aplicadas(cursor)
        nuevas = [a.name for a in archivos_migracion() if a.name not in ya_aplicadas]
        for nombre in nuevas:
            _registrar(cursor, nombre)
    conexion.commit()
    return nuevas


def aplicar_pendientes(conexion) -> list:
    with conexion.cursor() as cursor:
        ya_aplicadas = _aplicadas(cursor)
    conexion.commit()

    aplicadas = []
    for archivo in archivos_migracion():
        if archivo.name in ya_aplicadas:
            continue
        try:
            with conexion.cursor() as cursor:
                cursor.execute(archivo.read_text(encoding="utf-8"))
                _registrar(cursor, archivo.name)
            conexion.commit()
        except psycopg2.Error as error:
            conexion.rollback()
            raise SystemExit(f"La migración {archivo.name} falló y no se aplicó: {error}")
        aplicadas.append(archivo.name)
    return aplicadas


if __name__ == "__main__":
    from app.config import settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo-marcar", action="store_true")
    argumentos = parser.parse_args()

    url = make_url(settings.DATABASE_URL)
    conexion = psycopg2.connect(host=url.host, port=url.port, user=url.username, password=url.password, dbname=url.database)
    try:
        nombres = marcar_todas(conexion) if argumentos.solo_marcar else aplicar_pendientes(conexion)
    finally:
        conexion.close()
    accion = "Marcadas como aplicadas" if argumentos.solo_marcar else "Aplicadas"
    print(f"Base {url.database}. {accion}: {', '.join(nombres) if nombres else 'ninguna, ya estaba al día'}")
