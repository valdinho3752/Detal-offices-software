"""Casos que requieren comprobar detalles concretos en pantalla: fechas, filtros, volumen y aspecto."""
import base64
import re
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from apoyo import BASE, CLAVE_ADMIN, ZONA, ahora_clinica, desborde_de_main, dia_libre, sql
from test_ui_flujos import abrir_odontograma, caras, elegir_pieza, hallazgos, pulsar

caso = pytest.mark.caso
RUTAS = ["", "pacientes", "odontograma", "citas", "asistencia", "evolucion", "radiografias", "protesis", "caja", "cobranzas", "nomina", "auditoria", "reportes", "tratamientos", "sillones", "configuracion", "usuarios"]


@pytest.fixture(autouse=True)
def _caja_abierta(fab):
    fab.caja()


def instante(dia, hora):
    """La hora de la clínica, como la escribe una persona en el formulario."""
    return datetime.fromisoformat(f"{dia}T{hora}:00").replace(tzinfo=ZoneInfo(ZONA)).isoformat()


def cita_local(api, fab, paciente_id, dia, inicio, fin, doctor=None, box=1, **extra):
    return api.post("/citas/", {
        "paciente_id": paciente_id, "doctor_id": doctor or fab.usuario("DOCTOR").doctor_id, "motivo_consulta": "Control QA",
        "fecha_inicio_programada": instante(dia, inicio), "fecha_fin_programada": instante(fin[0], fin[1]) if isinstance(fin, tuple) else instante(dia, fin),
        "notas_adicionales": f"Box {box}", **extra,
    })


@pytest.fixture
def sillon(api):
    creados = []

    def _crear():
        creados.append(api.post("/sillones/", {"nombre": f"QA{uuid4().hex[:6]}"}).json())
        return creados[-1]["numero"]

    yield _crear
    for s in creados:
        api.delete(f"/sillones/{s['id']}")


def vista_mensual(p):
    p.get_by_role("button", name="Vista Mensual").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)


def celda_del_dia(p, dia_numero):
    """La celda del mes en curso: las de otros meses se ven atenuadas."""
    return p.locator('[title^="Click para seleccionar día"]:not(.opacity-40)').filter(has=p.locator(f'span:text-is("{dia_numero}")')).first


# ---------------- Sesión y usuarios ----------------

@caso("ACC-20")
def test_misma_cuenta_en_dos_equipos(fab, abrir):
    u = fab.usuario()
    uno = abrir(u.alias, u.clave)
    dos = abrir(u.alias, u.clave)
    for pagina in (uno, dos):
        pagina.goto(f"{BASE}/pacientes")
        pagina.wait_for_load_state("networkidle")
        assert "/login" not in pagina.url
    assert u.api.post("/auth/cambiar-contrasena", {"actual": u.clave, "nueva": "OtraClave1234!"}).ok
    uno.goto(f"{BASE}/pacientes")
    uno.wait_for_url(f"{BASE}/login")


@caso("USU-26")
def test_doctor_desactivado_con_citas(fab, api, como_admin, sillon):
    doc = fab.usuario("DOCTOR", nombre="Baja", apellido=f"D{uuid4().hex[:5]}")
    reemplazo = fab.usuario("DOCTOR")
    paciente = fab.paciente(nombres=f"Reasigna{uuid4().hex[:6]}")
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    cita = cita_local(api, fab, paciente["id"], hoy, "12:00", "12:30", doctor=doc.doctor_id, box=sillon()).json()
    assert api.put(f"/usuarios/{doc.id}", {"activo": False}).ok
    p = como_admin("citas")
    p.wait_for_selector("table")
    assert paciente["nombres"].lower() in p.locator("tbody").inner_text().lower(), "Sus citas siguen visibles"
    assert api.put(f"/citas/{cita['id']}", {"doctor_id": reemplazo.doctor_id}).ok, "Se puede reasignar"
    assert api.get("/citas/", paciente_id=paciente["id"]).json()[0]["doctor_id"] == reemplazo.doctor_id
    # Tras reasignarlas, el doctor desactivado ya no se ofrece para citas nuevas
    assert doc.doctor_id not in {d["id"] for d in api.get("/usuarios/doctores/lista").json()}
    p.reload()
    p.wait_for_load_state("networkidle")
    assert api.get("/citas/", paciente_id=paciente["id"]).json()[0]["doctor"]["nombre_completo"]


# ---------------- Pacientes ----------------

@caso("PAC-09")
def test_caracteres_especiales(fab, como_admin):
    nombre = f"José Ñandú 😀 O'Brien-{uuid4().hex[:4]}"
    paciente = fab.paciente(nombres=nombre)
    assert paciente["nombres"] == nombre
    p = como_admin("pacientes")
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(nombre[-8:])
    p.wait_for_timeout(600)
    assert nombre in p.inner_text("main")


@caso("PAC-23")
def test_listado_con_muchos_pacientes(fab, api, como_admin, sillon):
    marca = uuid4().hex[:6]
    sql(
        "insert into pacientes (nombres, apellidos, tipo_documento, numero_documento, genero, fecha_nacimiento, telefono) "
        f"select 'Masivo', 'Lista{marca}' || g, 'CI', 'M{marca}' || g, 'OTRO', '1990-01-01', '70000000' from generate_series(1, 150) g"
    )
    ultimo = fab.paciente(nombres=f"Ultimo{marca}", apellidos="ZZZZ")
    p = como_admin("pacientes")
    inicio = datetime.now()
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(f"Ultimo{marca}")
    p.get_by_text(f"Ultimo{marca}").first.wait_for(timeout=5000)
    assert (datetime.now() - inicio).total_seconds() < 3
    assert ultimo["id"]
    # Encuentra por documento a alguien que no cabe en la primera página
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(f"M{marca}149")
    p.get_by_text(f"Lista{marca}149").first.wait_for(timeout=5000)

    # Quien no cabe en la primera página también se atiende en las demás pantallas
    nombre = f"Ultimo{marca} ZZZZ"
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    assert cita_local(api, fab, ultimo["id"], hoy, "11:00", "11:30", box=sillon()).status == 201
    p.goto(f"{BASE}/citas")
    p.wait_for_selector("table")
    p.wait_for_load_state("networkidle")
    assert f"ultimo{marca}" in p.locator("tbody").inner_text().lower(), "La agenda muestra su nombre"
    p.get_by_role("button", name="Nueva Cita").click()
    f = p.locator("form").last
    f.get_by_placeholder("Buscar paciente por nombre o CI...").fill(nombre)
    f.get_by_text(nombre).first.click()
    f.get_by_title("Cambiar o deseleccionar paciente").wait_for(timeout=3000)  # Se puede elegir buscando su nombre completo
    for ruta in ("cobranzas", "evolucion", "radiografias", "odontograma"):
        p.goto(f"{BASE}/{ruta}?paciente_id={ultimo['id']}")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(450)
        assert nombre in p.inner_text("main"), f"{ruta} abre su ficha"


# ---------------- Odontograma ----------------

