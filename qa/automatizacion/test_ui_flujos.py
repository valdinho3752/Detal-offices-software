"""Flujos clínicos y de agenda completos, hechos en pantalla y comprobados en la base y la API."""
import re
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from apoyo import ZONA, ahora_clinica, dia_libre, sql

caso = pytest.mark.caso


@pytest.fixture(autouse=True)
def _caja_abierta(fab):
    fab.caja()


# ---------------- Odontograma ----------------

def hallazgos(paciente_id, pieza=None, tipo=None):
    filtro = f" and d.numero_fdi = {pieza}" if pieza else ""
    filtro += f" and o.tipo_registro = '{tipo}'" if tipo else ""
    filas = sql(
        "select d.numero_fdi||'|'||h.superficie||'|'||h.estado_clinico||'|'||upper(coalesce(h.color_hex,'')) "
        "from hallazgos_superficie h join piezas_dentales d on d.id = h.pieza_dental_id "
        f"join odontogramas o on o.id = d.odontograma_id where o.paciente_id = '{paciente_id}'{filtro}"
    )
    return [f.split("|") for f in filas.splitlines() if f.strip()]


def abrir_odontograma(abrir, usuario, paciente):
    p = abrir(usuario.alias, usuario.clave, ruta=f"odontograma?paciente_id={paciente['id']}")
    p.wait_for_selector('[title^="#"]')
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    return p


def elegir_pieza(p, pieza):
    p.get_by_title(re.compile(f"^#{pieza} ")).first.click()
    p.get_by_text("Seleccionar Cara Anatómica a Intervenir:").wait_for()


def caras(p):
    return p.get_by_text("Seleccionar Cara Anatómica a Intervenir:").locator("..").locator("button")


def pulsar(p, nombre, **opciones):
    p.get_by_role("button", name=nombre, **opciones).first.click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(450)


@caso("ODO-03", "ODO-04", "ODO-05", "ODO-06", "ODO-07", "ODO-10")
def test_estados_y_caras(fab, abrir):
    paciente = fab.paciente()
    doc = fab.usuario("DOCTOR")
    p = abrir_odontograma(abrir, doc, paciente)

    elegir_pieza(p, 11)
    pulsar(p, "Plan de tratamiento")
    caras(p).first.click()
    pulsar(p, "Marcar Cara Activa")
    assert hallazgos(paciente["id"], 11)[0][2:] == ["REQUERIDO_PATOLOGIA", "#EF4444"]

    elegir_pieza(p, 21)
    p.get_by_role("button", name="Alta clínica / Control posterior").first.click()
    caras(p).first.click()
    pulsar(p, "Marcar Cara Activa")
    assert hallazgos(paciente["id"], 21)[0][2:] == ["REALIZADO_EN_CLINICA", "#3B82F6"]

    elegir_pieza(p, 12)
    p.get_by_role("button", name="Diagnóstico y evaluación inicial").first.click()
    caras(p).first.click()
    pulsar(p, "Guardar Diagnóstico Inicial")
    assert hallazgos(paciente["id"], 12)[0][2] == "EXISTENTE_PREVIO"
    assert "Estado de Ingreso Inicial" in p.inner_text("main")

    # Cada cara queda registrada por separado
    p.get_by_role("button", name="Plan de tratamiento").first.click()
    elegir_pieza(p, 16)
    total = caras(p).count()
    assert total >= 6
    for indice in range(total):
        caras(p).nth(indice).click()
        pulsar(p, "Marcar Cara Activa")
    assert len({h[1] for h in hallazgos(paciente["id"], 16)}) == total

    pulsar(p, "Limpiar Diente Completo")
    assert hallazgos(paciente["id"], 16) == []
    assert hallazgos(paciente["id"], 11), "Limpiar un diente no toca los demás"

    elegir_pieza(p, 48)
    pulsar(p, "Marcar Inexistente")
    estado = sql(f"select d.estado_general from piezas_dentales d join odontogramas o on o.id = d.odontograma_id where o.paciente_id = '{paciente['id']}' and d.numero_fdi = 48")
    assert "EXTRAIDO" in estado
    assert "Ausente" in p.get_by_title(re.compile("^#48 ")).first.inner_text() or "AUSENTE" in p.get_by_title(re.compile("^#48 ")).first.inner_text().upper()


