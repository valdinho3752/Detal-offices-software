"""Pruebas en pantalla con Microsoft Edge. Cubren lo que una persona ve y hace."""
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from apoyo import ANCHOS, BASE, CLAVE, CLAVE_ADMIN, CLAVE_INICIAL, ZONA, ahora_clinica, campo, desborde_de_main, dia_libre, sql

caso = pytest.mark.caso
RUTAS = ["", "pacientes", "odontograma", "citas", "asistencia", "evolucion", "radiografias", "protesis", "caja", "cobranzas", "nomina", "auditoria", "reportes", "tratamientos", "sillones", "configuracion", "usuarios"]
MENU = {
    "DOCTOR": {"/pacientes", "/odontograma", "/citas", "/asistencia", "/evolucion", "/radiografias", "/protesis", "/nomina"},
    "ASISTENTE": {"/pacientes", "/odontograma", "/citas", "/asistencia", "/evolucion", "/radiografias", "/protesis"},
    "RECEPCION": {"/pacientes", "/citas", "/asistencia", "/protesis", "/caja", "/cobranzas"},
}
EXCLUSIVAS = {"/auditoria", "/reportes", "/tratamientos", "/sillones", "/configuracion", "/usuarios"}


@pytest.fixture(autouse=True)
def _caja_abierta(fab):
    fab.caja()


# ---------------- Acceso ----------------

@caso("ACC-01", "ACC-14", "ACC-21", "PAN-01")
def test_entrar(como_admin):
    p = como_admin()
    assert "Panel Principal" in p.inner_text("main") and "Administrador" in p.inner_text("main")
    assert "admin123" not in p.content()
    p.reload()
    p.wait_for_load_state("networkidle")
    assert p.url == f"{BASE}/"


@caso("ACC-04")
def test_campos_vacios(abrir):
    p = abrir()
    p.click('button[type="submit"]')
    assert p.locator('input[type="text"]').evaluate("e => !e.validity.valid") and "/login" in p.url


@caso("ACC-14", "ACC-24")
def test_pantalla_de_acceso(abrir):
    for ancho, tema in ((1500, "light"), (1500, "dark"), (390, None)):
        p = abrir(ancho=ancho, tema=tema)
        p.wait_for_load_state("networkidle")
        texto = p.inner_text("body")
        assert "Demostración" not in texto and "admin123" not in p.content()
        assert p.locator("h1").inner_text().strip()
        assert p.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


@caso("ACC-15", "ACC-16", "ACC-17")
def test_sesion(como_admin, abrir):
    sin = abrir()
    sin.goto(f"{BASE}/caja")
    sin.wait_for_url(f"{BASE}/login")
    p = como_admin()
    p.goto(f"{BASE}/caja")
    p.wait_for_load_state("networkidle")
    p.locator("aside").get_by_role("button", name="Cerrar Sesión").click()
    p.wait_for_url(f"{BASE}/login")
    p.go_back()
    p.wait_for_url(f"{BASE}/login")
    assert "Gaveta" not in p.inner_text("body"), "El botón Atrás no muestra datos protegidos"
    q = como_admin()
    q.evaluate("localStorage.setItem('token', 'alterado.token.falso')")
    q.reload()
    q.wait_for_url(f"{BASE}/login")


@caso("ACC-05")
def test_mensaje_de_bloqueo_en_pantalla(abrir):
    p = abrir()
    alias = f"cuenta_{uuid4().hex[:8]}"
    for _ in range(6):
        p.fill('input[type="text"]', alias)
        p.fill('input[type="password"]', "Incorrecta1")
        p.click('button[type="submit"]')
        p.wait_for_timeout(350)
    assert "Demasiados intentos" in p.inner_text("body")


# ---------------- Contraseñas ----------------

@caso("PWD-01", "PWD-02", "PWD-06", "PWD-09", "PWD-11", "PWD-15")
def test_primer_ingreso(fab, abrir):
    u = fab.usuario("RECEPCION", cambiar_clave=False)
    p = abrir(u.alias, CLAVE_INICIAL)
    d = p.get_by_role("dialog", name="Cambiar contraseña")
    assert d.count() == 1 and d.get_by_role("button", name="Cancelar").count() == 0

    def llenar(actual, nueva, repetida):
        d.locator("#clave-actual").fill(actual)
        d.locator("#clave-nueva").fill(nueva)
        d.locator("#clave-repetida").fill(repetida)
        d.get_by_role("button", name="Guardar Contraseña").click()
        p.wait_for_timeout(500)

    llenar(CLAVE_INICIAL, "Nueva1234!", "Otra1234!")
    assert "no coinciden" in d.inner_text()
    llenar(CLAVE_INICIAL, "abcdefgh", "abcdefgh")
    alerta = d.get_by_role("alert").inner_text()
    assert "letras y números" in alerta and "[{" not in alerta, alerta
    llenar(CLAVE_INICIAL, CLAVE, CLAVE)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert p.get_by_role("dialog").count() == 0 and "/login" not in p.url
    assert "Panel Principal" in p.inner_text("main")
    assert "Caja" in p.inner_text("main"), "Los datos se cargan tras el cambio"

    p.get_by_role("button", name="Cambiar mi contraseña").click()
    d = p.get_by_role("dialog", name="Cambiar contraseña")
    assert d.get_by_role("button", name="Cancelar").count() == 1
    d.get_by_role("button", name="Cancelar").click()
    assert p.get_by_role("dialog").count() == 0


# ---------------- Menú por rol ----------------

@caso("USU-21", "USU-22", "AUD-07", "REP-17", "SIL-10", "CFG-21", "TRA-12", "NOM-26", "COB-17", "EVO-15", "RAD-12", "ODO-30")
@pytest.mark.parametrize("rol", MENU)
def test_menu_por_rol(fab, abrir, rol):
    u = fab.usuario(rol)
    p = abrir(u.alias, u.clave)
    enlaces = set(p.locator("aside nav a").evaluate_all("e => e.map(a => a.getAttribute('href'))")) - {"/"}
    assert enlaces == MENU[rol], f"{rol}: {enlaces ^ MENU[rol]}"
    prohibidas = {f"/{r}" for r in RUTAS if r} - MENU[rol]
    for ruta in sorted(prohibidas):
        p.goto(BASE + ruta)
        p.wait_for_timeout(150)
        p.wait_for_load_state("networkidle")
        assert p.url == f"{BASE}/", f"{rol} abrió {ruta}"


@caso("USU-21", "PAN-09")
def test_menu_de_administrador(como_admin):
    p = como_admin()
    enlaces = set(p.locator("aside nav a").evaluate_all("e => e.map(a => a.getAttribute('href'))"))
    assert EXCLUSIVAS <= enlaces and {f"/{r}" for r in RUTAS if r} <= enlaces


@caso("PAN-10")
def test_todas_las_pantallas_abren(como_admin):
    p = como_admin()
    for ruta in RUTAS:
        p.goto(f"{BASE}/{ruta}")
        p.wait_for_load_state("networkidle")
        assert not re.search(r"HU-?\d", p.content()), ruta
        assert p.locator("main").inner_text().strip(), ruta


# ---------------- Usuarios ----------------

@caso("USU-01", "USU-09")
def test_usuarios_en_pantalla(fab, como_admin):
    u = fab.usuario("DOCTOR", nombre="Buscable")
    p = como_admin("usuarios")
    assert "Usuarios" in p.inner_text("main")
    buscador = p.get_by_placeholder("Buscar por usuario, nombre o email...")
    for termino in (u.alias, "Buscable", f"{u.alias}@clinica-pruebas.com"):
        buscador.fill(termino)
        p.wait_for_timeout(300)
        assert u.alias in p.inner_text("main"), termino
    buscador.fill("nadie_coincide_xyz")
    p.wait_for_timeout(300)
    assert u.alias not in p.inner_text("main")