@caso("ODO-08")
def test_caras_mesiales_hacia_la_linea_media(fab, como_admin):
    paciente = fab.paciente()
    p = como_admin(f"odontograma?paciente_id={paciente['id']}")
    p.wait_for_selector('[title^="#"]')
    p.wait_for_timeout(400)
    medidas = p.evaluate("""() => {
      const salida = {};
      const dientes = [...document.querySelectorAll('[title^="#"]')];
      const centro = (e) => { const r = e.getBoundingClientRect(); return r.left + r.width / 2; };
      const de = (n) => dientes.find((d) => d.title.startsWith('#' + n + ' '));
      for (const n of [11, 12, 16, 21, 22, 26, 31, 32, 36, 41, 42, 46]) {
        const d = de(n);
        const m = [...d.querySelectorAll('polygon')].find((x) => x.querySelector('title')?.textContent.startsWith('Mesial'));
        const o = [...d.querySelectorAll('polygon')].find((x) => x.querySelector('title')?.textContent === 'Distal');
        salida[n] = { mesial: centro(m), distal: centro(o) };
      }
      return salida;
    }""")
    for pieza, m in medidas.items():
        izquierda = int(pieza) // 10 in (1, 4)
        # Los cuadrantes 1 y 4 están a la izquierda en pantalla: su lado mesial mira a la derecha
        assert (m["mesial"] > m["distal"]) == izquierda, (pieza, m)


@caso("ODO-12", "ODO-26")
def test_tabla_de_ingreso(fab, abrir):
    paciente = fab.paciente()
    doc = fab.usuario("DOCTOR")
    p = abrir_odontograma(abrir, doc, paciente)
    elegir_pieza(p, 12)
    p.get_by_role("button", name="Diagnóstico y evaluación inicial").first.click()
    caras(p).first.click()
    pulsar(p, "Guardar Diagnóstico Inicial")
    elegir_pieza(p, 22)
    p.get_by_role("button", name="Plan de tratamiento").first.click()
    caras(p).first.click()
    pulsar(p, "Marcar Cara Activa")
    assert hallazgos(paciente["id"], 12)
    pulsar(p, "Ver Ambos Espacios")
    texto = p.inner_text("main")
    assert "Estado de Ingreso Inicial" in texto, "Muestra el estado de ingreso"
    assert re.search("Tratamientos? a Realizar|Presupuesto|Plan de Tratamiento", texto, re.I), "Y los tratamientos a realizar"
    pinta = p.evaluate("""() => [...document.querySelector('[title^="#12 "]').querySelectorAll('polygon')].map((x) => x.getAttribute('fill')).join()""")
    p.get_by_title("Eliminar registro de ingreso").first.click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    assert hallazgos(paciente["id"], 12) == [], "Desaparece de la base"
    assert p.get_by_title("Eliminar registro de ingreso").count() == 0, "Desaparece de la tabla"
    despues = p.evaluate("""() => [...document.querySelector('[title^="#12 "]').querySelectorAll('polygon')].map((x) => x.getAttribute('fill')).join()""")
    assert despues != pinta, "Y del gráfico"


@caso("ODO-34")
@pytest.mark.parametrize("tema", ["light", "dark"])
def test_colores_del_odontograma(fab, abrir, tema):
    paciente = fab.paciente()
    doc = fab.usuario("DOCTOR")
    p = abrir(doc.alias, doc.clave, ruta=f"odontograma?paciente_id={paciente['id']}", tema=tema)
    p.wait_for_selector('[title^="#"]')
    p.wait_for_timeout(400)
    for pieza, boton in ((11, "Plan de tratamiento"), (21, "Alta clínica / Control posterior"), (31, "Diagnóstico y evaluación inicial")):
        elegir_pieza(p, pieza)
        p.get_by_role("button", name=boton).first.click()
        caras(p).first.click()
        pulsar(p, "Guardar Diagnóstico Inicial" if pieza == 31 else "Marcar Cara Activa")
    colores = p.evaluate("""() => {
      const sin = {};
      for (const n of [11, 21, 31, 41]) {
        const fills = [...document.querySelector('[title^="#' + n + ' "]').querySelectorAll('polygon')].map((x) => x.getAttribute('fill'));
        sin[n] = [...new Set(fills)];
      }
      return sin;
    }""")
    p.screenshot(path=str(_captura(f"odontograma_{tema}")), full_page=True)
    vacio = set(colores["41"])
    marcados = {n: set(colores[n]) - vacio for n in ("11", "21", "31")}
    assert all(marcados.values()), colores
    assert len(set.union(*marcados.values())) == 3, f"Cada estado tiene su propio color: {marcados}"


def _captura(nombre):
    from conftest import CAPTURAS
    return CAPTURAS / f"revision_{nombre}.png"


# ---------------- Catálogo ----------------

@caso("TRA-11")
def test_filtros_del_catalogo(fab, como_admin):
    marca = uuid4().hex[:6]
    uno = fab.tratamiento(10, nombre=f"Filtro {marca} A", categoria="ENDODONCIA")
    dos = fab.tratamiento(10, nombre=f"Filtro {marca} B", categoria="ORTODONCIA")
    p = como_admin("tratamientos")
    p.get_by_placeholder("Buscar por nombre o código...").fill(f"Filtro {marca}")
    p.wait_for_timeout(200)
    texto = p.inner_text("main")
    assert uno["nombre"] in texto and dos["nombre"] in texto
    p.get_by_label("Filtrar por categoría").select_option("ENDODONCIA")
    p.wait_for_timeout(200)
    texto = p.inner_text("main")
    assert uno["nombre"] in texto and dos["nombre"] not in texto
    p.get_by_placeholder("Buscar por nombre o código...").fill(dos["codigo"])
    p.wait_for_timeout(200)
    assert dos["nombre"] not in p.inner_text("main"), "Los dos filtros se combinan"


# ---------------- Agenda ----------------

@caso("AGE-26")
def test_filtros_de_agenda(fab, api, como_admin, sillon):
    marca = uuid4().hex[:6]
    uno = fab.usuario("DOCTOR", nombre="Filtro", apellido=f"Uno{marca}")
    dos = fab.usuario("DOCTOR", nombre="Filtro", apellido=f"Dos{marca}")
    endo = fab.tratamiento(10, categoria="ENDODONCIA")
    orto = fab.tratamiento(10, categoria="ORTODONCIA")
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    pa = fab.paciente(nombres=f"Endo{marca}")
    pb = fab.paciente(nombres=f"Orto{marca}")
    numero = sillon()
    assert cita_local(api, fab, pa["id"], hoy, "13:00", "13:30", doctor=uno.doctor_id, box=numero, tratamiento_id=endo["id"]).status == 201
    assert cita_local(api, fab, pb["id"], hoy, "13:30", "14:00", doctor=dos.doctor_id, box=numero, tratamiento_id=orto["id"]).status == 201
    p = como_admin("citas")
    p.wait_for_selector("table")
    cuerpo = lambda: p.locator("tbody").inner_text().lower()
    assert pa["nombres"].lower() in cuerpo() and pb["nombres"].lower() in cuerpo()
    filtro_especialidad, filtro_doctor = p.locator("main select").nth(0), p.locator("main select").nth(1)
    filtro_doctor.select_option(uno.doctor_id)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(350)
    assert pa["nombres"].lower() in cuerpo() and pb["nombres"].lower() not in cuerpo()
    filtro_doctor.select_option("")
    filtro_especialidad.select_option("ORTODONCIA")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(350)
    assert pb["nombres"].lower() in cuerpo() and pa["nombres"].lower() not in cuerpo()


