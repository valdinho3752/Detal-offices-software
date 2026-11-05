"""
Levanta una instalación de QA limpia, ejecuta las pruebas y escribe los resultados en qa/.
Uso, desde la carpeta del proyecto:
  python qa/automatizacion/ejecutar.py            Instalación limpia y todas las pruebas
  python qa/automatizacion/ejecutar.py --reusar   Usa la instalación que ya esté en marcha
  python qa/automatizacion/ejecutar.py -- -k caja Pasa las opciones siguientes a pytest
"""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))
from apoyo import BASE, RAIZ, RESPALDOS, dc  # noqa: E402

argumentos = sys.argv[1:]
opciones = argumentos[argumentos.index("--") + 1:] if "--" in argumentos else []

if "--reusar" not in argumentos:
    dc("--profile", "herramientas", "down", "-v", comprobar=False)
    shutil.rmtree(RESPALDOS, ignore_errors=True)
    RESPALDOS.mkdir(parents=True)
    print("Construyendo y levantando la instalación de QA...")
    print(dc("up", "--build", "-d")[-400:])

if not opciones:
    # Una ejecución completa decide todo el estado: lo que ya no se prueba no conserva un OK antiguo
    documento = RAIZ / "qa" / "CASOS_DE_PRUEBA.md"
    filas = []
    for fila in documento.read_text(encoding="utf-8").split("\n"):
        if re.match(r"\| [A-Z0-9]{3}-\d+ \|", fila):
            partes = fila.split("|")
            partes[6] = " "
            fila = "|".join(partes)
        filas.append(fila)
    documento.write_text("\n".join(filas), encoding="utf-8")

for _ in range(60):
    estado = subprocess.run(["curl", "-sk", "-o", "NUL", "-w", "%{http_code}", f"{BASE}/api/v1/configuracion/publica"], capture_output=True, text=True).stdout
    if estado == "200":
        break
    time.sleep(2)
else:
    sys.exit("La instalación de QA no respondió a tiempo")
time.sleep(8)  # Da tiempo a la primera copia automática

sys.exit(subprocess.call([sys.executable, "-m", "pytest", str(CARPETA), "-q", "--tb=short", "-p", "no:cacheprovider", *opciones], cwd=RAIZ))