# ---------------- Pacientes ----------------

@caso("PAC-01", "PAC-07", "PAC-12", "PAC-10", "PAC-25", "PAC-26", "EVO-25")
def test_registrar_paciente_en_pantalla(api, como_admin):
    p = como_admin("pacientes")
    alertas = []
    p.on("dialog", lambda d: (alertas.append(d.message), d.dismiss()))
    p.get_by_role("button", name="Nuevo Paciente").click()
    f = p.locator("form").last
    f.get_by_role("button", name="Guardar Paciente").click()
    assert p.locator("form").last.is_visible(), "Sin obligatorios no se envía"
    doc = f"UI-{uuid4().hex[:8]}"
    campo(f, "Nombres").fill("<script>alert(1)</script>Ana")
    campo(f, "Apellidos").fill("Prueba")
    campo(f, "Documento").fill(doc)
    campo(f, "Nacimiento").fill("1990-05-10")
    campo(f, "Teléfono").fill("70000000")
    campo(f, "Alergias").fill("Penicilina")
    campo(f, "Sexo").select_option("FEMENINO")
    p.locator("#paciente-direccion").fill("Calle <b>QA</b> 123")
    f.get_by_role("button", name="Guardar Paciente").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert not alertas, "No se ejecutó código del nombre"
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(doc)
    p.wait_for_timeout(600)
    p.wait_for_load_state("networkidle")
    p.locator("main").get_by_text(doc).first.click()
    p.wait_for_timeout(500)
    texto = p.inner_text("main")
    assert "Penicilina" in texto and "Femenino" in texto and "Calle <b>QA</b> 123" in texto
    p.locator("main").get_by_role("button", name=re.compile("Editar")).first.click()
    f = p.locator("form").last
    assert campo(f, "Alergias").input_value() == "Penicilina" and campo(f, "Sexo").input_value() == "FEMENINO"
    campo(f, "Alergias").fill("Látex")
    f.get_by_role("button", name=re.compile("Guardar")).click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert "Látex" in p.inner_text("main"), "La ficha se actualiza sin recargar"
    guardado = next(x for x in api.get("/pacientes/", buscar=doc, busqueda=doc, q=doc, search=doc).json() if x["numero_documento"] == doc)
    assert guardado["genero"] == "FEMENINO" and guardado["email"] is None and guardado["antecedentes"]["alergias"] == "Látex"


@caso("PAC-16", "PAC-24")
def test_buscador_de_pacientes(como_admin):
    p = como_admin("pacientes")
    buscador = p.get_by_placeholder("Buscar por nombre, documento o apellido...")
    assert "RUT" not in buscador.get_attribute("placeholder")
    buscador.fill("nadie_que_coincida_xyz")
    p.wait_for_timeout(700)
    assert "No se encontraron pacientes" in p.inner_text("main")


@caso("PAC-17")
def test_accesos_desde_la_ficha(fab, como_admin):
    paciente = fab.paciente(nombres=f"Acceso{uuid4().hex[:6]}")
    p = como_admin("pacientes")
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(paciente["nombres"])
    p.wait_for_timeout(600)
    p.locator("main").get_by_text(paciente["nombres"]).first.click()
    p.wait_for_timeout(400)
    for nombre, ruta in (("Odontograma", "/odontograma"), ("Evolución", "/evolucion"), ("Radiografías", "/radiografias"), ("Cobranza", "/cobranzas"), ("Agendar Cita", "/citas")):
        enlace = p.locator("main").get_by_role("link", name=nombre)
        enlace = enlace if enlace.count() else p.locator("main").get_by_role("button", name=nombre)
        enlace.first.click()
        p.wait_for_load_state("networkidle")
        assert ruta in p.url and paciente["id"] in p.url, f"{nombre}: {p.url}"
        p.go_back()
        p.wait_for_load_state("networkidle")
        p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(paciente["nombres"])
        p.wait_for_timeout(500)
        p.locator("main").get_by_text(paciente["nombres"]).first.click()
        p.wait_for_timeout(300)


# ---------------- Odontograma ----------------

def _dientes(p):
    return p.locator('[title^="#"]').filter(has=p.locator("svg"))


def _medir(p):
    return p.evaluate("""() => {
      const d = [...document.querySelectorAll('[title^="#"]')].filter(e => e.querySelector('svg'));
      const r = d.map(e => e.getBoundingClientRect());
      const c = d[0].closest('.rounded-2xl.p-5').getBoundingClientRect();
      const m = document.querySelector('main'); const s = getComputedStyle(m);
      const util = m.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
      return {n: d.length, izq: Math.min(...r.map(x => x.left)), der: Math.max(...r.map(x => x.right)), ci: c.left, cd: c.right, util};
    }""")


@caso("ODO-01", "ODO-02", "ODO-36")
def test_denticiones(fab, como_admin):
    fab.paciente()
    p = como_admin("odontograma")
    p.wait_for_selector('[title^="#"]')
    assert _medir(p)["n"] == 32
    texto = p.inner_text("main")
    assert "Diagnóstico y evaluación inicial" in texto and "Alta clínica / Control posterior" in texto
    for pieza in (18, 11, 21, 28, 48, 41, 31, 38):
        assert p.get_by_title(re.compile(f"^#{pieza} ")).count() == 1
    p.get_by_role("button", name=re.compile("Dentición Temporal")).click()
    p.wait_for_timeout(300)
    assert _medir(p)["n"] == 20
    for pieza in (55, 51, 61, 65, 85, 81, 71, 75):
        assert p.get_by_title(re.compile(f"^#{pieza} ")).count() == 1


@caso("ODO-31", "ODO-32")
def test_ancho_del_odontograma(fab, como_admin):
    fab.paciente()
    for ancho in ANCHOS:
        p = como_admin("odontograma", ancho=ancho)
        p.wait_for_selector('[title^="#"]')
        m = _medir(p)
        assert m["izq"] >= m["ci"] and m["der"] <= m["cd"] and (m["der"] - m["izq"]) / m["util"] >= 0.93, (ancho, m)
        p.get_by_title(re.compile("^#16 ")).first.click()
        p.wait_for_timeout(200)
        assert desborde_de_main(p) <= 0, ancho


@caso("ODO-33")
def test_odontograma_en_celular(fab, como_admin):
    fab.paciente()
    p = como_admin("odontograma", ancho=390)
    p.wait_for_selector('[title^="#"]')
    assert desborde_de_main(p) <= 0 and p.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


@caso("ODO-09", "ODO-11")
def test_marcar_y_limpiar_cara(fab, abrir, api):
    nombre = f"Odo{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    p = abrir("admin", CLAVE_ADMIN, ruta=f"odontograma?paciente_id={paciente['id']}")
    p.locator("select").first.select_option(paciente["id"])
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(600)
    p.get_by_title(re.compile("^#16 ")).first.click()
    p.wait_for_timeout(300)
    p.get_by_role("button", name="Marcar Cara Activa").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(700)
    hallazgos = sql(f"select count(*) from hallazgos_superficie h join piezas_dentales d on d.id = h.pieza_dental_id join odontogramas o on o.id = d.odontograma_id where o.paciente_id = '{paciente['id']}' and d.numero_fdi = 16")
    assert int(hallazgos) >= 1
    p.reload()
    p.wait_for_load_state("networkidle")
    p.locator("select").first.select_option(paciente["id"])
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    p.get_by_title(re.compile("^#16 ")).first.click()
    p.wait_for_timeout(300)
    assert "hallazgo(s) registrados" in p.inner_text("main")
    p.get_by_role("button", name="Limpiar Cara").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(700)
    restantes = sql(f"select count(*) from hallazgos_superficie h join piezas_dentales d on d.id = h.pieza_dental_id join odontogramas o on o.id = d.odontograma_id where o.paciente_id = '{paciente['id']}' and d.numero_fdi = 16")
    assert int(restantes) < int(hallazgos)