@caso("AGE-33")
def test_agenda_con_muchos_sillones(api, como_admin):
    creados = [api.post("/sillones/", {"nombre": f"Extra{uuid4().hex[:4]}"}).json() for _ in range(6)]
    try:
        p = como_admin("citas", ancho=1280)
        p.wait_for_selector("table")
        assert p.locator("thead th").count() - 1 >= 6
        assert desborde_de_main(p) <= 0, "La página no se rompe"
        assert p.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        tabla = p.evaluate("""() => {
          const t = document.querySelector('main table'); let e = t.parentElement;
          while (e && getComputedStyle(e).overflowX === 'visible') e = e.parentElement;
          return { tabla: t.getBoundingClientRect().width, contenedor: e.clientWidth, desplaza: e.scrollWidth > e.clientWidth, tieneScroll: ['auto', 'scroll'].includes(getComputedStyle(e).overflowX) };
        }""")
        assert tabla["tieneScroll"] and tabla["tabla"] >= tabla["contenedor"] - 1, tabla
    finally:
        for s in creados:
            api.delete(f"/sillones/{s['id']}")


@caso("AGE-37")
def test_cita_que_cruza_la_medianoche(fab, api, como_admin, sillon):
    ahora = ahora_clinica()
    # Un día dentro del mes visible, para no depender de la navegación
    dia = ahora.replace(day=10)
    siguiente = dia + timedelta(days=1)
    nombre = f"Medianoche{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    res = cita_local(api, fab, paciente["id"], dia.strftime("%Y-%m-%d"), "23:30", (siguiente.strftime("%Y-%m-%d"), "00:30"), box=sillon())
    assert res.status == 201, res.text
    cita = res.json()
    p = como_admin("citas")
    vista_mensual(p)
    assert nombre[:10] in celda_del_dia(p, 10).inner_text(), "Aparece el día en que empieza"
    assert nombre[:10] not in celda_del_dia(p, 11).inner_text(), "Y no el siguiente"
    # El listado y el reporte la cuentan el día en que empieza, y no el siguiente
    del_dia = {"fecha_desde": instante(dia.strftime("%Y-%m-%d"), "00:00"), "fecha_hasta": instante(dia.strftime("%Y-%m-%d"), "23:59")}
    del_siguiente = {"fecha_desde": instante(siguiente.strftime("%Y-%m-%d"), "00:00"), "fecha_hasta": instante(siguiente.strftime("%Y-%m-%d"), "23:59")}
    assert [c["id"] for c in api.get("/citas/", paciente_id=paciente["id"], **del_dia).json()] == [cita["id"]]
    assert api.get("/citas/", paciente_id=paciente["id"], **del_siguiente).json() == []
    total = lambda periodo: sum(d["total_citas"] for d in api.get("/reportes/productividad-doctores", doctor_id=cita["doctor_id"], **periodo).json()["doctores"])
    assert total(del_dia) == 1 and total(del_siguiente) == 0


@caso("CAL-02")
def test_meses_de_distinta_duracion(como_admin):
    p = como_admin("citas")
    vista_mensual(p)
    actual = ahora_clinica().replace(day=1)
    vistos = set()
    for _ in range(13):
        dias = p.locator('[title^="Click para seleccionar día"]:not(.opacity-40)')
        numeros = [int(x) for x in dias.locator("span").all_inner_texts() if x.strip().isdigit() and int(x) <= 31]
        unicos = sorted({n for n in numeros})
        # La duración real del mes visible
        siguiente = (actual.replace(day=28) + timedelta(days=4)).replace(day=1)
        largo = (siguiente - timedelta(days=1)).day
        assert unicos[-1] == largo and unicos[0] == 1, (actual.strftime("%Y-%m"), unicos[-3:])
        # Cada día en la columna de su día de la semana (lunes = primera)
        primera = dias.first.evaluate("e => [...e.parentElement.children].indexOf(e)")
        assert primera == actual.replace(day=1).weekday(), actual.strftime("%Y-%m")
        vistos.add(largo)
        actual = siguiente
        p.get_by_title("Mes Siguiente").click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(120)
    assert {30, 31} <= vistos and (28 in vistos or 29 in vistos), vistos


@caso("CAL-04", "CAL-07", "CAL-10")
def test_calendario_dia_actual_y_varias_citas(fab, api, como_admin, sillon):
    hoy = ahora_clinica()
    # Otro día del mes: hoy puede tener citas de otras pruebas
    dia = hoy.replace(day=20 if hoy.day != 20 else 21)
    texto_dia = dia.strftime("%Y-%m-%d")
    marca = uuid4().hex[:5]
    numero = sillon()
    # Sin otras citas de otras pruebas ese día
    sql(f"delete from citas where fecha_inicio_programada::date between '{texto_dia}'::date - 1 and '{texto_dia}'::date + 1")
    for indice in range(5):
        hora = f"{8 + indice:02d}:00"
        fin = f"{8 + indice:02d}:30"
        assert cita_local(api, fab, fab.paciente(nombres=f"Dia{marca}{indice}")["id"], texto_dia, hora, fin, box=numero).status == 201
    noche = fab.paciente(nombres=f"Noche{marca}")
    # A las 23:30 de la clínica ya es el día siguiente en UTC
    assert cita_local(api, fab, noche["id"], texto_dia, "23:30", "23:55", box=numero).status == 201
    p = como_admin("citas")
    vista_mensual(p)
    celda = celda_del_dia(p, dia.day)
    assert "+3 más" in celda.inner_text(), "Muestra 3 y la cantidad restante"
    assert celda.locator('[title^="Click para editar"]').count() == 3
    assert celda.locator("span").nth(1).inner_text() == "6"

    numero_hoy = celda_del_dia(p, hoy.day).locator("span").first
    assert "bg-teal-500" in numero_hoy.get_attribute("class"), "El día actual está resaltado"
    assert p.locator('[title^="Click para seleccionar día"] span.bg-teal-500').count() == 1, "Y solo ese"

    # La cita de las 23:30 pertenece a su día local, en la matriz de ese día y no en el siguiente
    celda.click()
    p.wait_for_load_state("networkidle")
    p.get_by_role("button", name=re.compile("Matriz|Vista.*Sillones")).first.click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert texto_dia in p.inner_text("main"), "Abre el día elegido"
    p.get_by_title("Día Siguiente").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert noche["nombres"].lower() not in p.locator("tbody").inner_text().lower(), "Al día siguiente no aparece"
    vista_mensual(p)
    p.get_by_role("button", name="Hoy").click()
    p.wait_for_timeout(300)
    # Con pocas citas el día debe listarla: se comprueba con un día con una sola cita de noche
    otro = hoy.replace(day=22 if hoy.day != 22 else 23)
    tarde = fab.paciente(nombres=f"Tarde{marca}")
    assert cita_local(api, fab, tarde["id"], otro.strftime("%Y-%m-%d"), "23:30", "23:55", box=numero).status == 201
    # La noche del último día del mes ya es el mes siguiente en UTC
    ultimo = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    fin_de_mes = fab.paciente(nombres=f"Fin{marca}")
    assert cita_local(api, fab, fin_de_mes["id"], ultimo.strftime("%Y-%m-%d"), "23:30", "23:55", box=numero).status == 201
    p.reload()
    p.wait_for_load_state("networkidle")
    vista_mensual(p)
    assert f"Tarde{marca}"[:10] in celda_del_dia(p, otro.day).inner_text(), "Aparece en su día local"
    assert f"Tarde{marca}"[:10] not in celda_del_dia(p, otro.day + 1).inner_text(), "No en el día UTC"
    assert f"Fin{marca}"[:8] in celda_del_dia(p, ultimo.day).inner_text(), "Tampoco se pierde a fin de mes"