@caso("ODO-13", "ODO-14", "ODO-19", "ODO-20", "ODO-21", "ODO-22", "ODO-25", "TRA-14", "EVO-19", "E2E-01")
def test_plan_desde_el_odontograma(fab, api, abrir):
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=40)
    paciente = fab.paciente()
    pid = paciente["id"]
    marca = uuid4().hex[:6]
    uno = fab.tratamiento(300, nombre=f"Resina {marca}", categoria="RESTAURADORA")
    dos = fab.tratamiento(200, nombre=f"Sellante {marca}", categoria="PREVENCION")
    p = abrir_odontograma(abrir, doc, paciente)
    buscador = p.get_by_placeholder(re.compile("Buscar tratamiento por nombre o código"))

    elegir_pieza(p, 26)
    caras(p).first.click()
    buscador.fill(uno["nombre"])
    p.wait_for_timeout(250)
    pulsar(p, re.compile("Asignar$"))
    elegir_pieza(p, 36)
    caras(p).first.click()
    buscador.fill(dos["codigo"])
    p.wait_for_timeout(250)
    pulsar(p, re.compile("Asignar$"))

    pulsar(p, "Guardar Propuesta")
    planes = api.get("/tratamientos/planes", paciente_id=pid).json()
    assert len(planes) == 1 and planes[0]["estado"] == "PROPUESTO" and planes[0]["doctor_id"] == doc.doctor_id
    assert fab.saldo(pid) == 0
    items = {i["pieza_fdi"]: i for i in planes[0]["items"]}
    assert float(items[26]["costo_acordado"]) == 300 and items[26]["superficie"] and float(items[36]["costo_acordado"]) == 200

    pulsar(p, "Aprobar y Cargar a Cuenta")
    assert api.get(f"/tratamientos/planes/{planes[0]['id']}").json()["estado"] == "APROBADO"
    assert fab.saldo(pid) == 500
    pendientes = [h for h in hallazgos(pid, 26) if h[2] == "REQUERIDO_PATOLOGIA"]
    assert pendientes, "La cara queda marcada como plan"

    # Alta desde el plan
    pulsar(p, "Dar Alta")
    item = api.get(f"/tratamientos/planes/{planes[0]['id']}").json()["items"]
    assert sum(1 for i in item if i["estado"] == "COMPLETADO") == 1
    assert any(h[2] == "REALIZADO_EN_CLINICA" and h[3] == "#3B82F6" for h in hallazgos(pid)), "La cara se pinta de azul"

    # El otro tratamiento se realiza en una cita: cambia el odontograma de evolución, no el inicial
    resto = next(i for i in item if i["estado"] != "COMPLETADO")
    inicial = sorted(map(tuple, hallazgos(pid, tipo="INICIAL_INGRESO")))
    cita = fab.cita(pid, doctor=doc.doctor_id, item_plan_id=resto["id"]).json()
    assert doc.api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    assert sorted(map(tuple, hallazgos(pid, tipo="INICIAL_INGRESO"))) == inicial
    assert any(h[2] == "REALIZADO_EN_CLINICA" and h[0] == str(resto["pieza_fdi"]) for h in hallazgos(pid, tipo="EVOLUCION_ACTUAL"))

    visita = api.get("/visitas/", paciente_id=pid).json()[0]
    assert f"Pieza {resto['pieza_fdi']}" in visita["procedimiento_realizado"]
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "doctor_comision_id": doc.doctor_id}).ok
    assert fab.saldo(pid) == 500 - float(cuenta["total"])
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == round(float(cuenta["total"]) * 0.4, 2)