@caso("ODO-27")
def test_cambiar_de_paciente_no_mezcla(fab, abrir):
    a, b = fab.paciente(nombres="Primero"), fab.paciente(nombres="Segundo")
    p = abrir("admin", CLAVE_ADMIN, ruta="odontograma")
    selector = p.locator("select").first
    selector.select_option(a["id"])
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    selector.select_option(b["id"])
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert selector.input_value() == b["id"]


# ---------------- Agenda ----------------

@caso("AGE-01", "AGE-25", "AGE-31", "SIL-11")
def test_matriz(fab, api, como_admin):
    sillon = api.post("/sillones/", {"nombre": f"Sala{uuid4().hex[:4]}"}).json()
    try:
        p = como_admin("citas")
        p.wait_for_selector("table")
        activos = [s for s in api.get("/sillones/").json() if s["activo"]]
        assert p.locator("thead th").count() - 1 >= len(activos)
        assert f"Los {p.locator('thead th').count() - 1} sillones" in p.inner_text("main")
        assert sillon["nombre"].upper() in p.locator("thead").inner_text().upper()
        filas = p.locator("tbody tr").all_inner_texts()
        assert "07:00" in filas[0] and any("21:30" in f or "22:00" in f for f in filas[-2:])
        hoy = ahora_clinica()
        assert hoy.strftime("%Y-%m-%d") in p.inner_text("main")
        p.get_by_title("Día Siguiente").click()
        p.wait_for_load_state("networkidle")
        assert (hoy + timedelta(days=1)).strftime("%Y-%m-%d") in p.inner_text("main")
        p.get_by_title("Día Anterior").click()
        p.get_by_title("Día Anterior").click()
        p.wait_for_load_state("networkidle")
        assert (hoy - timedelta(days=1)).strftime("%Y-%m-%d") in p.inner_text("main")
    finally:
        api.delete(f"/sillones/{sillon['id']}")


@caso("AGE-15", "CAL-08")
def test_cancelada_visible(fab, api, como_admin):
    paciente = fab.paciente(nombres=f"Canc{uuid4().hex[:6]}")
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    res = fab.cita(paciente["id"], hoy, "21:00", "21:30", box=3)
    if res.status != 201:
        pytest.skip(f"Horario ocupado: {res.detalle}")
    cita = res.json()
    assert api.delete(f"/citas/{cita['id']}").status == 204
    p = como_admin("citas")
    p.wait_for_selector("table")
    assert paciente["nombres"] in p.locator("tbody").inner_text()
    p.get_by_role("button", name="Vista Mensual").click()
    p.wait_for_timeout(500)
    assert p.locator(".line-through", has_text=paciente["nombres"][:8]).count() >= 1


@caso("AGE-32", "CAL-11")
def test_ancho_de_la_agenda(como_admin):
    for ancho in ANCHOS:
        p = como_admin("citas", ancho=ancho)
        p.wait_for_selector("table")
        m = p.evaluate("""() => {
          const t = document.querySelector('table').getBoundingClientRect();
          const m = document.querySelector('main'); const s = getComputedStyle(m);
          const c = [...document.querySelectorAll('thead th')].slice(1).map(x => Math.round(x.getBoundingClientRect().width));
          return {t: t.width, util: m.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight), dif: Math.max(...c) - Math.min(...c)};
        }""")
        assert m["t"] / m["util"] >= 0.99 and m["dif"] <= 1, (ancho, m)
        assert desborde_de_main(p) <= 0
        p.get_by_role("button", name="Vista Mensual").click()
        p.wait_for_timeout(300)
        a = p.evaluate("""() => {
          const r = [...document.querySelectorAll('[title^="Click para seleccionar día"]')].map(c => c.getBoundingClientRect());
          const m = document.querySelector('main'); const s = getComputedStyle(m);
          return (Math.max(...r.map(x => x.right)) - Math.min(...r.map(x => x.left))) / (m.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight));
        }""")
        assert a >= 0.95, (ancho, a)


@caso("CAL-01", "CAL-03", "CAL-05", "CAL-12")
def test_vista_mensual(como_admin):
    p = como_admin("citas")
    p.get_by_role("button", name="Vista Mensual").click()
    p.wait_for_timeout(300)
    cabecera = p.locator(".grid-cols-7").first.inner_text().upper()
    assert cabecera.strip().startswith("LUN")
    dias = p.locator('[title^="Click para seleccionar día"]')
    assert dias.count() % 7 == 0 and dias.count() >= 28
    p.get_by_title("Mes Siguiente").click()
    p.wait_for_load_state("networkidle")
    p.get_by_role("button", name="Hoy").click()
    p.wait_for_load_state("networkidle")
    assert p.locator(".bg-teal-500").count() >= 1, "El día actual se resalta"
    dias.nth(15).dblclick()
    p.wait_for_timeout(300)
    f = p.locator("form").last
    assert f.get_by_role("button", name="Agendar Cita").count() == 1
    assert f.locator('input[type="date"]').first.input_value()[:7] == ahora_clinica().strftime("%Y-%m"), "Abre con la fecha elegida"
    q = como_admin("citas", ancho=390)
    q.get_by_role("button", name="Vista Mensual").click()
    q.wait_for_timeout(300)
    assert q.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


@caso("PAN-07")
def test_doctor_no_avanza_cita_ajena(fab, abrir):
    doc, otro = fab.usuario("DOCTOR"), fab.usuario("DOCTOR")
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    res = fab.cita(fab.paciente()["id"], hoy, "20:00", "20:30", box=2, doctor=otro.doctor_id)
    assert res.status == 201, res.text
    p = abrir(doc.alias, doc.clave)
    assert p.locator("main").get_by_role("button", name=re.compile("Recepción|Llegó")).count() == 0
    fab.admin.delete(f"/citas/{res.json()['id']}")


# ---------------- Evolución ----------------