# ---------------- Evolución ----------------

def _paciente_con_diagnostico(fab, api, pieza=26):
    pid = fab.paciente()["id"]
    odo = api.post("/odontogramas/", {"paciente_id": pid, "doctor_id": fab.doctor})
    assert odo.status == 201, odo.text
    return pid, odo.json()


@caso("EVO-02")
def test_evolucion_con_diagnostico_del_odontograma(fab, api, abrir):
    paciente = fab.paciente()
    pid = paciente["id"]
    doc = fab.usuario("DOCTOR")
    p = abrir_odontograma(abrir, doc, paciente)
    elegir_pieza(p, 26)
    caras(p).first.click()
    pulsar(p, "Marcar Cara Activa")
    fila = hallazgos(pid, 26)
    assert fila and fila[0][2] == "REQUERIDO_PATOLOGIA"
    superficie = fila[0][1]
    plan = fab.plan(pid, doctor=doc.doctor_id)
    item = fab.item(plan, fab.tratamiento(50)["id"], 50, pieza_fdi=26, superficie=superficie)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    cita = fab.cita(pid, doctor=doc.doctor_id, item_plan_id=item["id"]).json()
    assert doc.api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    visita = api.get("/visitas/", paciente_id=pid).json()[0]
    assert visita["generada_automaticamente"] and "pieza 26" in visita["diagnostico"], visita["diagnostico"]
    q = abrir(doc.alias, doc.clave, ruta=f"evolucion?paciente_id={pid}")
    q.get_by_text("Diagnóstico (tomado del odontograma):").first.wait_for()
    assert visita["diagnostico"] in q.inner_text("main")


@caso("EVO-23")
def test_receta_e_indicaciones(fab, api, abrir):
    doc = fab.usuario("DOCTOR")
    pid = fab.paciente()["id"]
    res = doc.api.post("/visitas/", {
        "paciente_id": pid, "doctor_id": doc.doctor_id, "motivo_consulta": "Dolor", "observaciones_clinicas": "Observado", "diagnostico": "Pulpitis",
        "procedimiento_realizado": "Apertura", "receta_medicamentos": "Ibuprofeno 400 mg", "indicaciones_postoperatorias": "Dieta blanda",
    })
    assert res.status == 201, res.text
    p = abrir(doc.alias, doc.clave, ruta=f"evolucion?paciente_id={pid}")
    p.add_init_script("window.__imprimio = 0; window.print = () => { window.__imprimio += 1; }")
    p.reload()
    p.wait_for_load_state("networkidle")
    p.get_by_text("Ibuprofeno 400 mg").first.wait_for()
    assert "Dieta blanda" in p.inner_text("main")
    p.get_by_role("button", name="Imprimir Receta").first.click()
    assert p.evaluate("window.__imprimio") == 1


# ---------------- Radiografías ----------------

PNG_1X1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@caso("RAD-05", "RAD-08")
def test_visor_e_imagen_rota(fab, api, como_admin):
    pid = fab.paciente()["id"]
    rota = api.post("/radiografias/", {"paciente_id": pid, "tipo_estudio": "PERIAPICAL", "titulo": "Imagen eliminada", "archivo_url": f"{BASE}/no-existe-{uuid4().hex}.png", "informe_diagnostico": "Sin lesión", "fecha_toma": "2026-02-03"})
    assert rota.status == 201, rota.text
    p = como_admin(f"radiografias?paciente_id={pid}")
    p.get_by_text("Imagen eliminada").first.wait_for()
    p.wait_for_timeout(600)
    assert "No se pudo cargar la imagen" in p.inner_text("main"), "Avisa en la tarjeta"
    p.get_by_test_id("vista-radiografia").first.click()
    p.wait_for_timeout(500)
    cuerpo = p.inner_text("body")
    assert "Fecha: 2026-02-03" in cuerpo and "Sin lesión" in cuerpo, "Muestra la fecha y el informe"
    assert cuerpo.count("No se pudo cargar la imagen") >= 2, "Y también en el visor, sin romper la pantalla"
    p.get_by_role("button", name="Cerrar", exact=True).click()

    enlace = "https://imagenes.ejemplo.test/correcta.png"
    p.route(enlace, lambda r: r.fulfill(status=200, content_type="image/png", body=base64.b64decode(PNG_1X1.split(",")[1])))
    buena = api.post("/radiografias/", {"paciente_id": pid, "tipo_estudio": "PANORAMICA", "titulo": "Imagen correcta", "archivo_url": enlace, "informe_diagnostico": "Normal", "fecha_toma": "2026-03-04"})
    assert buena.status == 201, buena.text
    p.reload()
    p.wait_for_load_state("networkidle")
    p.get_by_text("Imagen correcta").first.wait_for()
    p.get_by_test_id("vista-radiografia").filter(has=p.locator('img[alt="Imagen correcta"]')).click()
    p.wait_for_timeout(400)
    imagen = p.locator('img[alt="Radiografía Dental"]')
    assert imagen.evaluate("e => e.naturalWidth > 0"), "Muestra la imagen"
    assert "Fecha: 2026-03-04" in p.inner_text("body") and "Normal" in p.inner_text("body")


# ---------------- Prótesis ----------------

@caso("PRO-04")
def test_fecha_de_envio_local_por_la_noche(fab, api, abrir):
    nombre = f"Noche{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    p = abrir("admin", CLAVE_ADMIN, ruta="protesis", reloj=noche)
    p.get_by_role("button", name=re.compile("Nueva Orden")).first.click()
    f = p.locator("form").last
    f.get_by_placeholder(re.compile("Buscar paciente")).fill(nombre)
    p.wait_for_timeout(400)
    f.get_by_text(nombre).first.click()
    f.locator("select").first.select_option(index=1)
    f.get_by_placeholder("ej. Lab Dental Cerámicas & Cía").fill(f"Lab{uuid4().hex[:6]}")
    f.get_by_placeholder("ej. Corona Zirconio, Incrustación E-max").fill("Corona")
    with p.expect_request(lambda q: q.method == "POST" and "/protesis" in q.url) as envio:
        f.locator('button[type="submit"]').click()
    assert envio.value.post_data_json["fecha_envio"] == noche.strftime("%Y-%m-%d"), "Usa la fecha local, no UTC"


# ---------------- Nómina ----------------

@caso("NOM-17")
def test_quincena_propone_la_mitad(fab, como_admin):
    rec = fab.usuario("RECEPCION", salario_base=3000)
    p = como_admin("nomina")
    p.get_by_label("Empleado").select_option(rec.id)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    p.get_by_role("button", name="Registrar Pago / Adelanto").click()
    d = p.get_by_role("dialog", name="Registrar pago")
    d.get_by_label("Tipo de pago").select_option("QUINCENA")
    assert "$1.500,00" in d.get_by_test_id("neto-sueldo").inner_text()


# ---------------- Panel ----------------