@caso("ODO-23", "ODO-24")
def test_resultado_clinico_por_tratamiento(fab, api):
    pid = fab.paciente()["id"]
    assert api.post("/odontogramas/", {"paciente_id": pid, "doctor_id": fab.doctor}).status == 201
    plan = fab.plan(pid)
    casos = {36: ("Extracción simple", "CIRUGIA_MAXILOFACIAL"), 46: ("Endodoncia molar", "ENDODONCIA"), 26: ("Corona de zirconio", "REHABILITACION_PROTESIS"), 16: ("Implante unitario", "IMPLANTOLOGIA")}
    items = {}
    for pieza, (nombre, categoria) in casos.items():
        res = api.post("/tratamientos/catalogo", {"codigo": f"Q{uuid4().hex[:8]}", "categoria": categoria, "nombre": f"{nombre} {uuid4().hex[:4]}", "costo_base": 10})
        if res.status != 201:
            res = api.post("/tratamientos/catalogo", {"codigo": f"Q{uuid4().hex[:8]}", "categoria": "PREVENCION", "nombre": f"{nombre} {uuid4().hex[:4]}", "costo_base": 10})
        assert res.status == 201, res.text
        items[pieza] = fab.item(plan, res.json()["id"], 10, pieza_fdi=pieza, superficie="OCLUSAL")
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    for pieza, item in items.items():
        cita = fab.cita(pid, item_plan_id=item["id"]).json()
        assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok, pieza
    consulta = lambda pieza, campo: sql(f"select d.{campo} from piezas_dentales d join odontogramas o on o.id = d.odontograma_id where o.paciente_id = '{pid}' and o.tipo_registro = 'EVOLUCION_ACTUAL' and d.numero_fdi = {pieza}")
    assert consulta(36, "estado_general") == "EXTRAIDO"
    assert not [h for h in hallazgos(pid, 36, "EVOLUCION_ACTUAL") if h[2] == "REQUERIDO_PATOLOGIA"], "Sin patologías pendientes"
    assert consulta(46, "tiene_endodoncia") == "t"
    assert consulta(16, "estado_general") == "IMPLANTE"
    assert any("REALIZADO_EN_CLINICA" == h[2] for h in hallazgos(pid, 26, "EVOLUCION_ACTUAL"))


# ---------------- Agenda ----------------

def formulario_cita(p, nombre, inicio=None, fin=None, fecha=None):
    f = p.locator("form").last
    buscador = f.get_by_placeholder("Buscar paciente por nombre o CI...")
    assert buscador.count() == 1, "No debe venir un paciente preseleccionado"
    buscador.fill(nombre)
    p.wait_for_timeout(200)
    f.get_by_text(nombre).first.click()
    if fecha:
        f.locator('input[type="date"]').first.fill(fecha)
    if inicio:
        f.locator('input[type="time"]').nth(0).fill(inicio)
        f.locator('input[type="time"]').nth(1).fill(fin)
    f.get_by_placeholder("ej. Evaluación general, Extracción de tercer molar").fill("Prueba de agenda")
    f.get_by_role("button", name="Agendar Cita").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)


@caso("AGE-03", "AGE-04", "CAL-09", "CAL-06")
def test_nueva_cita_de_varios_bloques(fab, api, como_admin):
    nombre = f"Bloques{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    otro = fab.paciente()
    dia = dia_libre()
    p = como_admin("citas")
    p.get_by_role("button", name="Nueva Cita").click()
    formulario_cita(p, nombre, "09:00", "10:30", dia)
    citas = api.get("/citas/", paciente_id=paciente["id"]).json()
    assert len(citas) == 1 and citas[0]["motivo_consulta"] == "Prueba de agenda"
    medico = citas[0]["doctor_id"]
    def en_hora_local(inicio, fin):
        # El formulario trabaja con la hora de la clínica
        instante = lambda hora: datetime.fromisoformat(f"{dia}T{hora}:00").replace(tzinfo=ZoneInfo(ZONA)).isoformat()
        return api.post("/citas/", {"paciente_id": otro["id"], "doctor_id": medico, "motivo_consulta": "Bloque", "fecha_inicio_programada": instante(inicio), "fecha_fin_programada": instante(fin), "notas_adicionales": "Box 3"})

    assert en_hora_local("10:00", "10:30").status == 409, "10:00 sigue ocupado"
    assert en_hora_local("10:30", "11:00").status == 201, "10:30 ya está libre"

    # Una cita de hoy se ve igual en la matriz y en el mes, y al hacer clic se edita
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    assert fab.cita(paciente["id"], hoy, "20:30", "21:00", box=4).status == 201
    p.reload()
    p.wait_for_load_state("networkidle")
    p.wait_for_selector("table")
    p.wait_for_timeout(400)
    assert nombre.lower() in p.locator("tbody").inner_text().lower()
    p.get_by_role("button", name="Vista Mensual").click()
    p.wait_for_timeout(300)
    enlace = p.get_by_title(re.compile(rf"Click para editar: .*{nombre}"))
    assert enlace.count() == 1
    enlace.click()
    p.wait_for_timeout(300)
    assert p.locator("form").last.get_by_role("button", name=re.compile("Guardar|Actualizar")).count() >= 1