@caso("EVO-05", "EVO-06", "EVO-07", "EVO-21", "EVO-22")
def test_evolucion_en_pantalla(fab, api, abrir):
    paciente = fab.paciente()
    cita = fab.cita(paciente["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    p = abrir("admin", CLAVE_ADMIN, ruta=f"evolucion?paciente_id={paciente['id']}", reloj=noche)
    p.wait_for_timeout(500)
    assert "DIAGNÓSTICO (TOMADO DEL ODONTOGRAMA)" in p.inner_text("main").upper()
    assert "OBSERVACIONES CLÍNICAS / DIAGNÓSTICO" not in p.inner_text("main").upper()
    p.get_by_role("button", name="Nueva Nota de Evolución").first.click()
    p.wait_for_timeout(300)
    f = p.locator("form").last
    assert "no se puede modificar" in f.inner_text()
    fecha = f.locator('input[type="datetime-local"]').first.input_value()
    assert fecha == noche.strftime("%Y-%m-%dT%H:%M"), fecha
    f.get_by_placeholder("ej. Control de endodoncia").fill("Control")
    f.get_by_placeholder("Se realizó aislamiento absoluto").fill("Profilaxis")
    f.locator('input[type="datetime-local"]').first.fill(noche.strftime("%Y-%m-%dT09:15"))
    f.get_by_role("button", name="Guardar Evolución").click()
    p.wait_for_timeout(300)
    assert f.locator("#visita-diagnostico").evaluate("e => !e.validity.valid"), "Exige diagnóstico"
    f.locator("#visita-diagnostico").fill("Gingivitis marginal")
    f.get_by_role("button", name="Guardar Evolución").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(600)
    assert "Gingivitis marginal" in p.inner_text("main") and "Registrada manualmente" in p.inner_text("main")
    guardada = next(v for v in api.get("/visitas/", paciente_id=paciente["id"]).json() if not v["generada_automaticamente"])
    assert datetime.fromisoformat(guardada["fecha_hora"]).astimezone(ZoneInfo(ZONA)).strftime("%Y-%m-%dT%H:%M") == noche.strftime("%Y-%m-%dT09:15"), "Conserva la hora, sin desfase"
    assert p.locator("main").get_by_role("button", name="Editar").count() == 0


@caso("EVO-11", "EVO-25")
def test_observacion_en_pantalla(fab, api, como_admin):
    paciente = fab.paciente()
    cita = fab.cita(paciente["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    p = como_admin(f"evolucion?paciente_id={paciente['id']}")
    p.wait_for_timeout(400)
    p.get_by_placeholder(re.compile("Una vez guardada no se puede modificar")).first.fill("<img src=x onerror=window.__x=1>Evoluciona bien")
    p.get_by_role("button", name="Agregar", exact=True).first.click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    texto = p.inner_text("main")
    assert "<img src=x onerror=window.__x=1>Evoluciona bien" in texto and "RolCodigoEnum" not in texto
    assert p.evaluate("window.__x") is None, "Se muestra como texto"
    assert "Administrador Principal" in texto, "Muestra al autor"


# ---------------- Radiografías ----------------

@caso("RAD-06", "RAD-07", "RAD-09", "RAD-16")
def test_radiografias_en_pantalla(fab, api, abrir):
    paciente = fab.paciente()
    base = {"paciente_id": paciente["id"], "tipo_estudio": "PERIAPICAL", "archivo_url": "https://ejemplo.test/a.jpg"}
    assert api.post("/radiografias/", {**base, "titulo": "Pieza dieciseis", "pieza_fdi": 16}).ok
    assert api.post("/radiografias/", {**base, "titulo": "Pieza veintiuno", "pieza_fdi": 21}).ok
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    p = abrir("admin", CLAVE_ADMIN, ruta=f"radiografias?paciente_id={paciente['id']}", reloj=noche)
    p.wait_for_timeout(500)
    texto = p.inner_text("main")
    assert "Pieza dieciseis" in texto and "Pieza veintiuno" in texto
    filtro = p.get_by_placeholder(re.compile("dejar vacío para ver todas"))
    filtro.fill("16")
    p.wait_for_timeout(400)
    texto = p.inner_text("main")
    assert "Pieza dieciseis" in texto and "Pieza veintiuno" not in texto
    filtro.fill("")
    p.wait_for_timeout(400)
    assert "Pieza veintiuno" in p.inner_text("main")
    p.get_by_role("button", name="Subir Radiografía").click()
    p.wait_for_timeout(300)
    assert p.locator("form").last.locator('input[type="date"]').first.input_value() == noche.strftime("%Y-%m-%d")


# ---------------- Prótesis ----------------

@caso("PRO-07", "PRO-15", "PRO-17")
def test_protesis_en_pantalla(fab, api, abrir):
    paciente = fab.paciente(nombres=f"Pro{uuid4().hex[:6]}")
    enviada = api.post("/protesis/", {"paciente_id": paciente["id"], "doctor_id": fab.doctor, "laboratorio_nombre": "Lab Enviada", "tipo_trabajo": "CORONA_ZIRCONIO"}).json()
    assert api.put(f"/protesis/{enviada['id']}", {"estado": "EN_LABORATORIO"}).ok
    assert api.post("/protesis/", {"paciente_id": paciente["id"], "doctor_id": fab.doctor, "laboratorio_nombre": "Lab QA", "tipo_trabajo": "CORONA_ZIRCONIO", "costo_laboratorio": 85, "color_guia_vita": "A3", "piezas_dentales": "Pieza 16"}).ok
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    p = abrir("admin", CLAVE_ADMIN, ruta="protesis", reloj=noche)
    p.wait_for_timeout(400)
    texto = p.inner_text("main")
    assert "Lab QA" in texto and "$85,00" in texto and "A3" in texto and "Pieza 16" in texto
    p.locator("main select").first.select_option("EN_LABORATORIO")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    texto = p.inner_text("main")
    assert "Lab Enviada" in texto and "Lab QA" not in texto, "El filtro muestra solo ese estado"
    p.get_by_role("button", name=re.compile("Nueva Orden")).first.click()
    p.wait_for_timeout(300)
    assert "Costo Laboratorio ($)" in p.inner_text("body")


# ---------------- Caja ----------------

@caso("CAJ-01", "CAJ-02", "CAJ-03", "CAJ-27", "CAJ-28")
def test_bloqueo_y_apertura(fab, abrir, como_admin):
    doc = fab.usuario("DOCTOR")
    fab.cerrar_caja()
    try:
        d = abrir(doc.alias, doc.clave)
        d.wait_for_timeout(500)
        assert "Abrir Caja" not in d.inner_text("body") and "Gaveta:" not in d.inner_text("header")
        p = como_admin()
        p.wait_for_timeout(500)
        assert "Apertura de Caja Diaria Requerida" in p.inner_text("body")
        entrada = p.locator('input[type="number"]').first
        entrada.fill("750")
        p.get_by_role("button", name=re.compile("Abrir Caja")).click()
        p.get_by_text("Apertura de Caja Diaria Requerida").wait_for(state="hidden")
        assert "$750,00" in p.inner_text("header")
        p.goto(f"{BASE}/caja")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(300)
        assert "-$0,00" not in p.inner_text("main")
    finally:
        fab.caja()


@caso("CAJ-09", "CAJ-15", "CAJ-30")
def test_egreso_y_cierre_en_pantalla(fab, como_admin):
    fab.cerrar_caja()
    assert fab.admin.post("/caja/abrir", {"monto_inicial_fondo": 1000}).status == 201
    try:
        p = como_admin("caja")
        p.get_by_role("button", name="Registrar Egreso").click()
        f = p.locator("form").last
        f.get_by_placeholder("ej. Compra de mascarillas y guantes en farmacia").fill("Guantes")
        f.get_by_placeholder("0.00").fill("100")
        f.locator('button[type="submit"]').click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(500)
        assert "Guantes" in p.inner_text("main") and "$900,00" in p.inner_text("main")
        p.get_by_role("button", name=re.compile("Cerrar Turno")).click()
        f = p.locator("form").last
        f.locator('input[type="number"]').first.fill("900")
        f.locator('button[type="submit"]').click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(600)
        assert not fab.admin.get("/caja/estado").json()["caja_abierta"]
        assert sql("select diferencia_descuadre from cajas_sesiones order by fecha_cierre desc nulls last limit 1") == "0.00"
    finally:
        fab.caja()


# ---------------- Cobranzas ----------------

@caso("COB-16", "COB-18", "ANU-08", "ANU-12", "PAC-18")
def test_cobranzas_en_pantalla(fab, api, abrir, como_admin):
    paciente = fab.paciente(nombres=f"Cob{uuid4().hex[:6]}")
    plan = fab.plan(paciente["id"], 300)
    pago = api.post("/caja/pagos", {"paciente_id": paciente["id"], "plan_id": plan, "monto": 100, "metodo_pago": "TRANSFERENCIA", "referencia_comprobante": "REC-QA"}).json()
    p = como_admin(f"cobranzas?paciente_id={paciente['id']}")
    p.wait_for_timeout(500)
    texto = p.inner_text("main")
    assert "$300,00" in texto and "$100,00" in texto and "$200,00" in texto and "REC-QA" in texto
    p.locator("main").get_by_role("button", name="Anular").first.click()
    f = p.locator("form").last
    f.locator("textarea").fill("Comprobante equivocado")
    f.locator('button[type="submit"]').click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    texto = p.inner_text("main")
    assert "Comprobante equivocado" in texto and "$300,00" in texto
    rec = fab.usuario("RECEPCION")
    r = abrir(rec.alias, rec.clave, ruta=f"cobranzas?paciente_id={paciente['id']}")
    r.wait_for_timeout(500)
    assert r.locator("main").get_by_role("button", name="Anular").count() == 0


@caso("COB-01", "COB-02", "COB-12")
def test_registrar_cobro_en_pantalla(fab, como_admin):
    paciente = fab.paciente()
    fab.plan(paciente["id"], 200)
    p = como_admin(f"cobranzas?paciente_id={paciente['id']}")
    p.wait_for_timeout(500)
    p.get_by_role("button", name="Registrar Abono / Pago").click()
    f = p.locator("form").last
    f.get_by_placeholder("0.00").fill("250")
    f.locator('button[type="submit"]').click()
    p.wait_for_timeout(300)
    monto = f.get_by_placeholder("0.00")
    assert monto.evaluate("e => e.validity.rangeOverflow") and fab.saldo(paciente["id"]) == 200, "El navegador impide enviar más que el saldo"
    assert "$200,00" in f.inner_text()
    monto.fill("50")
    enviar = f.locator('button[type="submit"]')
    enviar.dblclick()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(700)
    assert fab.saldo(paciente["id"]) == 150, "El doble clic no cobra dos veces"


@caso("CCI-01", "CCI-03", "CCI-04")
def test_cuenta_de_cita_en_pantalla(fab, api, como_admin):
    nombre = f"Cta{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    t = fab.tratamiento(100, nombre="Resina compuesta", categoria="RESTAURADORA")
    plan = fab.plan(paciente["id"])
    item = fab.item(plan, t["id"], 100, pieza_fdi=16)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    cita = fab.cita(paciente["id"], item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    p = como_admin("cobranzas")
    p.wait_for_timeout(500)
    p.get_by_role("region", name="Cobros de citas pendientes").get_by_role("button", name=nombre).click()
    p.wait_for_timeout(400)
    assert "Resina compuesta" in p.get_by_label("Concepto 1").input_value()
    p.get_by_role("button", name="Agregar concepto").click()
    p.get_by_label("Concepto 2").fill("Radiografía")
    p.get_by_label("Monto 2").fill("15")
    assert "$115,00" in p.get_by_role("button", name="Confirmar pago").inner_text()
    p.get_by_role("button", name="Guardar cambios").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    guardada = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    assert float(guardada["total"]) == 115 and guardada["estado"] == "PENDIENTE"


# ---------------- Nómina ----------------

@caso("NOM-01", "NOM-02", "NOM-08", "NOM-10", "NOM-13", "NOM-24", "NOM-28")
def test_nomina_en_pantalla(fab, api, abrir, como_admin):
    rec = fab.usuario("RECEPCION", nombre="Rita", apellido=f"N{uuid4().hex[:5]}", salario_base=3000)
    assert api.post("/empleados/pagos", {"usuario_empleado_id": rec.id, "tipo_pago": "ADELANTO", "monto_neto_pagado": 500, "metodo_pago": "TRANSFERENCIA"}).ok
    p = como_admin("nomina")
    selector = p.get_by_label("Empleado")
    selector.select_option(rec.id)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert "$3.000,00" in p.inner_text("main") and "$2.500,00" in p.inner_text("main")
    p.get_by_role("button", name="Registrar Pago / Adelanto").click()
    d = p.get_by_role("dialog", name="Registrar pago")
    assert d.get_by_label("Tipo de pago").locator("option", has_text="comisiones").count() == 0
    d.get_by_label("Tipo de pago").select_option("SUELDO_MENSUAL")
    assert d.get_by_label("Descontar adelantos").input_value() == "500.00" and "$2.500,00" in d.get_by_test_id("neto-sueldo").inner_text()
    d.get_by_role("button", name="Cancelar").click()

    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=40)
    cobro = fab.cobro_directo(fab.paciente()["id"], 1000, doctor_comision_id=doc.doctor_id)
    p.reload()
    p.wait_for_load_state("networkidle")
    p.get_by_label("Empleado").select_option(doc.id)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert "$400,00" in p.inner_text("main") and "-$0,00" not in p.inner_text("main")
    p.get_by_role("button", name="Registrar Pago / Adelanto").click()
    d = p.get_by_role("dialog", name="Registrar pago")
    assert d.get_by_label("Monto a pagar").input_value() == "400.00"
    d.get_by_label("Monto a pagar").fill("400.01")
    d.get_by_label("Pagar en efectivo").uncheck()
    d.get_by_role("button", name="Confirmar Pago").click()
    p.wait_for_timeout(500)
    assert "no puede superar" in d.inner_text()
    d.get_by_label("Monto a pagar").fill("400")
    d.get_by_role("button", name="Confirmar Pago").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert p.get_by_role("dialog").count() == 0
    assert api.post(f"/caja/pagos/{cobro['id']}/anular", {"motivo": "Error"}).ok
    p.reload()
    p.wait_for_load_state("networkidle")
    p.get_by_label("Empleado").select_option(doc.id)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert "Pagado de más" in p.inner_text("main")

    v = abrir(doc.alias, doc.clave, ruta="nomina")
    assert v.get_by_label("Empleado").locator("option").count() == 1
    assert v.get_by_role("button", name="Registrar Pago / Adelanto").count() == 0 and v.get_by_role("button", name="Editar contrato").count() == 0


# ---------------- Asistencia ----------------

@caso("ASI-01", "ASI-02", "ASI-03", "ASI-04", "ASI-05", "ASI-07", "ASI-10", "ASI-11", "ASI-14", "ASI-15", "ASI-16")
def test_asistencia_en_pantalla(fab, abrir):
    u = fab.usuario("RECEPCION", nombre="Rita", apellido="Mamani")
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    p = abrir(u.alias, u.clave, ruta="asistencia", reloj=noche)
    assert p.locator('input[type="date"]').first.input_value() == noche.strftime("%Y-%m-%d")
    p.locator('input[type="date"]').first.fill(ahora_clinica().strftime("%Y-%m-%d"))
    p.wait_for_load_state("networkidle")
    principal = p.locator("main")
    NOMBRES = ["Entrada", "Descanso", "Fin Descanso", "Salida"]
    activos = lambda: {n for n in NOMBRES if principal.get_by_role("button", name=n, exact=True).is_enabled()}

    def marcar(nombre):
        principal.get_by_role("button", name=nombre, exact=True).click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(350)

    assert activos() == {"Entrada"} and "Fuera de turno" in p.get_by_test_id("estado-turno").inner_text()
    assert principal.get_by_role("button", name="Salida", exact=True).get_attribute("title") == "Primero marca tu entrada"
    marcar("Entrada")
    assert activos() == {"Descanso", "Salida"}
    marcar("Descanso")
    assert activos() == {"Fin Descanso"}
    marcar("Fin Descanso")
    assert activos() == {"Descanso", "Salida"}
    marcar("Salida")
    assert activos() == {"Entrada"} and "Turno cerrado" in p.get_by_test_id("estado-turno").inner_text()
    tabla = principal.locator("table").inner_text()
    assert "Rita Mamani" in tabla and "Recepción" in tabla and "--:--" not in tabla and "Inicio de descanso" in tabla
    assert "IP" in principal.locator("table thead").inner_text().upper() and re.search(r"\d+\.\d+\.\d+\.\d+", tabla), "Muestra la IP"
    p.locator("header").get_by_role("button", name="Fichar Turno").click()
    p.wait_for_timeout(400)
    selector = p.get_by_label("Tipo de evento")
    assert selector.locator("option:not([disabled])").all_inner_texts() == ["Entrada"]
    p.get_by_role("button", name="Registrar Marcaje", exact=True).click()
    p.wait_for_timeout(2000)
    assert activos() == {"Descanso", "Salida"}
    assert u.api.post("/auth/fichar", {"tipo_evento": "SALIDA"}).ok
    marcar("Salida")
    assert "turno ya está cerrado" in principal.inner_text() and activos() == {"Entrada"}
    ayer = (ahora_clinica() - timedelta(days=1)).strftime("%Y-%m-%d")
    p.locator('input[type="date"]').first.fill(ayer)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    assert "Rita Mamani" not in principal.inner_text().split("Bitácora")[-1]


@caso("ASI-13", "COR-02", "COR-03", "COR-04", "COR-05", "COR-07", "COR-16")
def test_correccion_en_pantalla(fab, abrir, como_admin):
    u = fab.usuario("RECEPCION", nombre="Olvido", apellido=f"S{uuid4().hex[:5]}")
    assert u.api.post("/auth/fichar", {"tipo_evento": "ENTRADA"}).ok
    sql(f"update registro_asistencia set fecha_hora = (date_trunc('day', now() at time zone '{ZONA}') - interval '1 day' + interval '8 hours') at time zone '{ZONA}' where usuario_id = '{u.id}'")
    v = abrir(u.alias, u.clave, ruta="asistencia")
    assert "quedó sin salida" in v.locator("main").inner_text()
    assert v.get_by_role("button", name="Corregir Marcaje").count() == 0 and v.get_by_role("region", name="Jornadas sin salida").count() == 0
    p = como_admin("asistencia")
    fila = p.get_by_role("region", name="Jornadas sin salida").locator("li").filter(has_text=u.id[:0] + "Olvido")
    fila.first.get_by_role("button", name="Corregir").click()
    d = p.get_by_role("dialog", name="Corregir marcaje")
    assert d.get_by_label("Empleado").input_value() == u.id and d.get_by_label("Marcaje").input_value() == "SALIDA" and d.get_by_label("Hora real").input_value() == ""
    d.get_by_label("Hora real").fill("18:00")
    d.get_by_role("button", name="Guardar Corrección").click()
    p.wait_for_timeout(300)
    assert d.count() == 1, "Exige motivo"
    d.get_by_label("Motivo").fill("Olvidó marcar")
    d.get_by_label("Marcaje").select_option("ENTRADA")
    d.get_by_role("button", name="Guardar Corrección").click()
    p.wait_for_timeout(500)
    assert "No puede haber una entrada después de una entrada" in d.get_by_role("alert").inner_text()
    d.get_by_label("Marcaje").select_option("SALIDA")
    d.get_by_role("button", name="Guardar Corrección").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(600)
    assert p.get_by_role("dialog").count() == 0
    tabla = p.locator("main table").inner_text()
    assert "Corregido" in tabla and "Olvidó marcar" in tabla


@caso("COR-12")
def test_anular_marcaje_en_pantalla(fab, como_admin):
    u = fab.usuario("RECEPCION", nombre="Anula", apellido=f"M{uuid4().hex[:5]}")
    assert u.api.post("/auth/fichar", {"tipo_evento": "ENTRADA"}).ok
    p = como_admin("asistencia")
    p.wait_for_timeout(300)
    fila = p.locator("main table tbody tr").filter(has_text=f"Anula")
    fila.first.get_by_role("button", name="Anular").click()
    d = p.get_by_role("dialog", name="Anular marcaje")
    d.get_by_label("Motivo").fill("Por error")
    d.get_by_role("button", name="Anular Marcaje").click()
    p.wait_for_timeout(600)
    assert "Anulado: Por error" in p.locator("main table").inner_text()


# ---------------- Panel ----------------

@caso("PAN-02", "PAN-04", "PAN-08")
def test_panel(fab, api, abrir):
    fab.cerrar_caja()
    assert api.post("/caja/abrir", {"monto_inicial_fondo": 1234}).status == 201
    try:
        paciente = fab.paciente()
        antiguo = fab.cobro_directo(paciente["id"], 7777)
        inicio_mes = ahora_clinica().replace(day=1)
        sql(f"update pagos set fecha_hora = '{(inicio_mes - timedelta(days=10)).isoformat()}' where id = '{antiguo['id']}'")
        noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
        hoy = noche.strftime("%Y-%m-%d")
        peticiones = []
        p = abrir(reloj=noche)
        p.on("request", lambda q: peticiones.append(q.url))
        p.fill('input[type="text"]', "admin")
        p.fill('input[type="password"]', CLAVE_ADMIN)
        p.click('button[type="submit"]')
        p.wait_for_url(f"{BASE}/")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(400)
        texto = p.inner_text("main")
        assert "$1.234,00" in texto and "Citas para Hoy" in texto
        assert "Ingresos del Mes" in texto and "7.777,00" not in texto
        assert any(f"fecha_inicio={hoy}" in u for u in peticiones), "Pide las citas del día local"
        d = fab.usuario("ASISTENTE")
        q = abrir(d.alias, d.clave)
        texto = q.inner_text("main")
        assert "Caja en Gaveta" not in texto and "Ingresos del Mes" not in texto
    finally:
        fab.caja()


# ---------------- Reportes ----------------

@caso("REP-01", "REP-02", "REP-05", "REP-06", "REP-16", "REP-18")
def test_reportes_en_pantalla(como_admin):
    p = como_admin("reportes")
    grupo = p.get_by_role("group", name="Periodo del reporte")
    assert grupo.get_by_role("button", name="Mes actual", exact=True).get_attribute("aria-pressed") == "true"
    for periodo in ("Hoy", "Esta semana", "Semana pasada", "Mes actual", "Mes pasado", "Últimos 30 días", "Este año", "Todo"):
        peticiones = []
        p.on("request", lambda q: peticiones.append(q.url) if "/reportes/" in q.url else None)
        grupo.get_by_role("button", name=periodo, exact=True).click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(200)
        assert len(peticiones) >= 5, periodo
        assert all(("fecha_" in u) == (periodo != "Todo") for u in peticiones), periodo
    grupo.get_by_role("button", name="Personalizado", exact=True).click()
    entradas = p.locator('input[type="date"]')
    entradas.nth(0).fill("1990-01-01")
    entradas.nth(1).fill("1990-01-31")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    assert "$0,00" in p.inner_text("main") and p.locator("table").count() == 0
    entradas.nth(0).fill("1990-02-15")
    p.wait_for_timeout(300)
    assert "no puede ser posterior" in p.inner_text("main")
    imagenes = p.locator("section img")
    assert imagenes.count() == 2 and all(imagenes.nth(i).evaluate("e => e.naturalWidth > 0") for i in range(2))
    p.get_by_role("button", name=re.compile("Modo (Claro|Oscuro)")).click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert all(imagenes.nth(i).evaluate("e => e.naturalWidth > 0") for i in range(2))


# ---------------- Auditoría ----------------

@caso("AUD-01", "AUD-09")
def test_filtros_de_auditoria(fab, como_admin):
    u = fab.usuario()
    assert u.api.post("/auth/fichar", {"tipo_evento": "ENTRADA"}).ok
    fab.admin.post("/personal/asistencia/correcciones", {"usuario_id": u.id, "tipo_evento": "SALIDA", "fecha_hora": ahora_clinica().isoformat(), "motivo": "QA"})
    p = como_admin("auditoria")
    tabla = p.locator("select").first
    opciones = tabla.locator("option").evaluate_all("e => e.map(o => o.value)")
    reales = {"pacientes", "citas", "odontogramas", "visitas_evolucion", "radiografias_estudios", "ordenes_laboratorio_protesis", "cajas_sesiones", "pagos", "cobros_cita", "pagos_empleados", "registro_asistencia", "catalogo_tratamientos", "sillones", "configuracion_clinica", "usuarios"}
    assert reales <= set(opciones), reales - set(opciones)
    for opcion in sorted(reales):
        tabla.select_option(opcion)
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(250)
        assert p.locator("main table tbody tr").count() >= 1, f"{opcion} no devuelve registros"
    tabla.select_option("pagos")
    p.locator("select").nth(1).select_option("UPDATE")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    acciones = p.locator("main table tbody").inner_text()
    assert "UPDATE" in acciones and "INSERT" not in acciones, "El filtro de acción también se aplica"


# ---------------- Sillones y catálogo ----------------

@caso("SIL-01", "SIL-04")
def test_sillones_en_pantalla(api, como_admin):
    nombre = f"Sala{uuid4().hex[:5]}"
    p = como_admin("sillones")
    p.get_by_role("button", name="Agregar Sillón").click()
    f = p.locator("form").last
    f.locator("input").first.fill(nombre)
    f.get_by_role("button", name="Agregar Sillón").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert nombre in p.inner_text("main")
    p.goto(f"{BASE}/citas")
    p.locator("thead").get_by_text(nombre, exact=False).wait_for()
    creado = next(s for s in api.get("/sillones/").json() if s["nombre"] == nombre)
    api.delete(f"/sillones/{creado['id']}")


@caso("TRA-01")
def test_catalogo_en_pantalla(como_admin):
    codigo = f"Q{uuid4().hex[:6]}"
    p = como_admin("tratamientos")
    p.get_by_role("button", name=re.compile("Nuevo|Agregar")).first.click()
    f = p.locator("form").last
    f.locator("#trat-codigo").fill(codigo) if f.locator("#trat-codigo").count() else f.get_by_placeholder("ej. END-001").fill(codigo)
    f.get_by_placeholder("ej. Endodoncia unirradicular").fill("Limpieza QA")
    f.locator("#trat-precio").fill("120")
    f.locator('button[type="submit"]').click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    p.get_by_placeholder("Buscar por nombre o código...").fill(codigo)
    p.wait_for_timeout(300)
    assert codigo in p.inner_text("main") and "$120,00" in p.inner_text("main")


# ---------------- Configuración ----------------

PNG = None


def _png():
    import struct
    import zlib
    fila = b"\x00" + bytes((220, 40, 90)) * 120
    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", 120, 120, 8, 2, 0, 0, 0)) + trozo(b"IDAT", zlib.compress(fila * 120)) + trozo(b"IEND", b"")


@caso("CFG-01", "CFG-02", "CFG-05", "CFG-06", "CFG-07", "CFG-08", "CFG-10")
def test_marca_en_pantalla(api, abrir, como_admin, tmp_path):
    original = api.get("/configuracion/").json()
    logo = tmp_path / "logo.png"
    logo.write_bytes(_png())
    falso = tmp_path / "falso.png"
    falso.write_bytes(b"no es una imagen")
    grande = tmp_path / "grande.png"
    grande.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (1024 * 1024 + 10))
    svg = tmp_path / "logo.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', encoding="utf-8")
    try:
        p = como_admin("configuracion")
        nombre = f"Clínica QA {uuid4().hex[:4]}"
        p.get_by_label("Nombre de la clínica").fill(nombre)
        p.get_by_role("button", name="Guardar Nombre").click()
        p.wait_for_timeout(500)
        assert nombre in p.inner_text("aside") and p.title() == nombre
        entrada = p.get_by_test_id("archivo-logo")
        for archivo, mensaje in ((falso, "PNG, JPG o WEBP"), (grande, "1 MB"), (svg, "PNG, JPG o WEBP")):
            entrada.set_input_files(str(archivo))
            p.wait_for_timeout(400)
            assert mensaje in p.get_by_role("alert").inner_text(), archivo.name
        icono_antes = p.evaluate("document.querySelector('link[rel~=icon]')?.href")
        # JPG y WEBP reales, generados por el navegador
        for tipo in ("jpeg", "webp"):
            datos = p.evaluate(f"""() => {{ const c = document.createElement('canvas'); c.width = c.height = 40; c.getContext('2d').fillRect(0, 0, 40, 40); return c.toDataURL('image/{tipo}').split(',')[1]; }}""")
            otro = tmp_path / f"logo.{tipo}"
            otro.write_bytes(base64.b64decode(datos))
            entrada.set_input_files(str(otro))
            p.wait_for_timeout(700)
            assert p.locator("aside img").evaluate("e => e.naturalWidth") == 40, tipo
        entrada.set_input_files(str(logo))
        p.wait_for_timeout(700)
        assert p.locator("aside img").evaluate("e => e.naturalWidth") == 120
        assert p.evaluate("document.querySelector('link[rel~=icon]')?.href") != icono_antes or "logo" in (icono_antes or ""), "También en la pestaña"
        v = abrir()
        v.wait_for_load_state("networkidle")
        v.wait_for_timeout(400)
        assert v.locator("h1").inner_text() == nombre and v.locator("img").evaluate("e => e.naturalWidth") == 120
        p.get_by_role("button", name="Quitar logo").click()
        p.wait_for_timeout(500)
        assert p.locator("aside img").count() == 0
    finally:
        api.delete("/configuracion/logo")
        api.put("/configuracion/", {"nombre_clinica": original["nombre_clinica"]})


@caso("CFG-12", "CFG-13", "CFG-14")
def test_tema_por_defecto(api, abrir, como_admin):
    original = api.get("/configuracion/").json()
    es_oscuro = lambda pagina: pagina.evaluate("document.documentElement.classList.contains('dark')")
    try:
        assert api.put("/configuracion/", {"tema_por_defecto": "claro"}).ok
        n = abrir()
        n.wait_for_load_state("networkidle")
        n.wait_for_timeout(300)
        assert not es_oscuro(n), "Un equipo nuevo sigue el tema por defecto"
        p = como_admin()
        p.wait_for_timeout(300)
        assert not es_oscuro(p)
        p.get_by_role("button", name="Modo Oscuro").click()
        p.wait_for_timeout(200)
        assert es_oscuro(p)
        p.reload()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(300)
        assert es_oscuro(p), "Su elección se recuerda"
        p.goto(f"{BASE}/configuracion")
        p.wait_for_load_state("networkidle")
        assert "ya elegiste un tema" in p.inner_text("main")
    finally:
        api.put("/configuracion/", {"tema_por_defecto": original["tema_por_defecto"]})


@caso("CFG-15", "CFG-16", "REP-18", "PRO-15")
def test_moneda_en_pantalla(fab, api, como_admin):
    original = api.get("/configuracion/").json()
    try:
        p = como_admin("configuracion")
        grupo = p.get_by_role("group", name="Moneda de la clínica")
        for simbolo in ("Bs.", "$", "US$", "S/", "€"):
            grupo.get_by_role("button").filter(has_text=simbolo).first.click()
            assert p.get_by_test_id("vista-previa-moneda").inner_text() == f"{simbolo} 1.500,00" or p.get_by_test_id("vista-previa-moneda").inner_text() == f"{simbolo}1.500,00", simbolo
        grupo.get_by_role("button", name=re.compile(r"^Bs\.")).click()
        assert p.get_by_test_id("vista-previa-moneda").inner_text() == "Bs. 1.500,00"
        p.get_by_role("button", name="Guardar Moneda").click()
        p.wait_for_timeout(500)
        assert re.search(r"Gaveta: Bs\. [\d.]+,\d\d", p.inner_text("header"))
        for ruta in ("", "caja", "cobranzas", "nomina", "reportes", "tratamientos", "protesis"):
            p.goto(f"{BASE}/{ruta}")
            p.wait_for_load_state("networkidle")
            p.wait_for_timeout(200)
            assert "$" not in p.inner_text("main"), ruta
        p.goto(f"{BASE}/configuracion")
        p.wait_for_load_state("networkidle")
        p.get_by_label("Otra moneda").fill("COP")
        assert p.get_by_test_id("vista-previa-moneda").inner_text() == "COP 1.500,00"
    finally:
        api.put("/configuracion/", {"moneda_simbolo": original["moneda_simbolo"]})


# Sin caso propio: comprobación adicional
@pytest.mark.parametrize("tema", ["light", "dark"])
def test_recorrer_en_cada_tema(como_admin, tema):
    p = como_admin(tema=tema)
    for ruta in RUTAS:
        p.goto(f"{BASE}/{ruta}")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(120)
        contraste = p.evaluate("""() => {
          const luz = c => { const m = c.match(/[\\d.]+/g).map(Number); return (0.299*m[0] + 0.587*m[1] + 0.114*m[2]) / 255; };
          const h = document.querySelector('main h1');
          if (!h) return 1;
          const fondo = getComputedStyle(document.body).backgroundColor;
          return Math.abs(luz(getComputedStyle(h).color) - luz(fondo));
        }""")
        assert contraste > 0.3, (ruta, contraste)


# ---------------- Flujos completos ----------------

@caso("E2E-06")
def test_paciente_con_plan_de_principio_a_fin(fab, api, abrir):
    fab.caja()
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=40)
    nombre = f"Flujo{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)["id"]
    t = fab.tratamiento(500, nombre=f"Corona {nombre}", categoria="REHABILITACION_PROTESIS")
    plan = doc.api.post("/tratamientos/planes", {"paciente_id": paciente, "titulo": "Plan"}).json()["id"]
    item = doc.api.post("/tratamientos/items", {"plan_id": plan, "tratamiento_id": t["id"], "costo_acordado": 500, "pieza_fdi": 16}).json()
    assert doc.api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    assert fab.saldo(paciente) == 500
    dia = dia_libre()
    cita = fab.cita(paciente, dia, doctor=doc.doctor_id, item_plan_id=item["id"], tratamiento_id=t["id"]).json()
    url = f"/citas/{cita['id']}/sillon"
    for estado in ("EN_ESPERA", "EN_SILLON", "FINALIZADA"):
        assert doc.api.patch(url, {"estado": estado}).ok
    visita = api.get("/visitas/", paciente_id=paciente).json()[0]
    assert "Pieza 16" in visita["procedimiento_realizado"]
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    gaveta = fab.gaveta()
    rec = fab.usuario("RECEPCION")
    p = abrir(rec.alias, rec.clave, ruta="cobranzas")
    p.wait_for_timeout(400)
    p.get_by_role("region", name="Cobros de citas pendientes").get_by_role("button", name=nombre).click()
    p.wait_for_timeout(400)
    p.locator("#cobro-cita-medio").select_option("EFECTIVO")
    assert p.locator("#cobro-cita-doctor").input_value() == doc.doctor_id, "Propone al doctor de la cita"
    p.get_by_role("button", name="Confirmar pago").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(600)
    assert api.get(f"/cobros-cita/{cuenta['id']}").json()["estado"] == "PAGADO"
    assert fab.saldo(paciente) == 0 and fab.gaveta() == gaveta + 500
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == 200
    assert api.get("/reportes/tratamientos-demanda", limit=1000, fecha_desde=f"{dia}T00:00:00Z", fecha_hasta=f"{dia}T23:59:59Z").json()["ranking_tratamientos"][0]["tratamiento_id"] == t["id"]

    pago = api.get(f"/pacientes/{paciente}/saldo").json()["pagos"][0]
    assert api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error de cobro"}).ok
    assert fab.saldo(paciente) == 500 and fab.gaveta() == gaveta
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == 0
    assert api.get(f"/cobros-cita/{cuenta['id']}").json()["estado"] == "PENDIENTE"
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "doctor_comision_id": doc.doctor_id}).ok
    assert fab.saldo(paciente) == 0