@caso("PAN-03", "PAN-06")
def test_citas_de_hoy_en_el_panel(fab, api, abrir, sillon):
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    hoy = noche.strftime("%Y-%m-%d")
    ayer = (noche - timedelta(days=1)).strftime("%Y-%m-%d")
    manana = (noche + timedelta(days=1)).strftime("%Y-%m-%d")
    marca = uuid4().hex[:5]
    doc = fab.usuario("DOCTOR")
    numero = sillon()
    # Una por la mañana y otra a última hora, que en UTC ya es el día siguiente
    temprano = fab.paciente(nombres=f"Temprano{marca}")
    tarde = fab.paciente(nombres=f"Ultima{marca}")
    previo = fab.paciente(nombres=f"Anoche{marca}")
    siguiente = fab.paciente(nombres=f"Manana{marca}")
    c1 = cita_local(api, fab, temprano["id"], hoy, "00:05", "00:10", doctor=doc.doctor_id, box=numero)
    c2 = cita_local(api, fab, tarde["id"], hoy, "23:30", "23:50", doctor=doc.doctor_id, box=numero)
    assert c1.status == 201 and c2.status == 201, (c1.text, c2.text)
    assert cita_local(api, fab, previo["id"], ayer, "23:30", "23:50", doctor=doc.doctor_id, box=numero).status == 201
    assert cita_local(api, fab, siguiente["id"], manana, "00:10", "00:20", doctor=doc.doctor_id, box=numero).status == 201
    # El Panel muestra las primeras cinco: se dejan solo las de esta prueba ese día
    otras = [c["id"] for c in api.get("/citas/", fecha_desde=instante(hoy, "00:00"), fecha_hasta=instante(hoy, "23:59")).json() if c["id"] not in (c1.json()["id"], c2.json()["id"])]
    if otras:
        sql("delete from citas where id in (" + ",".join(f"'{i}'" for i in otras) + ")")
    assert api.put(f"/citas/{c1.json()['id']}", {"estado": "EN_SILLON"}).ok

    p = abrir(reloj=noche)
    p.fill('input[type="text"]', "admin")
    p.fill('input[type="password"]', CLAVE_ADMIN)
    p.click('button[type="submit"]')
    p.wait_for_url(f"{BASE}/")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    texto = p.inner_text("main")
    assert temprano["nombres"] in texto and tarde["nombres"] in texto, "Incluye toda la jornada local"
    assert "00:05" in texto and "23:30" in texto, "Con su hora real"
    assert previo["nombres"] not in texto and siguiente["nombres"] not in texto, "Y solo ese día"

    tarjeta = p.locator("main").get_by_text("Citas para Hoy").locator("..")
    esperado = [c for c in api.get("/citas/", fecha_desde=instante(hoy, "00:00"), fecha_hasta=instante(hoy, "23:59")).json()]
    en_sillon = sum(1 for c in esperado if c["estado"] == "EN_SILLON")
    assert f"{en_sillon} actualmente en sillón" in tarjeta.inner_text()
    assert re.search(rf"\b{len(esperado)}\b", tarjeta.inner_text()), (tarjeta.inner_text(), len(esperado))

    # Avanzar una cita desde el Panel
    fila = p.locator("main div").filter(has_text=tarde["nombres"]).last.locator("xpath=ancestor::div[contains(@class,'justify-between')][1]")
    fila.get_by_role("button").first.click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert api.get("/citas/", paciente_id=tarde["id"]).json()[0]["estado"] == "EN_ESPERA"


@caso("PAN-05")
def test_finanzas_del_panel_coinciden_con_reportes(fab, api, como_admin):
    fab.cobro_directo(fab.paciente()["id"], 9321.55)
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": 1200.25, "concepto_motivo": "Panel"}).status in (200, 201)
    antiguo = fab.cobro_directo(fab.paciente()["id"], 55555.55)
    sql(f"update pagos set fecha_hora = '{(ahora_clinica().replace(day=1) - timedelta(days=5)).isoformat()}' where id = '{antiguo['id']}'")
    p = como_admin()
    p.wait_for_timeout(500)
    tarjeta = lambda titulo: p.locator("main").get_by_text(titulo, exact=True).locator("..").inner_text()
    ingresos, egresos = tarjeta("Ingresos del Mes"), tarjeta("Egresos del Mes")
    assert "55.555,55" not in p.inner_text("main"), "Solo del mes actual"
    numero = lambda t: re.search(r"\$[\d.,]+", t).group(0)
    margen = re.search(r"Margen del mes: (\$-?[\d.,]+|-\$[\d.,]+)", ingresos).group(1)
    p.goto(f"{BASE}/reportes")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    texto = p.inner_text("main")
    assert numero(ingresos) in texto and numero(egresos) in texto and margen in texto, (ingresos, egresos, margen)


# ---------------- Reportes ----------------

@caso("REP-03")
def test_semanas_en_reportes(abrir):
    # Miércoles 4 de noviembre de 2026
    reloj = datetime(2026, 11, 4, 22, 30, tzinfo=ZoneInfo(ZONA))
    p = abrir("admin", CLAVE_ADMIN, ruta="reportes", reloj=reloj)
    grupo = p.get_by_role("group", name="Periodo del reporte")
    rango = p.get_by_test_id("rango-reporte")
    grupo.get_by_role("button", name="Esta semana", exact=True).click()
    assert "2 nov 2026" in rango.inner_text() and "4 nov 2026" in rango.inner_text(), rango.inner_text()
    grupo.get_by_role("button", name="Semana pasada", exact=True).click()
    assert "26 oct 2026" in rango.inner_text() and "1 nov 2026" in rango.inner_text(), rango.inner_text()


@caso("REP-15")
def test_cambio_rapido_de_periodo(fab, como_admin):
    fab.cobro_directo(fab.paciente()["id"], 111.11)
    p = como_admin("reportes")
    p.wait_for_timeout(300)
    grupo = p.get_by_role("group", name="Periodo del reporte")

    # La primera respuesta tarda más: una respuesta vieja no debe pisar a la última elegida
    def demorar(ruta):
        if "1990" not in ruta.request.url and "fecha_desde" in ruta.request.url:
            p.wait_for_timeout(1500)
        ruta.continue_()

    p.route("**/reportes/resumen-financiero*", demorar)
    grupo.get_by_role("button", name="Personalizado", exact=True).click()
    fechas = p.locator('input[type="date"]')
    grupo.get_by_role("button", name="Hoy", exact=True).click()
    grupo.get_by_role("button", name="Este año", exact=True).click()
    grupo.get_by_role("button", name="Todo", exact=True).click()
    p.wait_for_timeout(4500)
    assert grupo.get_by_role("button", name="Todo", exact=True).get_attribute("aria-pressed") == "true"
    assert p.get_by_test_id("rango-reporte").inner_text() == "Todo el historial"
    total_todo = sql("select coalesce(sum(monto),0) from pagos where not anulado")
    entero = f"{int(float(total_todo)):,}".replace(",", ".")
    assert entero in p.inner_text("main"), "Se queda con los datos del último período elegido"
    assert fechas.count() == 0


