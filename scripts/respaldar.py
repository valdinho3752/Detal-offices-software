"""
Crea una copia de seguridad de la base configurada y la comprueba.
Uso: python scripts/respaldar.py [--carpeta RUTA] [--conservar 30]
"""
import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

from comun import RAIZ, herramienta_pg, url

PATRON = "clinica_*.dump"


def respaldar(carpeta: Path, conservar: int) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"clinica_{url.database}_{datetime.now():%Y%m%d_%H%M%S}.dump"
    temporal = destino.with_suffix(".parcial")
    entorno = {**os.environ, "PGPASSWORD": url.password or ""}
    conexion = ["--host", url.host or "localhost", "--port", str(url.port or 5432), "--username", url.username or "postgres"]

    try:
        subprocess.run(
            [herramienta_pg("pg_dump"), *conexion, "--format=custom", f"--file={temporal}", url.database],
            env=entorno, check=True, capture_output=True,
        )
        # Una copia que no se puede leer es peor que no tenerla: da falsa seguridad
        subprocess.run([herramienta_pg("pg_restore"), "--list", str(temporal)], check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        temporal.unlink(missing_ok=True)
        raise SystemExit(f"La copia falló: {error.stderr.decode('utf-8', 'replace').strip()}")

    temporal.rename(destino)

    copias = sorted(carpeta.glob(PATRON), key=lambda archivo: archivo.stat().st_mtime, reverse=True)
    for antigua in copias[conservar:]:
        antigua.unlink()
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carpeta", default=os.getenv("BACKUP_DIR", str(RAIZ / "backups")))
    parser.add_argument("--conservar", type=int, default=30, help="Cantidad de copias que se conservan")
    argumentos = parser.parse_args()
    if argumentos.conservar < 1:
        parser.error("--conservar debe ser al menos 1")
    archivo = respaldar(Path(argumentos.carpeta), argumentos.conservar)
    print(f"Copia creada y comprobada: {archivo} ({archivo.stat().st_size / 1024:.0f} KB)")