@caso("AGE-02")
def test_paciente_no_preseleccionado(fab, api, como_admin):
    """Una cita nunca debe quedar a nombre de quien aparezca primero en la lista."""
    nombre = f"Cita{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre)
    p = como_admin("citas")
    p.wait_for_selector("table")
    for _ in range(5):
        p.get_by_title("Día Siguiente").click()
    p.wait_for_load_state("networkidle")
    p.locator("tbody td").filter(has_text="Libre").last.click()
    formulario_cita(p, nombre)
    assert api.get("/citas/", paciente_id=paciente["id"]).json(), "La cita es del paciente elegido"
    assert nombre.lower() in p.locator("tbody").inner_text().lower()
    p.get_by_role("button", name="Nueva Cita").click()
    assert p.locator("form").last.get_by_placeholder("Buscar paciente por nombre o CI...").count() == 1, "Tampoco arrastra al último paciente"


@caso("SIL-11")
def test_sillon_desactivado_con_citas(fab, api, como_admin):
    sillon = api.post("/sillones/", {"nombre": f"Temporal{uuid4().hex[:4]}"}).json()
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    cita = fab.cita(fab.paciente()["id"], hoy, "20:00", "20:30", box=sillon["numero"], doctor=fab.usuario("DOCTOR").doctor_id)
    assert cita.status == 201, cita.text
    assert api.put(f"/citas/{cita.json()['id']}", {"estado": "FINALIZADA"}).ok
    assert api.delete(f"/sillones/{sillon['id']}").json()["resultado"] == "DESACTIVADO"
    p = como_admin("citas")
    columna = p.locator("thead th").filter(has_text=sillon["nombre"])
    columna.wait_for()
    assert "desactivado" in columna.inner_text().lower()


# ---------------- Reportes ----------------

def _personalizado(p, desde, hasta):
    p.get_by_role("group", name="Periodo del reporte").get_by_role("button", name="Personalizado", exact=True).click()
    fechas = p.locator('input[type="date"]')
    fechas.nth(0).fill(desde)
    fechas.nth(1).fill(hasta)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)


def _pago_en(fab, monto, cuando):
    pago = fab.cobro_directo(fab.paciente()["id"], monto)
    sql(f"update pagos set fecha_hora = '{cuando}' where id = '{pago['id']}'")


@caso("REP-04", "REP-14")
def test_limites_de_fecha_en_reportes(fab, como_admin):
    # Último minuto del último día del mes, hora de la clínica, y un pago en el primer día del siguiente
    _pago_en(fab, 4321.00, f"1991-03-31 23:30:00 {ZONA}")
    _pago_en(fab, 1234.00, f"1991-04-01 00:30:00 {ZONA}")
    p = como_admin("reportes")
    _personalizado(p, "1991-03-01", "1991-03-31")
    texto = p.inner_text("main")
    assert "$4.321,00" in texto and "1.234,00" not in texto, "Cuenta en su mes y día locales"
    _personalizado(p, "1991-03-31", "1991-03-31")
    assert "$4.321,00" in p.inner_text("main"), "Ambos días incluidos"
    _personalizado(p, "1991-04-01", "1991-04-01")
    texto = p.inner_text("main")
    assert "$1.234,00" in texto and "4.321,00" not in texto


# ---------------- Auditoría ----------------

@caso("AUD-02", "AUD-03")
def test_detalle_de_auditoria(fab, api, como_admin):
    t = fab.tratamiento(111)
    assert api.put(f"/tratamientos/catalogo/{t['id']}", {"costo_base": 222}).ok
    p = como_admin("auditoria")
    p.locator("select").first.select_option("catalogo_tratamientos")
    p.locator("select").nth(1).select_option("UPDATE")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(400)
    fila = p.locator("main table tbody tr").first.inner_text()
    assert re.search(r"\d{1,2}/\d{1,2}/\d{4}", fila), f"Muestra la fecha real: {fila}"
    assert "Administrador Principal" in fila and "127.0.0.1" not in fila, f"Autor e IP reales: {fila}"
    p.get_by_role("button", name="Inspeccionar Diff").first.click()
    p.wait_for_timeout(250)
    detalle = p.inner_text("body")
    assert "111" in detalle and "222" in detalle, "Muestra el valor anterior y el nuevo"


# ---------------- Pacientes por rol ----------------

@caso("PAC-20")
def test_asistente_sin_botones_de_edicion(fab, abrir):
    paciente = fab.paciente(nombres=f"Sinboton{uuid4().hex[:5]}")
    asi = fab.usuario("ASISTENTE")
    p = abrir(asi.alias, asi.clave, ruta="pacientes")
    assert p.get_by_role("button", name="Nuevo Paciente").count() == 0
    p.get_by_placeholder("Buscar por nombre, documento o apellido...").fill(paciente["nombres"])
    p.wait_for_timeout(600)
    p.locator("main").get_by_text(paciente["nombres"]).first.click()
    p.wait_for_timeout(300)
    assert p.locator("main").get_by_role("button", name=re.compile("Editar")).count() == 0