@caso("REP-19")
def test_reporte_con_diez_doctores(fab, api, como_admin):
    marca = uuid4().hex[:4]
    pid = fab.paciente()["id"]
    for indice in range(10):
        doc = fab.usuario("DOCTOR", nombre=f"Maximiliano Bartolomé {indice}", apellido=f"Fernández de la Santísima Trinidad{marca}", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=10)
        fab.cobro_directo(pid, 10 + indice, doctor_comision_id=doc.doctor_id)
        assert fab.cita(pid, doctor=doc.doctor_id).status == 201
    p = como_admin("reportes", ancho=1366)
    p.get_by_role("group", name="Periodo del reporte").get_by_role("button", name="Todo", exact=True).click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(1500)
    assert desborde_de_main(p) <= 0
    assert p.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    imagenes = p.locator("section img")
    assert all(imagenes.nth(i).evaluate("e => e.naturalWidth > 0 && e.getBoundingClientRect().width <= e.parentElement.getBoundingClientRect().width + 1") for i in range(imagenes.count()))
    # Las filas de la tabla conservan el nombre completo o lo ofrecen sin cortar el valor
    assert f"Trinidad{marca}" in p.inner_text("main")
    p.locator("section").filter(has_text="Productividad").first.screenshot(path=str(_captura("reporte_diez_doctores")))


# ---------------- Auditoría ----------------

@caso("AUD-10")
def test_auditoria_con_muchos_registros(api, como_admin):
    sql(
        "insert into auditoria_logs (tabla_afectada, registro_id, accion, seccion_consultada, fecha_hora) "
        "select 'qa_masivo', gen_random_uuid(), 'UPDATE', 'QA', now() - (g || ' minutes')::interval from generate_series(1, 30000) g"
    )
    p = como_admin()
    inicio = datetime.now()
    p.goto(f"{BASE}/auditoria")
    p.locator("main table tbody tr").first.wait_for(timeout=5000)
    p.wait_for_load_state("networkidle")
    assert (datetime.now() - inicio).total_seconds() < 3
    assert p.locator("main table tbody tr").count() <= 500, "No intenta dibujar todo el historial"
    assert api.get("/auditoria/", tabla_afectada="qa_masivo").ok


# ---------------- Sillones ----------------

@caso("SIL-03")
def test_editar_sillon(api, como_admin):
    sillon = api.post("/sillones/", {"nombre": f"Editar{uuid4().hex[:4]}"}).json()
    nuevo = f"Renombrado{uuid4().hex[:4]}"
    try:
        p = como_admin("sillones")
        p.get_by_role("button", name=f"Editar {sillon['nombre']}").click()
        f = p.locator("form").last
        f.locator("input").first.fill(nuevo)
        f.get_by_label("Especialidad").fill("Cirugía QA")
        f.get_by_role("button", name="Guardar Cambios").click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(300)
        assert nuevo in p.inner_text("main")
        p.goto(f"{BASE}/citas")
        cabecera = p.locator("thead th").filter(has_text=nuevo)
        cabecera.wait_for()
        assert "cirugía qa" in cabecera.inner_text().lower()
    finally:
        api.delete(f"/sillones/{sillon['id']}")


# ---------------- Configuración ----------------

@caso("CFG-04")
def test_nombre_de_clinica_largo(api, como_admin):
    original = api.get("/configuracion/").json()["nombre_clinica"]
    largo = ("Clínica Odontológica Integral de Especialidades " * 3)[:120]
    try:
        assert api.put("/configuracion/", {"nombre_clinica": largo}).ok
        p = como_admin()
        titulo = p.locator("aside h1")
        medidas = titulo.evaluate("e => ({ancho: e.getBoundingClientRect().width, contenido: e.scrollWidth, alto: e.getBoundingClientRect().height, menu: e.closest('aside').getBoundingClientRect().width, derecha: e.getBoundingClientRect().right, borde: e.closest('aside').getBoundingClientRect().right})")
        assert medidas["derecha"] <= medidas["borde"], "No se sale del menú"
        assert medidas["alto"] < 30, "Se corta en una línea"
        assert titulo.get_attribute("title") == largo, "Se puede leer completo al pasar el cursor"
    finally:
        api.put("/configuracion/", {"nombre_clinica": original})


@caso("CFG-09")
def test_logo_no_cuadrado(api, como_admin, tmp_path):
    p = como_admin("configuracion")
    # Un PNG real de 400 x 100, generado por el navegador
    datos = p.evaluate("""() => { const c = document.createElement('canvas'); c.width = 400; c.height = 100; const x = c.getContext('2d'); x.fillStyle = '#0a7'; x.fillRect(0, 0, 400, 100); return c.toDataURL('image/png').split(',')[1]; }""")
    logo = tmp_path / "ancho.png"
    logo.write_bytes(base64.b64decode(datos))
    try:
        p.get_by_test_id("archivo-logo").set_input_files(str(logo))
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(500)
        imagen = p.locator("aside img").first
        assert imagen.evaluate("e => e.naturalWidth === 400 && getComputedStyle(e).objectFit === 'contain'"), "Mantiene su proporción"
    finally:
        api.delete("/configuracion/logo")


# ---------------- Aspecto en cada tema ----------------

MEDIR_CONTRASTE = """() => {
  const canales = (c) => { const m = c.match(/[\\d.]+/g); if (!m) return null; const n = m.map(Number); return { r: n[0], g: n[1], b: n[2], a: n.length > 3 ? n[3] : 1 }; };
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const sobre = (a, b) => ({ r: a.r * a.a + b.r * (1 - a.a), g: a.g * a.a + b.g * (1 - a.a), b: a.b * a.a + b.b * (1 - a.a), a: 1 });
  const fondo = (e) => {
    const capas = [];
    for (let x = e; x; x = x.parentElement) {
      const s = getComputedStyle(x);
      if (s.backgroundImage !== 'none') return null;
      const c = canales(s.backgroundColor);
      if (c && c.a > 0) { capas.push(c); if (c.a >= 1) break; }
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (const c of capas.reverse()) base = sobre(c, base);
    return base;
  };
  const malos = [];
  const raiz = document.querySelector('#root');
  const paseo = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
  const vistos = new Set();
  while (paseo.nextNode()) {
    const t = paseo.currentNode.textContent.trim();
    const e = paseo.currentNode.parentElement;
    if (!t || vistos.has(e) || ['OPTION', 'SCRIPT', 'STYLE', 'TITLE'].includes(e.tagName)) continue;
    vistos.add(e);
    const r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    let op = 1;
    // Un latido de animación no es el estado normal del texto
    for (let x = e; x; x = x.parentElement) if (!x.classList.contains('animate-pulse')) op *= parseFloat(getComputedStyle(x).opacity);
    if (op === 0 || e.closest(':disabled, [aria-disabled="true"]')) continue;
    const f = fondo(e);
    if (!f) continue;
    const c = canales(s.color);
    if (!c) continue;
    const real = sobre({ ...c, a: c.a * op }, f);
    const [a, b] = [lum(real), lum(f)].sort((x, y) => y - x);
    const razon = (a + 0.05) / (b + 0.05);
    // AA para texto normal es 4,5; aquí se rechaza lo que de verdad cuesta leer
    if (razon < 3) malos.push(`${t.slice(0, 40)} [${razon.toFixed(1)}] ${s.color} sobre rgb(${Math.round(f.r)},${Math.round(f.g)},${Math.round(f.b)})`);
  }
  return malos;
}"""


