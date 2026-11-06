"""Fixtures de Playwright y registro de resultados por caso de prueba."""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from apoyo import BASE, CLAVE_ADMIN, RAIZ, ZONA, Api, Fabrica  # noqa: E402
from casos_no_automatizables import CASOS  # noqa: E402

DOCUMENTO = RAIZ / "qa" / "CASOS_DE_PRUEBA.md"
RESULTADOS = RAIZ / "qa" / "resultados"
CAPTURAS = RESULTADOS / "capturas"
resultados_por_caso = defaultdict(list)


def pytest_configure(config):
    config.addinivalue_line("markers", "caso(*ids): casos de CASOS_DE_PRUEBA.md que cubre la prueba")
    CAPTURAS.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def navegador(pw):
    edge = pw.chromium.launch(channel="msedge", headless=True)
    yield edge
    edge.close()


@pytest.fixture(scope="session")
def solicitudes(pw):
    contexto = pw.request.new_context(ignore_https_errors=True)
    yield contexto
    contexto.dispose()


@pytest.fixture(scope="session")
def api(solicitudes):
    respuesta = Api(solicitudes).login("admin", CLAVE_ADMIN)
    assert respuesta.status == 200, f"No se pudo entrar como admin a la instalación de QA: {respuesta.text}"
    return Api(solicitudes, respuesta.json()["access_token"])


@pytest.fixture(scope="session")
def fab(api):
    return Fabrica(api)


@pytest.fixture
def sin_sesion(solicitudes):
    return Api(solicitudes)


@pytest.fixture
def abrir(navegador, request):
    """Abre el sistema en un contexto limpio. Sin usuario, queda en la pantalla de acceso."""
    contextos, paginas = [], []
    request.node.paginas = paginas
    request.node.errores_js = []

    def _abrir(alias=None, clave=None, ancho=1500, alto=950, tema=None, ruta=None, reloj=None, zona=ZONA, reloj_vivo=False):
        contexto = navegador.new_context(viewport={"width": ancho, "height": alto}, ignore_https_errors=True, timezone_id=zona, locale="es-BO")
        contextos.append(contexto)
        pagina = contexto.new_page()
        paginas.append(pagina)
        pagina.on("pageerror", lambda e: request.node.errores_js.append(f"{pagina.url}: {str(e)[:200]}"))
        if reloj:
            pagina.clock.set_fixed_time(reloj)
        if reloj_vivo:
            pagina.clock.install()
        if tema:
            pagina.add_init_script(f"localStorage.setItem('tema_preferido', '{tema}')")
        pagina.goto(f"{BASE}/login")
        if alias:
            pagina.fill('input[type="text"]', alias)
            pagina.fill('input[type="password"]', clave)
            pagina.click('button[type="submit"]')
            pagina.wait_for_url(f"{BASE}/")
            pagina.wait_for_load_state("networkidle")
        if ruta is not None:
            pagina.goto(f"{BASE}/{ruta}")
            pagina.wait_for_load_state("networkidle")
            pagina.wait_for_timeout(250)
        return pagina

    yield _abrir
    assert not request.node.errores_js, f"Errores de JavaScript: {request.node.errores_js[:3]}"
    for contexto in contextos:
        contexto.close()


@pytest.fixture
def como_admin(abrir):
    def _entrar(ruta=None, **opciones):
        return abrir("admin", CLAVE_ADMIN, ruta=ruta, **opciones)
    return _entrar


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    informe = resultado.get_result()
    fallo = informe.when in ("setup", "teardown") and informe.failed or informe.when == "call"
    if not fallo:
        return
    if informe.when == "call" and informe.passed:
        marcado = "OK"
    elif informe.failed:
        marcado = "FALLA"
    else:
        return

    detalle = ""
    if informe.failed:
        detalle = str(informe.longrepr.reprcrash.message if hasattr(informe.longrepr, "reprcrash") and informe.longrepr.reprcrash else informe.longrepr)
        for indice, pagina in enumerate(getattr(item, "paginas", [])):
            try:
                pagina.screenshot(path=str(CAPTURAS / f"{item.name}_{indice}.png"), full_page=True)
            except Exception:  # La captura es una ayuda: no debe cambiar el resultado
                pass
    via = "UI" if "test_ui" in item.nodeid else "API"
    for marcador in item.iter_markers("caso"):
        for caso in marcador.args:
            resultados_por_caso[caso].append((marcado, detalle[:400], item.name, via))


def pytest_sessionfinish(session, exitstatus):
    if not resultados_por_caso:
        return
    resumen = {}
    for caso, intentos in resultados_por_caso.items():
        fallos = [i for i in intentos if i[0] == "FALLA"]
        resumen[caso] = {
            "estado": "FALLA" if fallos else "OK",
            "detalle": fallos[0][1] if fallos else "",
            "prueba": (fallos or intentos)[0][2],
            "via": "UI" if any(i[3] == "UI" for i in intentos) else "API",
        }
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / "resultados.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    # La columna Estado del documento se escribe desde aquí
    texto = DOCUMENTO.read_text(encoding="utf-8")
    lineas = []
    for linea in texto.split("\n"):
        coincide = re.match(r"\| ([A-Z0-9]{3}-\d+) \|", linea)
        if coincide:
            identificador = coincide.group(1)
            estado = resumen.get(identificador, {}).get("estado")
            # Una falla siempre se muestra; un OK no aprueba lo que todavía requiere otra comprobación
            if identificador in CASOS and estado != "FALLA":
                estado = CASOS[identificador][0]
            if estado:
                partes = linea.split("|")
                partes[6] = f" {estado} "
                linea = "|".join(partes)
        lineas.append(linea)
    DOCUMENTO.write_text("\n".join(lineas), encoding="utf-8")

    filas = [l for l in lineas if re.match(r"\| [A-Z0-9]{3}-\d+ \|", l)]
    total = len(filas)
    cuenta = defaultdict(int)
    for fila in filas:
        cuenta[fila.split("|")[6].strip() or "Pendiente"] += 1
    fallos = {k: v for k, v in resumen.items() if v["estado"] == "FALLA"}
    salida = [
        "# Resultados de QA", "",
        f"Última ejecución: {datetime.now():%Y-%m-%d %H:%M}, contra {BASE}.", "",
        "| Estado | Casos |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(cuenta.items())],
        f"| **Total** | **{total}** |", "",
        f"Automatizados en esta ejecución: {len(resumen)} ({sum(1 for v in resumen.values() if v['via'] == 'UI')} en pantalla y {sum(1 for v in resumen.values() if v['via'] == 'API')} por API).", "",
    ]
    if fallos:
        salida += ["## Fallos", "", "| Caso | Prueba | Detalle |", "|---|---|---|"]
        for caso, datos in sorted(fallos.items()):
            detalle = re.sub(r"\s+", " ", datos["detalle"]).replace("|", "/")[:220]
            salida.append(f"| {caso} | `{datos['prueba']}` | {detalle} |")
    if CASOS:
        salida += ["", "## Falta comprobar o decidir", "", "| Caso | Estado | Prio | Motivo |", "|---|---|---|---|"]
        prioridades = {f.split("|")[1].strip(): f.split("|")[5].strip() for f in filas}
        for identificador, (estado, motivo) in sorted(CASOS.items(), key=lambda c: (c[1][0], prioridades.get(c[0], ""), c[0])):
            salida.append(f"| {identificador} | {estado} | {prioridades.get(identificador, '')} | {motivo} |")
    (RESULTADOS / "RESUMEN.md").write_text("\n".join(salida) + "\n", encoding="utf-8")