@caso("PRO-05", "PRO-06", "PRO-10", "RAD-11")
def test_protesis_avanza_en_pantalla(fab, api, abrir, como_admin):
    pid = fab.paciente()["id"]
    lab = f"Lab{uuid4().hex[:6]}"
    orden = api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "laboratorio_nombre": lab, "tipo_trabajo": "CORONA_ZIRCONIO", "fecha_entrega_esperada": "2031-02-03"}).json()
    p = como_admin("protesis")
    fila = p.locator("main table tbody tr").filter(has_text=lab)
    fila.wait_for()
    assert "2031-02-03" in fila.inner_text(), "Muestra la fecha de entrega"
    estado = lambda: api.get("/protesis/").json()
    actual = lambda: next(o for o in estado() if o["id"] == orden["id"])
    for boton, esperado in (("En Proceso", "EN_LABORATORIO"), ("Recibir en Clínica", "RECIBIDO_EN_CLINICA"), ("Prueba en Boca", "PRUEBA_EN_BOCA"), ("Colocado", "INSTALADO_FINALIZADO")):
        fila.get_by_role("button", name=boton).click()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(350)
        assert actual()["estado"] == esperado, boton
    assert actual()["fecha_recepcion_real"], "Registra la fecha real de recepción"
    assert fila.get_by_role("button").count() == 0, "Una orden instalada ya no avanza"

    otra = api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "laboratorio_nombre": f"{lab}B", "tipo_trabajo": "CORONA_ZIRCONIO"}).json()
    asi = fab.usuario("ASISTENTE")
    a = abrir(asi.alias, asi.clave, ruta="protesis")
    a.locator("main table tbody tr").filter(has_text=f"{lab}B").wait_for()
    assert a.get_by_role("button", name=re.compile("Nueva Orden")).count() == 0
    assert a.locator("main table tbody tr").filter(has_text=f"{lab}B").get_by_role("button").count() == 0
    assert otra["id"]

    rx = api.post("/radiografias/", {"paciente_id": pid, "tipo_estudio": "PERIAPICAL", "titulo": "Sin borrar", "archivo_url": "https://ejemplo.test/a.jpg"}).json()
    v = abrir(asi.alias, asi.clave, ruta=f"radiografias?paciente_id={pid}")
    v.get_by_text("Sin borrar").wait_for()
    assert not v.get_by_title("Eliminar radiografía").is_visible() and rx["id"]


# ---------------- Fin de mes ----------------

@caso("E2E-08")
def test_fin_de_mes(fab, api):
    fab.caja()
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=30)
    rec = fab.usuario("RECEPCION", salario_base=3000)
    pid = fab.paciente()["id"]
    pagar = lambda uid, tipo, neto, **extra: api.post("/empleados/pagos", {"usuario_empleado_id": uid, "tipo_pago": tipo, "monto_neto_pagado": neto, "metodo_pago": "TRANSFERENCIA", **extra})
    for monto in (1000, 2000, 500):
        fab.cobro_directo(pid, monto, doctor_comision_id=doc.doctor_id)
    liq = lambda uid: api.get(f"/empleados/liquidacion/{uid}").json()
    assert liq(doc.id)["comision_bruta_generada"] == 1050
    assert pagar(doc.id, "ADELANTO", 200).status == 201
    assert pagar(doc.id, "COMISION_TRATAMIENTOS", 500).status == 201
    assert liq(doc.id)["saldo_comision_por_pagar"] == 350
    assert pagar(doc.id, "COMISION_TRATAMIENTOS", 350).status == 201
    assert liq(doc.id)["saldo_comision_por_pagar"] == 0
    assert pagar(rec.id, "ADELANTO", 700).status == 201
    assert pagar(rec.id, "SUELDO_MENSUAL", 2300, monto_base=3000, deducciones_descuentos=700).status == 201
    assert liq(rec.id)["total_anticipos"] == 0
    pagados = sum(float(x["monto_neto_pagado"]) for x in api.get("/empleados/pagos", usuario_empleado_id=rec.id).json())
    assert pagados == 3000, "Lo pagado coincide con el sueldo"