@caso("CFG-22", "CFG-23")
@pytest.mark.parametrize("tema", ["light", "dark"])
def test_todas_las_pantallas_se_leen(fab, api, como_admin, tema):
    """Mide el contraste de cada texto visible y deja una captura de cada pantalla para revisarla."""
    paciente = fab.paciente(nombres="Lectura", apellidos="Tema")
    fab.cita(paciente["id"], ahora_clinica().strftime("%Y-%m-%d"), "16:00", "16:30")
    fab.cobro_directo(paciente["id"], 25)
    problemas = {}
    p = como_admin(tema=tema)
    rutas = RUTAS + [f"odontograma?paciente_id={paciente['id']}", f"evolucion?paciente_id={paciente['id']}", f"radiografias?paciente_id={paciente['id']}"]
    for ruta in rutas:
        p.goto(f"{BASE}/{ruta}")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(350)
        malos = p.evaluate(MEDIR_CONTRASTE)
        if malos:
            problemas[ruta or "panel"] = malos[:6]
        nombre = re.sub(r"\W+", "_", ruta.split("?")[0] or "panel") + ("_paciente" if "?" in ruta else "")
        p.screenshot(path=str(_captura(f"{tema}_{nombre}")), full_page=True)
    assert not problemas, problemas


# ---------------- Decisiones de la clínica ----------------

@caso("SEG-09")
def test_sesion_se_cierra_por_inactividad(fab, api, abrir):
    u = fab.usuario()
    assert u.api.get("/auth/me").json()["minutos_inactividad"] == 5, "Cinco minutos por defecto"
    p = abrir(u.alias, u.clave, reloj_vivo=True, ruta="pacientes")
    p.clock.fast_forward(4 * 60 * 1000 + 35 * 1000)
    p.get_by_test_id("aviso-inactividad").wait_for(timeout=3000)
    p.mouse.move(300, 300)
    p.mouse.move(320, 320)
    p.get_by_test_id("aviso-inactividad").wait_for(state="hidden", timeout=3000)
    p.clock.fast_forward(4 * 60 * 1000 + 35 * 1000)
    assert "/login" not in p.url, "La actividad reinicia la cuenta"
    p.mouse.move(340, 340)
    p.clock.fast_forward(5 * 60 * 1000 + 2000)
    p.wait_for_url(f"{BASE}/login", timeout=5000)
    assert "por inactividad" in p.inner_text("body")
    assert p.evaluate("localStorage.getItem('token')") is None

    # Volver a abrir la página tras el tiempo límite tampoco reabre la sesión
    q = abrir(u.alias, u.clave, ruta="pacientes")
    q.evaluate("localStorage.setItem('ultima_actividad', String(Date.now() - 6 * 60 * 1000))")
    q.reload()
    q.wait_for_url(f"{BASE}/login", timeout=5000)


@caso("SEG-09")
def test_cada_usuario_elige_su_tiempo_de_sesion(fab, api, abrir):
    u = fab.usuario()
    otro = fab.usuario()
    p = abrir(u.alias, u.clave, reloj_vivo=True)
    p.get_by_role("button", name="Cierre de sesión por inactividad").click()
    d = p.get_by_role("dialog", name="Cierre de sesión por inactividad")
    assert d.get_by_role("status").count() == 0, "Con el tiempo recomendado no hay advertencia"
    d.get_by_label("Cerrar mi sesión tras").select_option("30")
    assert "propia responsabilidad" in d.get_by_role("status").inner_text()
    d.get_by_role("button", name="Guardar").click()
    d.wait_for(state="hidden")
    assert u.api.get("/auth/me").json()["minutos_inactividad"] == 30
    assert otro.api.get("/auth/me").json()["minutos_inactividad"] == 5, "Solo cambia el suyo"
    p.clock.fast_forward(6 * 60 * 1000)
    p.wait_for_timeout(500)
    assert "/login" not in p.url
    p.clock.fast_forward(25 * 60 * 1000)
    p.wait_for_url(f"{BASE}/login", timeout=5000)
    assert u.api.put("/auth/sesion", {"minutos_inactividad": 1}).status == 422, "Sin valores fuera de las opciones"
    assert u.api.put("/auth/sesion", {"minutos_inactividad": 100000}).status == 422
    cambios = [a for a in fab.auditoria("usuarios") if a["seccion_consultada"] == "TIEMPO_DE_SESION" and a["registro_id"] == u.id]
    assert cambios and cambios[0]["datos_nuevos"]["minutos_inactividad"] == 30, "Queda registrado quién asumió el riesgo"


@caso("OPE-17")
def test_equipo_con_otra_zona_horaria_ve_la_hora_de_la_clinica(fab, api, abrir, sillon):
    # A las 22:30 de la clínica ya es otro día en Tokio
    noche = ahora_clinica().replace(hour=22, minute=30, second=0, microsecond=0)
    hoy = noche.strftime("%Y-%m-%d")
    nombre = f"Zona{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    numero = sillon()
    assert cita_local(api, fab, paciente["id"], hoy, "21:15", "21:45", box=numero).status == 201
    primero_mes = noche.replace(day=1).strftime("%Y-%m-%d")
    peticiones = []
    p = abrir(reloj=noche, zona="Asia/Tokyo")
    p.on("request", lambda q: peticiones.append(q.url))
    p.fill('input[type="text"]', "admin")
    p.fill('input[type="password"]', CLAVE_ADMIN)
    p.click('button[type="submit"]')
    p.wait_for_url(f"{BASE}/")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert p.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone") == "Asia/Tokyo", "El equipo sí está en otra zona"
    fila = p.locator("main").get_by_text(nombre).first.locator("xpath=ancestor::div[contains(@class,'justify-between')][1]")
    assert "21:15" in fila.inner_text(), "El Panel muestra la hora de la clínica"
    desde_mes = instante(primero_mes, "00:00")
    utc = datetime.fromisoformat(desde_mes).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M")
    assert any("/reportes/resumen-financiero" in u and f"fecha_desde={utc}" in u.replace("%3A", ":") for u in peticiones), "El mes es el de la clínica"

    # La agenda abre el día de la clínica y una cita nueva queda a la hora escrita
    p.goto(f"{BASE}/citas")
    p.wait_for_selector("table")
    p.wait_for_load_state("networkidle")
    assert hoy in p.inner_text("main"), "Abre el día de la clínica, no el de Tokio"
    assert nombre.lower() in p.locator("tbody").inner_text().lower()
    p.get_by_role("button", name="Nueva Cita").click()
    otro_nombre = f"Nueva{uuid4().hex[:6]}"
    otro = fab.paciente(nombres=otro_nombre)
    f = p.locator("form").last
    assert f.locator('input[type="date"]').first.input_value() == hoy
    f.get_by_placeholder("Buscar paciente por nombre o CI...").fill(otro_nombre)
    f.get_by_text(otro_nombre).first.click()
    f.locator(f'select:has(option[value="{numero}"])').first.select_option(str(numero))
    f.locator('input[type="time"]').nth(0).fill("15:30")
    f.locator('input[type="time"]').nth(1).fill("16:00")
    f.get_by_placeholder("ej. Evaluación general, Extracción de tercer molar").fill("Zona horaria")
    f.get_by_role("button", name="Agendar Cita").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    creada = api.get("/citas/", paciente_id=otro["id"]).json()
    assert creada and datetime.fromisoformat(creada[0]["fecha_inicio_programada"]) == datetime.fromisoformat(instante(hoy, "15:30")), creada[:1]

    # Una corrección de marcaje y el historial también usan la hora de la clínica
    empleado = fab.usuario()
    p.goto(f"{BASE}/asistencia")
    p.wait_for_load_state("networkidle")
    corregida = api.post("/personal/asistencia/correcciones", {"usuario_id": empleado.id, "tipo_evento": "ENTRADA", "fecha_hora": instante(hoy, "08:10"), "motivo": "Zona"})
    assert corregida.status == 201, corregida.text
    p.reload()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert re.search(r"8:10|08:10", p.inner_text("main")), "Hora de la clínica en la bitácora"