@caso("E2E-02", "E2E-05")
def test_consulta_simple_y_reemplazo(fab, api):
    paciente = fab.paciente()["id"]
    dia = dia_libre()
    primera = fab.cita(paciente, dia).json()
    assert api.delete(f"/citas/{primera['id']}").status == 204
    otro = fab.paciente()["id"]
    segunda = fab.cita(otro, dia).json()
    assert api.put(f"/citas/{segunda['id']}", {"estado": "FINALIZADA"}).ok
    assert api.get("/visitas/", paciente_id=otro).json()
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == segunda["id"])
    linea = cuenta["lineas"][0]
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "lineas": [{"id": linea["id"], "concepto": "Consulta", "monto": 50}]}).ok
    assert fab.saldo(otro) == 0
    assert api.get("/citas/", paciente_id=paciente).json()[0]["estado"] == "CANCELADA"


@caso("E2E-07")
def test_dia_de_caja(fab, api):
    fab.cerrar_caja()
    assert api.post("/caja/abrir", {"monto_inicial_fondo": 1000}).status == 201
    p = fab.paciente()["id"]
    for monto, metodo in ((200, "EFECTIVO"), (100, "TARJETA_DEBITO"), (50, "TARJETA_CREDITO"), (75, "TRANSFERENCIA")):
        fab.cobro_directo(p, monto, metodo)
    assert api.post("/caja/egresos", {"categoria": "COMPRA_INSUMOS", "monto": 30, "concepto_motivo": "x"}).ok
    u = fab.usuario()
    assert api.post("/empleados/pagos", {"usuario_empleado_id": u.id, "tipo_pago": "ADELANTO", "monto_neto_pagado": 20, "metodo_pago": "EFECTIVO_CAJA"}).ok
    estado = api.get("/caja/estado").json()
    assert estado["saldo_en_gaveta"] == 1150
    cierre = api.post("/caja/cerrar", {"total_efectivo_contado": 1150}).json()
    assert float(cierre["diferencia_descuadre"]) == 0
    assert estado["ingresos_otros_medios"] == {"tarjeta_debito": 100, "tarjeta_credito": 50, "transferencia": 75}
    assert sum(m["monto"] for m in estado["movimientos"] if m["tipo"] == "INGRESO") == 425
    fab.caja()