@caso("PRO-16")
def test_pagar_laboratorio_queda_vinculado(fab, api, abrir, como_admin):
    fab.caja()
    laboratorio = f"Lab{uuid4().hex[:6]}"
    pid = fab.paciente()["id"]
    orden = api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "laboratorio_nombre": laboratorio, "tipo_trabajo": "CORONA_ZIRCONIO", "costo_laboratorio": 321.5}).json()
    gaveta = fab.gaveta()
    p = como_admin("protesis")
    fila = p.locator("main table tbody tr").filter(has_text=laboratorio)
    fila.wait_for()
    fila.get_by_role("button", name="Pagar Laboratorio").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    assert fab.gaveta() == gaveta - 321.5, "Descuenta la caja"
    actual = next(o for o in api.get("/protesis/").json() if o["id"] == orden["id"])
    assert actual["egreso_caja_id"], "Queda vinculada al egreso"
    assert sql(f"select categoria || '/' || monto from egresos_caja where id = '{actual['egreso_caja_id']}'") == "PAGO_LABORATORIO_PROTESIS/321.50"
    assert "Pagado" in fila.inner_text() and fila.get_by_role("button", name="Pagar Laboratorio").count() == 0
    assert api.post(f"/protesis/{orden['id']}/pagar-laboratorio", {}).status == 409, "No se paga dos veces"
    assert fab.gaveta() == gaveta - 321.5

    # Sin caja abierta no se paga y la orden queda sin vincular; sin permiso, ni se ofrece
    otra = api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "laboratorio_nombre": f"{laboratorio}B", "tipo_trabajo": "CORONA_ZIRCONIO", "costo_laboratorio": 10}).json()
    fab.cerrar_caja()
    try:
        assert api.post(f"/protesis/{otra['id']}/pagar-laboratorio", {}).status == 400
        assert not next(o for o in api.get("/protesis/").json() if o["id"] == otra["id"])["egreso_caja_id"]
    finally:
        fab.caja()
    doc = fab.usuario("DOCTOR")
    assert doc.api.post(f"/protesis/{otra['id']}/pagar-laboratorio", {}).status == 403
    q = abrir(doc.alias, doc.clave, ruta="protesis")
    q.locator("main table tbody tr").filter(has_text=f"{laboratorio}B").wait_for()
    assert q.get_by_role("button", name="Pagar Laboratorio").count() == 0


@caso("NOM-30")
def test_empleado_inactivo_con_saldo_sigue_en_nomina(fab, api, como_admin):
    apellido = f"Saldo{uuid4().hex[:5]}"
    doc = fab.usuario("DOCTOR", apellido=apellido, tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=50)
    fab.cobro_directo(fab.paciente()["id"], 1000, doctor_comision_id=doc.doctor_id)
    assert api.put(f"/usuarios/{doc.id}", {"activo": False}).ok
    fila = lambda: next((e for e in api.get("/empleados/personal").json() if e["usuario_id"] == doc.id), None)
    assert fila() and fila()["activo"] is False, "Con saldo sigue visible"
    p = como_admin("nomina")
    opcion = p.get_by_label("Empleado").locator("option", has_text=apellido)
    assert "Inactivo, con saldo por pagar" in opcion.inner_text()
    pago = api.post("/empleados/pagos", {"usuario_empleado_id": doc.id, "tipo_pago": "COMISION_TRATAMIENTOS", "monto_neto_pagado": 500, "metodo_pago": "TRANSFERENCIA"})
    assert pago.status == 201, pago.text
    assert fila() is None, "Ya pagado, deja de aparecer"


# ---------------- Conexión ----------------

@caso("RED-08")
def test_perder_la_red_mientras_se_usa(fab, api, como_admin):
    nombre = f"SinRed{uuid4().hex[:6]}"
    p = como_admin("pacientes")
    p.get_by_role("button", name="Nuevo Paciente").click()
    f = p.locator("form").last
    entradas = f.locator('input[type="text"], input:not([type])')
    entradas.nth(0).fill(nombre)
    entradas.nth(1).fill("QA")
    f.locator('input[required]').evaluate_all("(es) => es.forEach((e) => { if (!e.value) { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; s.call(e, e.type === 'date' ? '1990-01-01' : 'QA' + Math.random().toString(36).slice(2, 10)); e.dispatchEvent(new Event('input', { bubbles: true })); } })")
    p.context.set_offline(True)
    try:
        f.locator('button[type="submit"]').click()
        p.wait_for_timeout(800)
        assert p.get_by_role("alert").count() >= 1 or "error" in p.inner_text("body").lower() or "conex" in p.inner_text("body").lower(), "Muestra un error"
        assert api.get("/pacientes/", q=nombre).json() == [], "No se guardó nada"
        assert f.locator("input").first.input_value() == nombre, "Conserva lo que se escribió"
    finally:
        p.context.set_offline(False)
    f.locator('button[type="submit"]').click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(800)
    assert len(api.get("/pacientes/", q=nombre).json()) == 1, "Al volver la red continúa y se guarda una sola vez"


@caso("RED-09")
def test_sin_internet(como_admin):
    """Todo debe cargar desde el propio servidor: la clínica puede quedarse sin internet."""
    externas = []
    p = como_admin()
    p.context.route(lambda url: not url.startswith(BASE), lambda r: (externas.append(r.request.url), r.abort()))
    for ruta in RUTAS:
        p.goto(f"{BASE}/{ruta}")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(100)
        assert p.locator("main").count() == 1, ruta
    assert not [u for u in externas if not u.startswith(("data:", "blob:"))], externas[:8]


@caso("RED-12")
@pytest.mark.parametrize("ancho,alto", [(768, 1024), (390, 844)])
def test_tableta_y_celular(navegador, ancho, alto):
    from apoyo import BASE as direccion
    contexto = navegador.new_context(viewport={"width": ancho, "height": alto}, has_touch=True, is_mobile=True, ignore_https_errors=True, timezone_id=ZONA)
    try:
        p = contexto.new_page()
        p.goto(f"{direccion}/login")
        p.fill('input[type="text"]', "admin")
        p.fill('input[type="password"]', CLAVE_ADMIN)
        p.tap('button[type="submit"]')
        p.wait_for_url(f"{direccion}/")
        for ruta in ("pacientes", "citas", "caja"):
            p.goto(f"{direccion}/{ruta}")
            p.wait_for_load_state("networkidle")
            assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), ruta
    finally:
        contexto.close()


# ---------------- Rendimiento ----------------

@caso("REN-01")
def test_cada_pantalla_carga_rapido(como_admin):
    p = como_admin()
    lentas = {}
    for ruta in RUTAS:
        inicio = datetime.now()
        p.goto(f"{BASE}/{ruta}")
        p.wait_for_load_state("networkidle")
        segundos = (datetime.now() - inicio).total_seconds()
        if segundos >= 3:
            lentas[ruta] = round(segundos, 1)
    assert not lentas, lentas


_ = dia_libre