@caso("E2E-09")
def test_turno_con_olvido(fab, api):
    u = fab.usuario()
    assert u.api.post("/auth/fichar", {"tipo_evento": "ENTRADA"}).ok
    assert u.api.post("/auth/fichar", {"tipo_evento": "INICIO_DESCANSO"}).ok
    assert u.api.post("/auth/fichar", {"tipo_evento": "FIN_DESCANSO"}).ok
    sql(f"update registro_asistencia set fecha_hora = fecha_hora - interval '1 day' where usuario_id = '{u.id}'")
    assert u.api.get("/auth/fichaje/estado").json()["jornada_sin_salida"]
    ultimo = api.get("/personal/asistencia", usuario_id=u.id).json()[0]
    from datetime import datetime
    salida = datetime.fromisoformat(ultimo["fecha_hora"]) + timedelta(minutes=1)
    assert api.post("/personal/asistencia/correcciones", {"usuario_id": u.id, "tipo_evento": "SALIDA", "fecha_hora": salida.isoformat(), "motivo": "Olvido"}).ok
    assert u.api.get("/auth/fichaje/estado").json()["jornada_sin_salida"] is None


# Sin caso propio: comprobación adicional
def test_protesis_con_pago(fab, api):
    fab.caja()
    p = fab.paciente()["id"]
    orden = api.post("/protesis/", {"paciente_id": p, "doctor_id": fab.doctor, "laboratorio_nombre": "Lab", "tipo_trabajo": "CORONA_ZIRCONIO", "costo_laboratorio": 80}).json()
    for estado in ("EN_LABORATORIO", "RECIBIDO_EN_CLINICA", "PRUEBA_EN_BOCA", "INSTALADO_FINALIZADO"):
        assert api.put(f"/protesis/{orden['id']}", {"estado": estado}).ok
    gaveta = fab.gaveta()
    assert api.post("/caja/egresos", {"categoria": "PAGO_LABORATORIO_PROTESIS", "monto": 80, "concepto_motivo": "Lab"}).ok
    assert fab.gaveta() == gaveta - 80
