"""Reglas de negocio: pacientes, planes, agenda, caja, cobros, nómina, asistencia y más."""
import concurrent.futures as cf
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from apoyo import ahora_clinica, dia_libre, peticion_directa, sql

caso = pytest.mark.caso
NADIE = "00000000-0000-0000-0000-000000000000"


def a_la_vez(funcion, n=12):
    with cf.ThreadPoolExecutor(n) as hilos:
        return list(hilos.map(lambda _: funcion(), range(n)))


# ---------------- Pacientes ----------------

def _datos_paciente(**extra):
    return {"nombres": "A", "apellidos": "B", "tipo_documento": "CI", "numero_documento": f"Q-{uuid4().hex[:10]}", "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "7", **extra}


@caso("PAC-01", "PAC-02", "PAC-11")
def test_registrar_y_editar_paciente(fab, api):
    completo = fab.paciente(email="a@b.com", direccion="Calle 1", ocupacion="Chef", contacto_emergencia_nombre="M", contacto_emergencia_telefono="7")
    assert completo["direccion"] == "Calle 1" and completo["contacto_emergencia_nombre"] == "M"
    assert fab.paciente()["id"]
    assert api.put(f"/pacientes/{completo['id']}", {"telefono": "72222222"}).json()["telefono"] == "72222222"
    assert any(r["registro_id"] == completo["id"] for r in fab.auditoria("pacientes"))


@caso("PAC-03", "PAC-04")
def test_documento_unico(fab, api):
    a, b = fab.paciente(), fab.paciente()
    res = api.post("/pacientes/", _datos_paciente(numero_documento=a["numero_documento"]))
    assert res.status == 400 and "Ya existe un paciente" in res.detalle
    res = api.put(f"/pacientes/{b['id']}", {"numero_documento": a["numero_documento"]})
    assert res.status == 400 and "Ya existe otro paciente" in res.detalle


@caso("PAC-05", "PAC-06", "PAC-07", "PAC-08")
def test_validaciones_de_paciente(fab, api):
    futuro = (date.today() + timedelta(days=2)).isoformat()
    assert api.post("/pacientes/", _datos_paciente(fecha_nacimiento=futuro)).status == 422
    p = fab.paciente()
    assert api.put(f"/pacientes/{p['id']}", {"fecha_nacimiento": futuro}).status == 422
    assert api.post("/pacientes/", _datos_paciente(email="no-es-correo")).status == 422
    assert api.post("/pacientes/", {"nombres": "A"}).status == 422
    assert api.post("/pacientes/", _datos_paciente(nombres="x" * 5000)).status == 422


@caso("PAC-13")
def test_antecedentes_como_doctor(fab):
    doc = fab.usuario("DOCTOR")
    p = fab.paciente()
    assert doc.api.put(f"/pacientes/{p['id']}/antecedentes", {"alergias": "Penicilina"}).ok
    assert doc.api.get(f"/pacientes/{p['id']}").json()["antecedentes"]["alergias"] == "Penicilina"


@caso("PAC-15", "PAC-16")
def test_buscar_paciente(fab, api):
    unico = f"Zq{uuid4().hex[:8]}"
    p = fab.paciente(nombres=unico)
    for termino in (unico, unico.upper(), unico[:6], p["numero_documento"]):
        assert any(x["id"] == p["id"] for x in api.get("/pacientes/", buscar=termino, busqueda=termino, q=termino, search=termino).json()), termino
    assert api.get("/pacientes/", buscar="nada_que_coincida_xyz", busqueda="nada_que_coincida_xyz", q="nada_que_coincida_xyz", search="nada_que_coincida_xyz").json() == []


@caso("PAC-19")
def test_ver_ficha_queda_auditado(fab, api):
    p = fab.paciente()
    assert api.get(f"/pacientes/{p['id']}").ok
    assert any(r["registro_id"] == p["id"] and r["accion"] == "VIEW" for r in fab.auditoria("pacientes"))


# ---------------- Catálogo y planes ----------------

@caso("TRA-01", "TRA-02", "TRA-03", "TRA-04", "TRA-05", "TRA-12")
def test_catalogo_validaciones(fab, api):
    t = fab.tratamiento()
    base = {"categoria": "PREVENCION", "nombre": "x", "costo_base": 1}
    res = api.post("/tratamientos/catalogo", {**base, "codigo": t["codigo"]})
    assert res.status == 400 and "ya existe" in res.detalle
    assert api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8], "costo_base": -1}).status == 422
    assert api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8], "duracion_estimada_min": 0}).status == 422
    assert api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8], "nombre": "   "}).status == 422
    assert api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8], "costo_base": 1e14}).status == 422
    for rol in ("DOCTOR", "RECEPCION"):
        assert fab.usuario(rol).api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8]}).status == 403
    todos = [x["id"] for x in api.get("/usuarios/permisos").json()]
    rol_total = api.post("/usuarios/roles", {"nombre": f"Todo {uuid4().hex[:8]}", "permiso_ids": todos}).json()["id"]
    assert fab.usuario(rol_total).api.post("/tratamientos/catalogo", {**base, "codigo": uuid4().hex[:8]}).status == 403, "Solo administradores, incluso con todos los permisos"


@caso("TRA-06", "TRA-07")
def test_cambiar_precio(fab, api):
    t = fab.tratamiento(100)
    p = fab.paciente()
    plan = fab.plan(p["id"])
    fab.item(plan, t["id"], 100)
    assert api.put(f"/tratamientos/catalogo/{t['id']}", {"costo_base": 150}).ok
    assert api.get(f"/tratamientos/planes/{plan}").json()["costo_total"] in (100, "100.00", 100.0)
    registro = next(r for r in fab.auditoria("catalogo_tratamientos") if r["registro_id"] == t["id"] and r["accion"] == "UPDATE")
    assert registro["datos_previos"] and registro["datos_nuevos"]


@caso("TRA-08", "TRA-09", "TRA-10", "ODO-15")
def test_eliminar_tratamiento(fab, api):
    sin_uso = fab.tratamiento()
    assert api.delete(f"/tratamientos/catalogo/{sin_uso['id']}").json()["resultado"] == "ELIMINADO"
    usado = fab.tratamiento()
    plan = fab.plan(fab.paciente()["id"])
    fab.item(plan, usado["id"])
    assert api.delete(f"/tratamientos/catalogo/{usado['id']}").json()["resultado"] == "DESACTIVADO"
    assert api.get(f"/tratamientos/planes/{plan}").json()["items"], "El plan lo conserva"
    assert usado["id"] not in [t["id"] for t in api.get("/tratamientos/catalogo").json() if t["activo"]]
    assert api.put(f"/tratamientos/catalogo/{usado['id']}", {"activo": True}).json()["activo"] is True


@caso("TRA-13")
def test_doctor_consulta_catalogo(fab):
    assert fab.usuario("DOCTOR").api.get("/tratamientos/catalogo").status == 200


@caso("TRA-15")
def test_plan_y_doctor(fab, api):
    doc, otro = fab.usuario("DOCTOR"), fab.usuario("DOCTOR")
    plan = doc.api.post("/tratamientos/planes", {"paciente_id": fab.paciente()["id"], "titulo": "P"}).json()
    assert plan["doctor_id"] == doc.doctor_id
    assert doc.api.put(f"/tratamientos/planes/{plan['id']}", {"doctor_id": otro.doctor_id}).status == 403
    assert api.put(f"/tratamientos/planes/{plan['id']}", {"doctor_id": otro.doctor_id}).json()["doctor_id"] == otro.doctor_id


@caso("TRA-16", "TRA-17", "ODO-16", "ODO-18")
def test_total_del_plan(fab, api):
    p = fab.paciente()
    plan = fab.plan(p["id"])
    t = fab.tratamiento()
    a = fab.item(plan, t["id"], 100)
    b = fab.item(plan, t["id"], 50)
    total = lambda: float(api.get(f"/tratamientos/planes/{plan}").json()["costo_total"])
    assert total() == 150
    assert api.put(f"/tratamientos/items/{a['id']}", {"costo_acordado": 80}).ok
    assert total() == 130
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    assert fab.saldo(p["id"]) == 130
    assert api.delete(f"/tratamientos/items/{b['id']}").status == 204
    assert total() == 80 and fab.saldo(p["id"]) == 80


@caso("ODO-17")
def test_descuento_mayor_al_precio(fab):
    plan = fab.plan(fab.paciente()["id"])
    t = fab.tratamiento()
    res = fab.admin.post("/tratamientos/items", {"plan_id": plan, "tratamiento_id": t["id"], "precio_unitario": 50, "descuento": 80})
    assert res.status == 201 and float(res.json()["costo_acordado"]) == 0


@caso("TRA-18")
def test_montos_negativos_de_plan(fab, api):
    plan = fab.plan(fab.paciente()["id"])
    t = fab.tratamiento()
    assert api.post("/tratamientos/items", {"plan_id": plan, "tratamiento_id": t["id"], "costo_acordado": -1}).status == 422
    assert api.post("/tratamientos/items", {"plan_id": plan, "tratamiento_id": t["id"], "precio_unitario": 10, "descuento": -5}).status == 422


@caso("TRA-19", "TRA-20")
def test_total_y_cancelacion_con_pagos(fab, api):
    p = fab.paciente()
    plan = fab.plan(p["id"], 200)
    fab.caja()
    respuesta = api.post("/caja/pagos", {"paciente_id": p["id"], "plan_id": plan, "monto": 150, "metodo_pago": "TRANSFERENCIA"})
    assert respuesta.status == 201, respuesta.text
    pago = respuesta.json()
    assert api.put(f"/tratamientos/planes/{plan}", {"costo_total": 149}).status == 409
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "CANCELADO"}).status == 409
    assert api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error"}).ok
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "CANCELADO"}).ok
    assert fab.saldo(p["id"]) == 0


@caso("TRA-21", "EVO-20")
def test_proxima_sesion(fab, api):
    plan = fab.plan(fab.paciente()["id"])
    item = fab.item(plan, fab.tratamiento()["id"])
    assert api.put(f"/tratamientos/items/{item['id']}", {"es_proxima_sesion": True}).json()["estado"] == "PROXIMA_SESION"


@caso("ODO-28", "ODO-29", "ODO-30")
def test_permisos_de_odontograma(fab, api):
    p = fab.paciente()
    doc, otro = fab.usuario("DOCTOR"), fab.usuario("DOCTOR")
    assert doc.api.post("/odontogramas/", {"paciente_id": p["id"], "doctor_id": otro.doctor_id}).status == 403
    assert fab.usuario("ASISTENTE").api.post("/odontogramas/", {"paciente_id": p["id"]}).status == 403
    assert fab.usuario("ASISTENTE").api.get("/odontogramas/", paciente_id=p["id"]).status == 200
    assert fab.usuario("RECEPCION").api.get("/odontogramas/").status == 403


@caso("ODO-35")
def test_pieza_inexistente(fab, api):
    plan = fab.plan(fab.paciente()["id"])
    t = fab.tratamiento()
    for pieza in (0, 19, 56, 99):
        assert api.post("/tratamientos/items", {"plan_id": plan, "tratamiento_id": t["id"], "costo_acordado": 1, "pieza_fdi": pieza}).status == 422


# ---------------- Agenda ----------------

@caso("AGE-05", "AGE-06", "AGE-07", "AGE-08", "AGE-09", "AGE-11", "AGE-12")
def test_reglas_de_horario(fab, api):
    p = fab.paciente()["id"]
    dia = dia_libre()
    otro = fab.usuario("DOCTOR")
    assert fab.cita(p, dia, "09:00", "10:00", 1).status == 201
    res = fab.cita(p, dia, "10:00", "09:00", 2)
    assert res.status == 400 and "posterior" in res.detalle
    res = fab.cita(p, dia, "09:30", "10:30", 2)
    assert res.status == 409 and "doctor ya tiene" in res.detalle
    res = fab.cita(p, dia, "09:30", "10:30", 1, doctor=otro.doctor_id)
    assert res.status == 409 and "ya está ocupado" in res.detalle
    assert fab.cita(p, dia, "10:00", "11:00", 1).status == 201, "Empezar cuando termina otra no es solape"
    assert fab.cita(p, dia, "09:00", "10:00", 2, doctor=otro.doctor_id).status == 201
    assert fab.cita(p, dia_libre(), doctor=str(uuid4())).status == 404
    assert fab.cita(str(uuid4()), dia_libre()).status == 404
    res = fab.cita(p, dia_libre(), box=99)
    assert res.status == 400 and "no existe o está desactivado" in res.detalle


@caso("AGE-10")
def test_citas_simultaneas(fab, api):
    p = fab.paciente()["id"]
    dia = dia_libre()
    cuerpo = {"paciente_id": p, "doctor_id": fab.doctor, "motivo_consulta": "Carrera", "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z", "notas_adicionales": "Box 2"}
    res = a_la_vez(lambda: peticion_directa("POST", "/citas/", api.token, cuerpo))
    assert res.count(201) == 1 and set(res) <= {201, 409}, res


@caso("AGE-13", "AGE-14")
def test_mover_cita(fab, api):
    p = fab.paciente()["id"]
    dia = dia_libre()
    a = fab.cita(p, dia, "09:00", "10:00", 1).json()
    fab.cita(p, dia, "11:00", "12:00", 2)
    movida = api.put(f"/citas/{a['id']}", {"fecha_inicio_programada": f"{dia}T13:00:00Z", "fecha_fin_programada": f"{dia}T14:00:00Z", "motivo_consulta": "Otro", "box_numero": 3})
    assert movida.ok and movida.json()["motivo_consulta"] == "Otro" and "Box 3" in movida.json()["notas_adicionales"]
    assert api.put(f"/citas/{a['id']}", {"fecha_inicio_programada": f"{dia}T11:30:00Z", "fecha_fin_programada": f"{dia}T12:30:00Z"}).status == 409
    actual = next(c for c in api.get("/citas/", paciente_id=p).json() if c["id"] == a["id"])
    assert actual["fecha_inicio_programada"] == movida.json()["fecha_inicio_programada"], "Sigue en su lugar"


@caso("AGE-16", "AGE-17", "AGE-18")
def test_cancelar_y_no_asistio(fab, api):
    p = fab.paciente()["id"]
    dia = dia_libre()
    a = fab.cita(p, dia, box=1).json()
    assert api.delete(f"/citas/{a['id']}").status == 204
    citas = {c["id"]: c for c in api.get("/citas/", paciente_id=p).json()}
    assert citas[a["id"]]["estado"] == "CANCELADA", "Sigue visible"
    b = fab.cita(p, dia, box=1).json()
    assert api.put(f"/citas/{b['id']}", {"estado": "NO_ASISTIO"}).ok
    c = fab.cita(p, dia, box=1).json()
    assert api.put(f"/citas/{c['id']}", {"estado": "FINALIZADA"}).ok
    res = api.delete(f"/citas/{c['id']}")
    assert res.status in (400, 409) and "ya fue atendida" in res.detalle


@caso("AGE-19", "AGE-24")
def test_recorrido_de_estados(fab, api):
    cita = fab.cita(fab.paciente()["id"]).json()
    url = f"/citas/{cita['id']}/sillon"
    assert api.patch(url, {"estado": "EN_ESPERA"}).json()["hora_llegada_recepcion"]
    assert api.patch(url, {"estado": "EN_SILLON"}).json()["hora_inicio_sillon"]
    assert api.patch(url, {"estado": "FINALIZADA"}).json()["hora_fin_sillon"]


@caso("AGE-20", "AGE-21", "EVO-01", "EVO-04", "CCI-01")
def test_finalizar_con_tratamientos(fab, api):
    p = fab.paciente()["id"]
    plan = fab.plan(p)
    t = fab.tratamiento(nombre="Resina compuesta", categoria="RESTAURADORA")
    a, b = fab.item(plan, t["id"], 100, pieza_fdi=16), fab.item(plan, t["id"], 50, pieza_fdi=21)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    dia = dia_libre()
    cita = fab.cita(p, dia, item_plan_id=a["id"], notas=f"Box 1 {b['id']}").json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    visita = api.get("/visitas/", paciente_id=p).json()[0]
    assert visita["generada_automaticamente"] and visita["fecha_hora"].startswith(dia[:8]) and "Pieza 16" in visita["procedimiento_realizado"] and "Pieza 21" in visita["procedimiento_realizado"]
    items = {i["id"]: i for i in api.get(f"/tratamientos/planes/{plan}").json()["items"]}
    assert items[a["id"]]["estado"] == items[b["id"]]["estado"] == "COMPLETADO"
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    assert cuenta["estado"] == "PENDIENTE" and len(cuenta["lineas"]) == 2 and float(cuenta["total"]) == 150


@caso("AGE-22", "EVO-03", "CCI-02")
def test_finalizar_sin_plan(fab, api):
    p = fab.paciente()["id"]
    t = fab.tratamiento(75)
    con = fab.cita(p, tratamiento_id=t["id"]).json()
    assert api.put(f"/citas/{con['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == con["id"])
    assert float(cuenta["total"]) == 75
    visita = api.get("/visitas/", paciente_id=p).json()[0]
    assert "Sin diagnóstico registrado" in visita["diagnostico"]


@caso("AGE-23", "AGE-34")
def test_cita_atendida_no_cambia(fab, api):
    p = fab.paciente()["id"]
    cita = fab.cita(p).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    for cuerpo in ({"estado": "FINALIZADA"}, {"estado": "PROGRAMADA"}, {"motivo_consulta": "x"}):
        assert api.put(f"/citas/{cita['id']}", cuerpo).status == 409
    assert api.patch(f"/citas/{cita['id']}/sillon", {"estado": "EN_SILLON"}).status == 409
    assert len(api.get("/visitas/", paciente_id=p).json()) == 1
    assert len([c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"]]) == 1


@caso("AGE-27", "AGE-28", "AGE-29", "AGE-30")
def test_permisos_de_agenda(fab, api):
    p = fab.paciente()["id"]
    doc1, doc2 = fab.usuario("DOCTOR"), fab.usuario("DOCTOR")
    cita = fab.cita(p, doctor=doc1.doctor_id).json()
    res = doc2.api.put(f"/citas/{cita['id']}", {"motivo_consulta": "x"})
    assert res.status == 403 and "tus propias citas" in res.detalle
    assert doc2.api.patch(f"/citas/{cita['id']}/sillon", {"estado": "EN_ESPERA"}).status == 403
    dia = dia_libre()
    assert doc2.api.post("/citas/", {"paciente_id": p, "doctor_id": doc1.doctor_id, "motivo_consulta": "x", "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z", "notas_adicionales": "Box 1"}).status == 403
    assert fab.usuario("ASISTENTE").api.put(f"/citas/{cita['id']}", {"motivo_consulta": "A"}).ok
    assert fab.usuario("RECEPCION").api.put(f"/citas/{cita['id']}", {"motivo_consulta": "R"}).ok
    assert fab.usuario("ASISTENTE").api.post("/citas/", {}).status == 403


@caso("AGE-35")
def test_reactivar_sobre_ocupado(fab, api):
    p = fab.paciente()["id"]
    dia = dia_libre()
    cancelada = fab.cita(p, dia).json()
    api.delete(f"/citas/{cancelada['id']}")
    assert fab.cita(p, dia).status == 201
    assert api.put(f"/citas/{cancelada['id']}", {"estado": "PROGRAMADA"}).status == 409


@caso("AGE-36")
def test_finalizar_saltando_pasos(fab, api):
    p = fab.paciente()["id"]
    cita = fab.cita(p).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    assert api.get("/visitas/", paciente_id=p).json()


# ---------------- Evolución ----------------

def _evolucion(api, p, doctor, **extra):
    return api.post("/visitas/", {"paciente_id": p, "doctor_id": doctor, "motivo_visita": "M", "diagnostico": "D", "procedimiento_realizado": "P", **extra})


@caso("EVO-05", "EVO-08", "EVO-09", "EVO-10")
def test_evolucion_inmutable(fab, api):
    p = fab.paciente()["id"]
    v = _evolucion(api, p, fab.doctor).json()
    assert not v["generada_automaticamente"]
    assert api.put(f"/visitas/{v['id']}", {"diagnostico": "x"}).status == 405
    assert api.delete(f"/visitas/{v['id']}").status == 405
    assert "HISTORIA_CLINICA_UPDATE" not in api.get("/usuarios/permisos").text


@caso("EVO-11", "EVO-12", "EVO-13", "EVO-14", "EVO-15", "EVO-16")
def test_observaciones(fab, api):
    p = fab.paciente()["id"]
    v = _evolucion(api, p, fab.doctor).json()
    url = f"/visitas/{v['id']}/observaciones"
    doc, asi, rec = fab.usuario("DOCTOR"), fab.usuario("ASISTENTE"), fab.usuario("RECEPCION")
    obs = doc.api.post(url, {"texto": "Por doctor"}).json()
    assert obs["autor_nombre"] and obs["rol_autor"] == "DOCTOR"
    assert asi.api.post(url, {"texto": "Por asistente"}).status == 201
    assert api.post(url, {"texto": "   "}).status == 422 and api.post(url, {"texto": "x" * 2001}).status == 422
    assert api.put(f"{url}/{obs['id']}", {"texto": "x"}).status in (404, 405) and api.delete(f"{url}/{obs['id']}").status in (404, 405)
    assert rec.api.get("/visitas/").status == 403 and rec.api.post(url, {"texto": "x"}).status == 403
    assert _evolucion(asi.api, p, fab.doctor).status == 403


@caso("EVO-17", "EVO-18")
def test_una_evolucion_por_cita(fab, api):
    p = fab.paciente()["id"]
    cita = fab.cita(p).json()
    assert _evolucion(api, p, fab.doctor, cita_id=cita["id"]).status == 201
    res = _evolucion(api, p, fab.doctor, cita_id=cita["id"])
    assert res.status == 409 and "ya tiene una evolución" in res.detalle
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    assert len(api.get("/visitas/", paciente_id=p).json()) == 1


# Sin caso propio: comprobación adicional
def test_tratamiento_desde_evolucion(fab, api):
    p = fab.paciente()["id"]
    plan = fab.plan(p)
    item = fab.item(plan, fab.tratamiento()["id"])
    assert _evolucion(api, p, fab.doctor, item_plan_id=item["id"]).ok
    assert api.get(f"/tratamientos/planes/{plan}").json()["items"][0]["estado"] == "COMPLETADO"


@caso("EVO-24")
def test_historial_ordenado(fab, api):
    p = fab.paciente()["id"]
    for fecha in ("2030-01-01T10:00:00Z", "2030-03-01T10:00:00Z", "2030-02-01T10:00:00Z"):
        _evolucion(api, p, fab.doctor, fecha_hora=fecha)
    fechas = [v["fecha_hora"] for v in api.get("/visitas/", paciente_id=p).json()]
    assert fechas == sorted(fechas, reverse=True)


# ---------------- Radiografías ----------------

def _rx(p, **extra):
    return {"paciente_id": p, "tipo_estudio": "PERIAPICAL", "titulo": "Rx", "archivo_url": "https://ejemplo.test/a.jpg", **extra}


@caso("RAD-01", "RAD-02", "RAD-03", "RAD-10", "RAD-11", "RAD-12", "RAD-13")
def test_radiografias(fab, api):
    p = fab.paciente()["id"]
    for tipo in ("PANORAMICA", "PERIAPICAL", "ALETA_MORDIDA", "CEFALOMETRICA", "CONE_BEAM_CBCT", "OCLUSAL", "FOTOGRAFIA_CLINICA"):
        assert api.post("/radiografias/", _rx(p, tipo_estudio=tipo)).status == 201, tipo
    assert api.post("/radiografias/", {"paciente_id": p, "titulo": "x"}).status == 422
    rx = api.post("/radiografias/", _rx(p)).json()
    assert api.get(f"/radiografias/{rx['id']}").ok
    assert any(r["registro_id"] == rx["id"] and r["accion"] == "VIEW" for r in fab.auditoria("radiografias_estudios"))
    assert fab.usuario("DOCTOR").api.delete(f"/radiografias/{rx['id']}").status == 403
    assert fab.usuario("ASISTENTE").api.delete(f"/radiografias/{rx['id']}").status == 403
    assert fab.usuario("RECEPCION").api.get("/radiografias/").status == 403
    assert api.delete(f"/radiografias/{rx['id']}").status == 204


@caso("RAD-04")
def test_url_javascript(fab, api):
    res = api.post("/radiografias/", _rx(fab.paciente()["id"], archivo_url="javascript:alert(1)"))
    assert res.status in (400, 422), f"Se aceptó una URL javascript: {res.status}"


@caso("RAD-14")
def test_radiografias_por_paciente(fab, api):
    a, b = fab.paciente()["id"], fab.paciente()["id"]
    rx = api.post("/radiografias/", _rx(a)).json()
    assert rx["id"] not in [r["id"] for r in api.get("/radiografias/", paciente_id=b).json()]


# ---------------- Prótesis ----------------

def _orden(p, doctor, **extra):
    return {"paciente_id": p, "doctor_id": doctor, "laboratorio_nombre": "Lab", "tipo_trabajo": "CORONA_ZIRCONIO", **extra}


@caso("PRO-01", "PRO-02", "PRO-03", "PRO-05", "PRO-06", "PRO-13", "PRO-14")
def test_ordenes_de_protesis(fab, api):
    p = fab.paciente()["id"]
    orden = api.post("/protesis/", _orden(p, fab.doctor, costo_laboratorio=50)).json()
    entrega = date.fromisoformat(orden["fecha_entrega_esperada"])
    assert (entrega - date.today()).days in (6, 7, 8)
    assert api.post("/protesis/", {"paciente_id": p}).status == 422
    for estado in ("EN_LABORATORIO", "RECIBIDO_EN_CLINICA", "PRUEBA_EN_BOCA", "AJUSTE_REPETICION", "INSTALADO_FINALIZADO"):
        assert api.put(f"/protesis/{orden['id']}", {"estado": estado}).json()["estado"] == estado
    assert api.put(f"/protesis/{orden['id']}", {"fecha_recepcion_real": date.today().isoformat()}).json()["fecha_recepcion_real"]
    assert api.post("/protesis/", _orden(p, fab.doctor, costo_laboratorio=-1)).status == 422
    assert api.post("/protesis/", _orden(p, fab.doctor, fecha_envio="2030-01-10", fecha_entrega_esperada="2030-01-05")).status == 400


@caso("PRO-08", "PRO-09", "PRO-10", "PRO-11", "PRO-12")
def test_permisos_de_protesis(fab, api):
    p = fab.paciente()["id"]
    doc, otro, asi, rec = fab.usuario("DOCTOR"), fab.usuario("DOCTOR"), fab.usuario("ASISTENTE"), fab.usuario("RECEPCION")
    assert doc.api.post("/protesis/", _orden(p, otro.doctor_id)).status == 403
    orden = doc.api.post("/protesis/", _orden(p, doc.doctor_id)).json()
    assert doc.api.put(f"/protesis/{orden['id']}", {"doctor_id": otro.doctor_id}).status == 403
    assert asi.api.post("/protesis/", _orden(p, doc.doctor_id)).status == 403 and asi.api.put(f"/protesis/{orden['id']}", {"estado": "EN_LABORATORIO"}).status == 403
    assert rec.api.put(f"/protesis/{orden['id']}", {"estado": "EN_LABORATORIO"}).ok
    assert rec.api.post("/protesis/", _orden(p, doc.doctor_id)).status == 403


# ---------------- Caja ----------------

@caso("CAJ-03", "CAJ-04", "CAJ-05", "CAJ-06", "CAJ-15", "CAJ-16", "CAJ-17", "CAJ-18", "CAJ-21", "CAJ-22", "CAJ-29")
def test_abrir_y_cerrar_caja(fab, api):
    fab.cerrar_caja()
    p = fab.paciente()["id"]
    res = api.post("/caja/pagos", {"paciente_id": p, "monto": 5, "metodo_pago": "EFECTIVO", "es_cobro_directo": True, "observaciones": "x"})
    assert res.status == 400 and "caja abierta" in res.detalle
    assert api.post("/caja/abrir", {"monto_inicial_fondo": -1}).status == 422
    res = [peticion for peticion in a_la_vez(lambda: peticion_directa("POST", "/caja/abrir", api.token, {"monto_inicial_fondo": 500}))]
    assert res.count(201) == 1 and set(res) <= {201, 400}, res
    assert sql("select count(*) from cajas_sesiones where estado='ABIERTA'") == "1"
    estado = api.get("/caja/estado").json()
    assert estado["saldo_en_gaveta"] == 500
    segunda = api.post("/caja/abrir", {"monto_inicial_fondo": 1})
    assert segunda.status == 400 and "ya existe" in segunda.detalle.lower()
    assert api.post("/caja/cerrar", {}).status == 400 and api.post("/caja/cerrar", {"total_efectivo_contado": -1}).status == 422
    cerrada = api.post("/caja/cerrar", {"total_efectivo_contado": 490}).json()
    assert float(cerrada["diferencia_descuadre"]) == -10 and cerrada["estado"] == "CERRADA"
    assert api.post("/caja/abrir", {"monto_inicial_fondo": 100}).status == 201
    assert api.get("/caja/estado").json()["movimientos"] == [], "Cada sesión tiene sus propios movimientos"
    sobrante = api.post("/caja/cerrar", {"total_efectivo_contado": 130}).json()
    assert float(sobrante["diferencia_descuadre"]) == 30
    assert len([r for r in fab.auditoria("cajas_sesiones") if r["seccion_consultada"] in ("APERTURA_CAJA", "CIERRE_CAJA")]) >= 4
    fab.caja()


@caso("CAJ-07", "CAJ-08", "CAJ-14")
def test_gaveta_segun_medio(fab):
    fab.caja()
    p = fab.paciente()["id"]
    antes = fab.gaveta()
    fab.cobro_directo(p, 50, "EFECTIVO")
    assert fab.gaveta() == antes + 50
    for metodo in ("TARJETA_DEBITO", "TARJETA_CREDITO", "TRANSFERENCIA"):
        fab.cobro_directo(p, 10, metodo)
    assert fab.gaveta() == antes + 50
    estado = fab.admin.get("/caja/estado").json()
    assert estado["ingresos_otros_medios"]["tarjeta_debito"] >= 10
    assert estado["fondo_inicial"] + estado["total_ingresos"] - estado["total_egresos"] == estado["saldo_en_gaveta"]


@caso("CAJ-30")
def test_movimientos_del_turno(fab, api):
    fab.caja()
    p = fab.paciente(nombres="Movimiento")["id"]
    cobro = fab.cobro_directo(p, 11.11, "TARJETA_DEBITO", referencia_comprobante="REC-MOV")
    anulado = fab.cobro_directo(p, 22.22, "TRANSFERENCIA")
    assert api.post(f"/caja/pagos/{anulado['id']}/anular", {"motivo": "Error"}).ok
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": 3.33, "concepto_motivo": "Egreso QA", "numero_recibo_comprobante": "EG-1"}).ok
    movimientos = api.get("/caja/estado").json()["movimientos"]
    assert movimientos[0]["tipo"] == "EGRESO" and movimientos[0]["concepto"] == "Egreso QA" and movimientos[0]["comprobante_numero"] == "EG-1"
    fila = next(m for m in movimientos if m["monto"] == 11.11)
    assert fila["tipo"] == "INGRESO" and "Movimiento" in fila["concepto"] and "Tarjeta de débito" in fila["concepto"] and fila["comprobante_numero"] == "REC-MOV"
    assert cobro["id"] and not [m for m in movimientos if m["monto"] == 22.22]
    assert "movimientos" not in fab.usuario("DOCTOR").api.get("/caja/estado").json()


@caso("CAJ-09", "CAJ-10", "CAJ-11", "CAJ-12", "CAJ-13")
def test_egresos(fab, api):
    fab.caja()
    antes = fab.gaveta()
    for categoria in ("COMPRA_INSUMOS", "PAGO_LABORATORIO_PROTESIS", "GASTO_OPERATIVO", "OTRO"):
        assert api.post("/caja/egresos", {"categoria": categoria, "monto": 1, "concepto_motivo": "x"}).status == 201
    assert fab.gaveta() == antes - 4
    res = api.post("/caja/egresos", {"categoria": "OTRO", "monto": antes * 10, "concepto_motivo": "x"})
    assert res.status == 400 and "efectivo suficiente" in res.detalle
    for monto in (0, -1, 1.001):
        assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": monto, "concepto_motivo": "x"}).status == 422
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": 1}).status == 422
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": fab.gaveta(), "concepto_motivo": "Todo"}).status == 201
    assert fab.gaveta() == 0
    fab.caja()


@caso("CAJ-19", "CAJ-20", "CAJ-26")
def test_caja_de_un_dia_anterior(fab, api):
    fab.caja()
    sql("update cajas_sesiones set fecha_apertura = fecha_apertura - interval '2 days' where estado='ABIERTA'")
    estado = api.get("/caja/estado").json()
    assert estado["tipo_bloqueo"] == "CIERRE_PENDIENTE_ANTERIOR" and estado["requiere_cierre_anterior"]
    res = api.post("/caja/abrir", {"monto_inicial_fondo": 1})
    assert res.status == 400 and "sin cerrar" in res.detalle
    fab.cerrar_caja()
    fab.caja()


@caso("CAJ-24", "CAJ-25")
def test_permisos_de_caja(fab):
    fab.caja()
    for rol in ("DOCTOR", "ASISTENTE"):
        u = fab.usuario(rol)
        estado = u.api.get("/caja/estado").json()
        assert "saldo_en_gaveta" not in estado and "fondo_inicial" not in estado
        assert u.api.post("/caja/abrir", {"monto_inicial_fondo": 1}).status == 403
        assert u.api.post("/caja/cerrar", {"total_efectivo_contado": 1}).status == 403
        assert u.api.post("/caja/egresos", {"categoria": "OTRO", "monto": 1, "concepto_motivo": "x"}).status == 403


# ---------------- Cobranzas ----------------

@caso("COB-01", "COB-02", "COB-03", "COB-04", "COB-05", "COB-06", "COB-18", "PAC-18")
def test_abonos_y_saldo(fab, api):
    p = fab.paciente()["id"]
    plan = fab.plan(p, 300)
    pagar = lambda monto, **extra: api.post("/caja/pagos", {"paciente_id": p, "plan_id": plan, "monto": monto, "metodo_pago": "TRANSFERENCIA", **extra})
    assert pagar(100).status == 201 and fab.saldo(p) == 200
    res = pagar(200.01)
    assert res.status == 400 and "supera el saldo" in res.detalle
    assert pagar(200).status == 201 and fab.saldo(p) == 0
    res = pagar(1)
    assert res.status == 400 and "no tiene saldo" in res.detalle
    otro = fab.paciente()["id"]
    propuesto = fab.plan(otro)
    res = api.post("/caja/pagos", {"paciente_id": otro, "plan_id": propuesto, "monto": 1, "metodo_pago": "TRANSFERENCIA"})
    assert res.status == 400 and "aprobado" in res.detalle
    res = api.post("/caja/pagos", {"paciente_id": otro, "plan_id": plan, "monto": 1, "metodo_pago": "TRANSFERENCIA"})
    assert res.status == 404 and "no pertenece" in res.detalle
    datos = api.get(f"/pacientes/{p}/saldo").json()
    assert datos["total_tratamientos"] - datos["total_pagado"] == datos["saldo_pendiente"]


@caso("COB-07", "COB-08", "COB-09", "COB-10", "COB-11", "COB-15", "COB-16", "E2E-04")
def test_cobro_directo(fab, api):
    p = fab.paciente()["id"]
    fab.caja()
    propuesta = fab.plan(p)
    fab.item(propuesta, fab.tratamiento()["id"], 500)
    base = {"paciente_id": p, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True, "observaciones": "Consulta"}
    for metodo in ("EFECTIVO", "TARJETA_DEBITO", "TARJETA_CREDITO", "TRANSFERENCIA", "OTRO"):
        res = api.post("/caja/pagos", {**base, "monto": 5, "metodo_pago": metodo, "referencia_comprobante": "REC-1"})
        assert res.status == 201 and res.json()["metodo_pago"] == metodo and res.json()["referencia_comprobante"] == "REC-1"
    assert fab.saldo(p) == 0, "Una consulta directa no genera ni reduce deuda, y el plan propuesto no cuenta"
    res = api.post("/caja/pagos", {**base, "monto": 5, "observaciones": "  "})
    assert res.status == 400 and "concepto" in res.detalle
    for monto in (0, -1, 1.001, 1e15):
        assert api.post("/caja/pagos", {**base, "monto": monto}).status == 422, monto
    assert api.post("/caja/pagos", {**base, "monto": 5, "doctor_comision_id": str(uuid4())}).status == 404
    pagos = api.get(f"/pacientes/{p}/saldo").json()["pagos"]
    assert len(pagos) >= 5


@caso("COB-13")
def test_cobros_simultaneos(fab, api):
    p = fab.paciente()["id"]
    plan = fab.plan(p, 100)
    res = a_la_vez(lambda: peticion_directa("POST", "/caja/pagos", api.token, {"paciente_id": p, "plan_id": plan, "monto": 60, "metodo_pago": "TRANSFERENCIA"}))
    assert res.count(201) == 1 and set(res) <= {201, 400}, res
    assert fab.saldo(p) == 40


@caso("COB-14", "COB-17")
def test_comision_y_permisos(fab, api):
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=40)
    fab.cobro_directo(fab.paciente()["id"], 1000, doctor_comision_id=doc.doctor_id)
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == 400
    assert doc.api.post("/caja/pagos", {}).status == 403 and fab.usuario("ASISTENTE").api.post("/caja/pagos", {}).status == 403


# ---------------- Anulación ----------------

@caso("ANU-01", "ANU-02", "ANU-06", "ANU-07", "ANU-08", "ANU-09", "ANU-14")
def test_anular_en_caja_abierta(fab, api):
    fab.caja()
    p = fab.paciente()["id"]
    plan = fab.plan(p, 500)
    gaveta = fab.gaveta()
    ingresos = float(api.get("/reportes/resumen-financiero").json()["total_ingresos"])
    efectivo = api.post("/caja/pagos", {"paciente_id": p, "plan_id": plan, "monto": 100, "metodo_pago": "EFECTIVO"}).json()
    tarjeta = api.post("/caja/pagos", {"paciente_id": p, "plan_id": plan, "monto": 50, "metodo_pago": "TARJETA_DEBITO"}).json()
    assert api.post(f"/caja/pagos/{efectivo['id']}/anular", {"motivo": " "}).status == 422
    anulado = api.post(f"/caja/pagos/{efectivo['id']}/anular", {"motivo": "Error"}).json()
    assert anulado["anulado"] and anulado["motivo_anulacion"] == "Error" and fab.gaveta() == gaveta
    res = api.post(f"/caja/pagos/{efectivo['id']}/anular", {"motivo": "Otra"})
    assert res.status == 409 and "ya fue anulado" in res.detalle
    assert api.post(f"/caja/pagos/{tarjeta['id']}/anular", {"motivo": "Error"}).ok
    assert fab.gaveta() == gaveta and fab.saldo(p) == 500
    assert float(api.get("/reportes/resumen-financiero").json()["total_ingresos"]) == ingresos
    assert any(r["registro_id"] == efectivo["id"] for r in fab.auditoria("pagos"))


@caso("ANU-03", "ANU-04", "ANU-05")
def test_anular_efectivo_de_caja_cerrada(fab, api):
    fab.caja()
    p = fab.paciente()["id"]
    pago = fab.cobro_directo(p, 100, "EFECTIVO")
    fab.cerrar_caja()
    sesion = sql(f"select caja_sesion_id from pagos where id = '{pago['id']}'")
    arqueo = f"select total_ingresos_efectivo||'/'||total_egresos_efectivo||'/'||diferencia_descuadre from cajas_sesiones where id = '{sesion}'"
    antes = sql(arqueo)
    res = api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error"})
    assert res.status == 400 and "abre la caja" in res.detalle
    assert api.post("/caja/abrir", {"monto_inicial_fondo": 10}).status == 201
    res = api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error"})
    assert res.status == 400 and "efectivo suficiente" in res.detalle
    fab.cerrar_caja()
    assert api.post("/caja/abrir", {"monto_inicial_fondo": 1000}).status == 201
    assert api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error"}).ok
    assert fab.gaveta() == 900
    assert sql(arqueo) == antes, "El arqueo anterior no cambia"


@caso("ANU-10", "ANU-11", "ANU-15")
def test_anular_cuenta_de_cita(fab, api):
    fab.caja()
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=50)
    p = fab.paciente()["id"]
    plan = fab.plan(p)
    item = fab.item(plan, fab.tratamiento()["id"], 200)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    cita = fab.cita(p, doctor=doc.doctor_id, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "doctor_comision_id": doc.doctor_id}).ok
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == 100
    pago = next(x for x in api.get(f"/pacientes/{p}/saldo").json()["pagos"])
    assert api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "Error"}).ok
    assert api.get(f"/cobros-cita/{cuenta['id']}").json()["estado"] == "PENDIENTE"
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["comision_bruta_generada"] == 0
    assert api.get(f"/tratamientos/planes/{plan}").json()["items"][0]["estado"] == "COMPLETADO"


@caso("ANU-12", "ANU-13")
def test_quien_puede_anular(fab, api):
    pago = fab.cobro_directo(fab.paciente()["id"], 10)
    assert fab.usuario("RECEPCION").api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "x"}).status == 403
    permiso = next(p["id"] for p in api.get("/usuarios/permisos").json() if p["codigo_permiso"] == "CAJA_ANULAR_PAGOS")
    rol = api.post("/usuarios/roles", {"nombre": f"Rol {uuid4().hex[:8]}", "permiso_ids": [permiso]}).json()["id"]
    assert fab.usuario(rol).api.post(f"/caja/pagos/{pago['id']}/anular", {"motivo": "x"}).ok


# ---------------- Cuenta de cita ----------------

def _cuenta(fab, api, costo=100, **cita):
    p = fab.paciente()["id"]
    plan = fab.plan(p)
    item = fab.item(plan, fab.tratamiento()["id"], costo)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    c = fab.cita(p, item_plan_id=item["id"], **cita).json()
    assert api.put(f"/citas/{c['id']}", {"estado": "FINALIZADA"}).ok
    return p, plan, item, next(x for x in api.get("/cobros-cita/").json() if x["cita_id"] == c["id"])


@caso("CCI-03", "CCI-04", "CCI-05", "CCI-08", "CCI-09", "CCI-16")
def test_editar_y_confirmar_cuenta(fab, api):
    fab.caja()
    p, _, _, cuenta = _cuenta(fab, api)
    linea = cuenta["lineas"][0]
    url = f"/cobros-cita/{cuenta['id']}"
    editada = api.put(url, {"lineas": [{"id": linea["id"], "concepto": "Editado", "monto": 90}, {"concepto": "Radiografía", "monto": 15}]}).json()
    assert float(editada["total"]) == 105 and editada["estado"] == "PENDIENTE"
    for mala in ({"concepto": "x", "monto": -1}, {"concepto": "x", "monto": 1.001}, {"concepto": "  ", "monto": 1}):
        assert api.put(url, {"lineas": [mala]}).status == 422, mala
    gaveta = fab.gaveta()
    assert api.post(f"{url}/confirmar", {"metodo_pago": "EFECTIVO"}).json()["estado"] == "PAGADO"
    assert fab.gaveta() == gaveta + 105
    res = api.put(url, {"lineas": [{"concepto": "x", "monto": 1}]})
    assert res.status == 409 and "ya fue cerrado" in res.detalle
    assert api.post(f"{url}/confirmar", {"metodo_pago": "EFECTIVO"}).status == 409
    _, _, _, otra = _cuenta(fab, api)
    gaveta = fab.gaveta()
    assert api.post(f"/cobros-cita/{otra['id']}/confirmar", {"metodo_pago": "TARJETA_CREDITO"}).ok and fab.gaveta() == gaveta


@caso("CCI-06", "CCI-07", "E2E-03")
def test_tratamiento_en_varias_citas(fab, api):
    p = fab.paciente()["id"]
    plan = fab.plan(p)
    item = fab.item(plan, fab.tratamiento()["id"], 200)
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    assert api.post("/caja/pagos", {"paciente_id": p, "plan_id": plan, "monto": 150, "metodo_pago": "TRANSFERENCIA"}).ok
    primera = fab.cita(p, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{primera['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(x for x in api.get("/cobros-cita/").json() if x["cita_id"] == primera["id"])
    assert float(cuenta["total"]) == 50 and float(cuenta["lineas"][0]["costo_referencia"]) == 200
    segunda = fab.cita(p, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{segunda['id']}", {"estado": "FINALIZADA"}).ok
    repetida = next(x for x in api.get("/cobros-cita/").json() if x["cita_id"] == segunda["id"])
    assert not [l for l in repetida["lineas"] if l.get("item_plan_id") == item["id"]], "No se cobra dos veces"


@caso("CCI-10")
def test_lineas_de_plan_y_directas(fab, api):
    fab.caja()
    p, plan, _, cuenta = _cuenta(fab, api, 100)
    linea = cuenta["lineas"][0]
    url = f"/cobros-cita/{cuenta['id']}"
    assert api.put(url, {"lineas": [{"id": linea["id"], "concepto": linea["concepto"], "monto": 100}, {"concepto": "Extra", "monto": 20}]}).ok
    assert api.post(f"{url}/confirmar", {"metodo_pago": "TRANSFERENCIA"}).ok
    assert fab.saldo(p) == 0
    pagos = api.get(f"/pacientes/{p}/saldo").json()["pagos"]
    assert sorted(float(x["monto"]) for x in pagos) == [20, 100]


@caso("CCI-11", "CCI-12", "CCI-13", "CCI-14", "CCI-15")
def test_casos_limite_de_cuenta(fab, api):
    fab.caja()
    p = fab.paciente()["id"]
    cita = fab.cita(p).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    cero = next(x for x in api.get("/cobros-cita/").json() if x["cita_id"] == cita["id"])
    res = api.post(f"/cobros-cita/{cero['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA"})
    assert res.status == 400 and "cierra el cobro sin pago" in res.detalle
    assert api.post(f"/cobros-cita/{cero['id']}/cerrar-sin-pago", {"motivo": " "}).status == 422
    assert api.post(f"/cobros-cita/{cero['id']}/cerrar-sin-pago", {"motivo": "Cortesía"}).json()["estado"] == "ANULADO"
    _, _, _, cuenta = _cuenta(fab, api, 100)
    linea = cuenta["lineas"][0]
    res = api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "lineas": [{"id": linea["id"], "concepto": linea["concepto"], "monto": 150}]})
    assert res.status == 400 and "supera" in res.detalle
    fab.cerrar_caja()
    res = api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "EFECTIVO"})
    assert res.status == 400 and "caja abierta" in res.detalle
    fab.caja()
    assert {"COBRO_CITA_CREADO", "COBRO_CITA_SIN_PAGO"} <= {r["seccion_consultada"] for r in fab.auditoria("cobros_cita")}


@caso("CCI-17")
def test_confirmar_a_la_vez(fab, api):
    p, _, _, cuenta = _cuenta(fab, api, 100)
    res = a_la_vez(lambda: peticion_directa("POST", f"/cobros-cita/{cuenta['id']}/confirmar", api.token, {"metodo_pago": "TRANSFERENCIA"}))
    assert res.count(200) == 1 and set(res) <= {200, 400, 409}, res
    assert len(api.get(f"/pacientes/{p}/saldo").json()["pagos"]) == 1


# ---------------- Nómina ----------------

def _pagar(api, uid, tipo, neto, metodo="TRANSFERENCIA", **extra):
    return api.post("/empleados/pagos", {"usuario_empleado_id": uid, "tipo_pago": tipo, "monto_neto_pagado": neto, "metodo_pago": metodo, **extra})


@caso("NOM-01", "NOM-02", "NOM-03")
def test_personal_y_contratos(fab, api):
    u = fab.usuario("RECEPCION")
    lista = {p["usuario_id"]: p for p in api.get("/empleados/personal").json()}
    assert lista[u.id]["contrato"] is None
    contrato = api.post("/personal/contratos", {"usuario_id": u.id, "salario_base": 3000}).json()
    assert api.get(f"/empleados/liquidacion/{u.id}").json()["salario_base"] == 3000
    assert api.put(f"/personal/contratos/{contrato['id']}", {"salario_base": 3500}).ok
    assert api.get(f"/empleados/liquidacion/{u.id}").json()["salario_base"] == 3500
    assert api.put(f"/personal/contratos/{contrato['id']}", {"porcentaje_comision": 101}).status == 422
    assert api.put(f"/personal/contratos/{contrato['id']}", {"salario_base": -1}).status == 422


@caso("NOM-04", "NOM-05", "NOM-06", "NOM-07", "NOM-08", "NOM-09", "NOM-10", "NOM-11", "COB-14")
def test_comisiones(fab, api):
    doc = fab.usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=40)
    liq = lambda: api.get(f"/empleados/liquidacion/{doc.id}").json()
    p = fab.paciente()["id"]
    cobro = fab.cobro_directo(p, 1000, doctor_comision_id=doc.doctor_id)
    assert liq()["comision_bruta_generada"] == 400
    contrato = next(c for c in api.get("/personal/contratos").json() if c["usuario_id"] == doc.id)
    assert api.put(f"/personal/contratos/{contrato['id']}", {"porcentaje_comision": 10}).ok
    assert liq()["comision_bruta_generada"] == 400
    fab.cobro_directo(p, 1000, doctor_comision_id=doc.doctor_id)
    assert liq()["comision_bruta_generada"] == 500
    res = _pagar(api, doc.id, "COMISION_TRATAMIENTOS", 500.01)
    assert res.status == 400 and "no puede superar" in res.detalle
    assert _pagar(api, doc.id, "COMISION_TRATAMIENTOS", 100).status == 201
    assert _pagar(api, doc.id, "ADELANTO", 50).status == 201
    assert liq()["saldo_comision_por_pagar"] == 350
    assert _pagar(api, doc.id, "COMISION_TRATAMIENTOS", 350).status == 201
    assert api.post(f"/caja/pagos/{cobro['id']}/anular", {"motivo": "Error"}).ok
    assert liq()["saldo_comision_por_pagar"] == -400
    assert _pagar(api, doc.id, "COMISION_TRATAMIENTOS", 1).status == 400
    fab.cobro_directo(p, 6000, doctor_comision_id=doc.doctor_id)
    assert liq()["saldo_comision_por_pagar"] == 200

    sin = fab.usuario("DOCTOR")
    fab.cobro_directo(p, 1000, doctor_comision_id=sin.doctor_id)
    assert api.post("/personal/contratos", {"usuario_id": sin.id, "porcentaje_comision": 50}).status == 201
    assert api.get(f"/empleados/liquidacion/{sin.id}").json()["comision_bruta_generada"] == 0


@caso("NOM-12", "NOM-13", "NOM-14", "NOM-15", "NOM-16", "NOM-19", "NOM-22", "NOM-23")
def test_sueldo_y_adelantos(fab, api):
    fab.caja()
    u = fab.usuario("RECEPCION", salario_base=3000)
    liq = lambda: api.get(f"/empleados/liquidacion/{u.id}").json()
    gaveta = fab.gaveta()
    assert _pagar(api, u.id, "ADELANTO", 500, "EFECTIVO_CAJA").status == 201
    assert fab.gaveta() == gaveta - 500 and liq()["total_anticipos"] == 500
    assert _pagar(api, u.id, "SUELDO_MENSUAL", 2400, monto_base=3000, deducciones_descuentos=600).status == 400
    assert _pagar(api, u.id, "SUELDO_MENSUAL", 2500, monto_base=3000, deducciones_descuentos=400).status == 422
    assert _pagar(api, u.id, "BONO", 10, deducciones_descuentos=1).status == 422
    assert _pagar(api, u.id, "SUELDO_MENSUAL", 2500, monto_base=3000, deducciones_descuentos=500).status == 201
    assert liq()["total_anticipos"] == 0
    gaveta = fab.gaveta()
    assert _pagar(api, u.id, "BONO", 10).status == 201 and fab.gaveta() == gaveta
    assert _pagar(api, u.id, "ADELANTO", 0).status == 422
    assert _pagar(api, u.id, "ADELANTO", 1000).status == 201
    assert _pagar(api, u.id, "SUELDO_MENSUAL", 0, "EFECTIVO_CAJA", monto_base=1000, deducciones_descuentos=1000).status == 201
    assert fab.gaveta() == gaveta and liq()["total_anticipos"] == 0


@caso("NOM-18")
def test_contrato_mixto(fab, api):
    doc = fab.usuario("DOCTOR", tipo_remuneracion="MIXTO_BASE_MAS_COMISION", porcentaje_comision=40, salario_base=2000)
    fab.cobro_directo(fab.paciente()["id"], 1000, doctor_comision_id=doc.doctor_id)
    assert _pagar(api, doc.id, "ADELANTO", 100).status == 201
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["saldo_comision_por_pagar"] == 300
    assert _pagar(api, doc.id, "SUELDO_MENSUAL", 1900, monto_base=2000, deducciones_descuentos=100).status == 201
    assert api.get(f"/empleados/liquidacion/{doc.id}").json()["saldo_comision_por_pagar"] == 400


@caso("NOM-20", "NOM-21")
def test_nomina_y_gaveta(fab, api):
    fab.caja()
    u = fab.usuario()
    res = _pagar(api, u.id, "BONO", fab.gaveta() + 1, "EFECTIVO_CAJA")
    assert res.status == 400 and "efectivo suficiente" in res.detalle
    fab.cerrar_caja()
    res = _pagar(api, u.id, "BONO", 1, "EFECTIVO_CAJA")
    assert res.status == 400 and "caja abierta" in res.detalle
    fab.caja()


@caso("NOM-25", "NOM-27", "NOM-29")
def test_privacidad_de_nomina(fab, api):
    doc, otro = fab.usuario("DOCTOR"), fab.usuario("RECEPCION")
    assert doc.api.get(f"/empleados/liquidacion/{otro.id}").status == 403
    assert [p["usuario_id"] for p in doc.api.get("/empleados/personal").json()] == [doc.id]
    assert fab.usuario("RECEPCION").api.post("/personal/contratos", {"usuario_id": doc.id}).status == 403
    assert _pagar(api, doc.id, "BONO", 1, "INVENTADO").status == 422


# ---------------- Asistencia ----------------

def _estado(u):
    return u.api.get("/auth/fichaje/estado").json()


def _marcar(u, tipo, **extra):
    return u.api.post("/auth/fichar", {"tipo_evento": tipo, **extra})


TODOS = {"ENTRADA", "INICIO_DESCANSO", "FIN_DESCANSO", "SALIDA"}


@caso("ASI-01", "ASI-02", "ASI-03", "ASI-04", "ASI-05", "ASI-06", "ASI-08")
def test_recorrido_de_turno(fab):
    u = fab.usuario()
    pasos = [("SIN_TURNO", {"ENTRADA"}, "ENTRADA"), ("EN_TURNO", {"INICIO_DESCANSO", "SALIDA"}, "INICIO_DESCANSO"),
             ("EN_DESCANSO", {"FIN_DESCANSO"}, "FIN_DESCANSO"), ("EN_TURNO", {"INICIO_DESCANSO", "SALIDA"}, "SALIDA"),
             ("TURNO_CERRADO", {"ENTRADA"}, "ENTRADA")]
    for estado, permitidos, siguiente in pasos:
        datos = _estado(u)
        assert datos["estado"] == estado and set(datos["permitidos"]) == permitidos, datos
        for tipo in TODOS - permitidos:
            assert _marcar(u, tipo).status == 409, f"{estado} {tipo}"
        assert _marcar(u, siguiente).ok


@caso("ASI-09")
def test_marcajes_simultaneos(fab):
    u = fab.usuario()
    res = a_la_vez(lambda: peticion_directa("POST", "/auth/fichar", u.api.token, {"tipo_evento": "ENTRADA"}))
    assert res.count(200) == 1 and set(res) <= {200, 409}, res


@caso("ASI-12", "ASI-17", "ASI-18")
def test_turnos_por_persona(fab, api):
    a, b = fab.usuario(), fab.usuario()
    assert _marcar(a, "ENTRADA", observaciones="Nota").json()["observaciones"] == "Nota"
    assert _estado(b)["estado"] == "SIN_TURNO"
    assert {r["usuario_id"] for r in a.api.get("/personal/asistencia", usuario_id=b.id).json()} <= {a.id}


@caso("ASI-13", "COR-01", "COR-03", "COR-04", "COR-17", "COR-18")
def test_salida_olvidada_y_correccion(fab, api):
    u = fab.usuario()
    entrada = _marcar(u, "ENTRADA").json()
    sql(f"update registro_asistencia set fecha_hora = fecha_hora - interval '1 day' where usuario_id = '{u.id}'")
    assert _estado(u)["estado"] == "SIN_TURNO" and _estado(u)["jornada_sin_salida"]
    pendiente = next(j for j in api.get("/personal/asistencia/jornadas-sin-salida").json() if j["usuario_id"] == u.id)
    assert pendiente["ultimo_evento"] == "ENTRADA"
    original = api.get("/personal/asistencia", usuario_id=u.id).json()[0]
    salida = datetime.fromisoformat(original["fecha_hora"]) + timedelta(minutes=5)
    corregido = api.post("/personal/asistencia/correcciones", {"usuario_id": u.id, "tipo_evento": "SALIDA", "fecha_hora": salida.isoformat(), "motivo": "Olvido"}).json()
    assert corregido["es_correccion"] and corregido["motivo_correccion"] == "Olvido" and corregido["corregido_por_nombre"] and corregido["ip_registro"] is None
    assert _estado(u)["jornada_sin_salida"] is None
    assert u.id not in [j["usuario_id"] for j in api.get("/personal/asistencia/jornadas-sin-salida").json()]
    assert next(r for r in api.get("/personal/asistencia", usuario_id=u.id).json() if r["id"] == entrada["id"])["fecha_hora"] == original["fecha_hora"]
    assert any(r["seccion_consultada"] == "CORRECCION_MARCAJE" and r["datos_nuevos"]["motivo"] == "Olvido" for r in fab.auditoria("registro_asistencia"))


@caso("COR-05", "COR-06", "COR-07", "COR-08", "COR-16")
def test_validaciones_de_correccion(fab, api):
    u = fab.usuario()
    ahora = datetime.now(timezone.utc)
    url = "/personal/asistencia/correcciones"
    cuerpo = {"usuario_id": u.id, "tipo_evento": "ENTRADA", "fecha_hora": (ahora - timedelta(seconds=30)).isoformat(), "motivo": "Olvido"}
    assert api.post(url, {**cuerpo, "motivo": "  "}).status == 422
    assert api.post(url, {**cuerpo, "fecha_hora": "2030-01-01T08:00:00"}).status == 422
    assert api.post(url, {**cuerpo, "fecha_hora": (ahora + timedelta(hours=1)).isoformat()}).status == 400
    assert u.api.post(url, cuerpo).status == 403 and u.api.get("/personal/asistencia/jornadas-sin-salida").status == 403
    assert api.post(url, cuerpo).status == 201
    assert _estado(u)["estado"] == "EN_TURNO"
    res = api.post(url, {**cuerpo, "fecha_hora": (ahora - timedelta(seconds=10)).isoformat()})
    assert res.status == 409 and "después de una entrada" in res.detalle


@caso("COR-09", "COR-10", "COR-11")
def test_descanso_en_turno_cerrado(fab, api):
    u = fab.usuario()
    _marcar(u, "ENTRADA")
    _marcar(u, "SALIDA")
    salida, entrada = api.get("/personal/asistencia", usuario_id=u.id).json()
    a, b = datetime.fromisoformat(entrada["fecha_hora"]), datetime.fromisoformat(salida["fecha_hora"])
    uno, dos = a + (b - a) / 3, a + 2 * (b - a) / 3
    base = {"usuario_id": u.id, "tipo_evento": "INICIO_DESCANSO", "motivo": "Olvido"}
    url = "/personal/asistencia/correcciones"
    assert api.post(url, {**base, "fecha_hora": uno.isoformat()}).status == 409
    assert api.post(url, {**base, "fecha_hora": dos.isoformat(), "fecha_hora_fin": uno.isoformat()}).status == 422
    assert api.post(url, {**base, "fecha_hora": uno.isoformat(), "fecha_hora_fin": (b + timedelta(milliseconds=1)).isoformat()}).status in (400, 409)
    assert api.post(url, {**base, "fecha_hora": uno.isoformat(), "fecha_hora_fin": dos.isoformat()}).status == 201
    assert [r["tipo_evento"] for r in api.get("/personal/asistencia", usuario_id=u.id).json()] == ["SALIDA", "FIN_DESCANSO", "INICIO_DESCANSO", "ENTRADA"]


@caso("COR-12", "COR-13", "COR-14", "COR-15")
def test_anular_marcaje(fab, api):
    u = fab.usuario()
    entrada = _marcar(u, "ENTRADA").json()
    salida = _marcar(u, "SALIDA").json()
    url = f"/personal/asistencia/{salida['id']}/anular"
    assert u.api.post(url, {"motivo": "x"}).status == 403
    datos = api.post(url, {"motivo": "Por error"}).json()
    assert datos["anulado"] and datos["motivo_anulacion"] == "Por error" and datos["anulado_por_nombre"]
    assert _estado(u)["estado"] == "EN_TURNO"
    assert api.post(url, {"motivo": "Otra"}).status == 409
    assert len(api.get("/personal/asistencia", usuario_id=u.id).json()) == 2
    _marcar(u, "SALIDA")
    res = api.post(f"/personal/asistencia/{entrada['id']}/anular", {"motivo": "x"})
    assert res.status == 409 and "posteriores" in res.detalle


# ---------------- Reportes y auditoría ----------------

def _rango(dia, hasta=None):
    return {"fecha_desde": f"{dia}T00:00:00Z", "fecha_hasta": f"{hasta or dia}T23:59:59Z"}


@caso("REP-07", "REP-08", "REP-09", "REP-10", "AGE-24")
def test_reportes_de_citas(fab, api):
    t = fab.tratamiento()
    doc = fab.usuario("DOCTOR")
    p = fab.paciente()["id"]
    dia = dia_libre()
    plan = fab.plan(p)
    a, b = fab.item(plan, t["id"], 10), fab.item(plan, t["id"], 10)
    uno = fab.cita(p, dia, "08:00", "08:30", doctor=doc.doctor_id, item_plan_id=a["id"]).json()
    dos = fab.cita(p, dia, "09:00", "09:30", doctor=doc.doctor_id, item_plan_id=b["id"]).json()
    tres = fab.cita(p, dia, "10:00", "10:30", doctor=doc.doctor_id).json()
    cuatro = fab.cita(p, dia, "11:00", "11:30", doctor=doc.doctor_id).json()
    assert api.patch(f"/citas/{uno['id']}/sillon", {"hora_inicio_sillon": f"{dia}T08:00:00Z", "hora_fin_sillon": f"{dia}T08:40:00Z", "estado": "FINALIZADA"}).ok
    assert api.put(f"/citas/{dos['id']}", {"estado": "FINALIZADA"}).ok
    assert api.put(f"/citas/{tres['id']}", {"estado": "NO_ASISTIO"}).ok
    assert api.delete(f"/citas/{cuatro['id']}").status == 204
    demanda = api.get("/reportes/tratamientos-demanda", limit=1000, **_rango(dia)).json()["ranking_tratamientos"]
    assert next(x for x in demanda if x["tratamiento_id"] == t["id"])["cantidad_realizada"] == 2
    datos = api.get("/reportes/productividad-doctores", doctor_id=doc.doctor_id, **_rango(dia)).json()["doctores"][0]
    assert (datos["total_citas"], datos["citas_finalizadas"], datos["citas_no_asistio"], datos["citas_canceladas"]) == (4, 2, 1, 1)
    assert datos["tiempo_total_sillon_minutos"] == 40 and datos["promedio_minutos_por_cita"] == 40 and datos["tasa_ausentismo_porcentaje"] == 25


@caso("REP-11", "REP-12", "REP-13")
def test_resumen_financiero(fab, api):
    fab.caja()
    hoy = ahora_clinica().date()
    rango = {"fecha_desde": f"{hoy - timedelta(days=1)}T00:00:00Z", "fecha_hasta": f"{hoy + timedelta(days=2)}T00:00:00Z"}
    r = lambda: api.get("/reportes/resumen-financiero", **rango).json()
    antes = r()
    p = fab.paciente()["id"]
    fab.cobro_directo(p, 100, "EFECTIVO")
    fab.cobro_directo(p, 50, "TARJETA_DEBITO")
    anulado = fab.cobro_directo(p, 999, "TRANSFERENCIA")
    assert api.post(f"/caja/pagos/{anulado['id']}/anular", {"motivo": "Error"}).ok
    assert api.post("/caja/egresos", {"categoria": "COMPRA_INSUMOS", "monto": 30, "concepto_motivo": "x"}).ok
    assert api.post("/empleados/pagos", {"usuario_empleado_id": fab.usuario().id, "tipo_pago": "BONO", "monto_neto_pagado": 20, "metodo_pago": "EFECTIVO_CAJA"}).ok
    despues = r()
    assert float(despues["total_ingresos"]) == float(antes["total_ingresos"]) + 150, "Suma los medios, sin anulados"
    assert float(despues["total_egresos"]) == float(antes["total_egresos"]) + 50, "Incluye gastos y nómina"
    # La devolución de un pago de una caja ya cerrada no es un egreso
    cerrado = fab.cobro_directo(p, 40, "EFECTIVO")
    fab.cerrar_caja()
    fab.caja()
    previo = r()
    assert api.post(f"/caja/pagos/{cerrado['id']}/anular", {"motivo": "Error"}).ok
    tras_devolver = r()
    assert float(tras_devolver["total_egresos"]) == float(previo["total_egresos"]), "La devolución no cuenta como egreso"
    assert float(tras_devolver["total_ingresos"]) == float(previo["total_ingresos"]) - 40
    assert float(despues["balance_neto_operativo"]) == float(despues["total_ingresos"]) - float(despues["total_egresos"])


@caso("REP-17")
def test_reportes_solo_con_permiso(fab):
    for rol in ("DOCTOR", "ASISTENTE", "RECEPCION"):
        u = fab.usuario(rol)
        for ruta in ("/reportes/resumen-financiero", "/reportes/tratamientos-demanda", "/reportes/productividad-doctores", "/reportes/graficos/tratamientos-demanda", "/reportes/graficos/productividad-doctores"):
            assert u.api.get(ruta).status == 403, f"{rol} {ruta}"


@caso("AUD-03", "AUD-04", "AUD-06", "AUD-07", "AUD-08")
def test_auditoria(fab, api):
    registros = api.get("/auditoria/", limit=500).json()
    assert registros
    assert all(r.get("accion") and r.get("tabla_afectada") for r in registros)
    assert "$2b$" not in str(registros) and "Prueba1234" not in str(registros)
    assert {"pagos", "catalogo_tratamientos", "registro_asistencia"} <= {r["tabla_afectada"] for r in api.get("/auditoria/", limit=5000).json()}
    uno = registros[0]["id"]
    assert api.put(f"/auditoria/{uno}", {}).status in (404, 405) and api.delete(f"/auditoria/{uno}").status in (404, 405)
    for rol in ("DOCTOR", "RECEPCION"):
        assert fab.usuario(rol).api.get("/auditoria/").status == 403


# ---------------- Sillones ----------------

@caso("SIL-01", "SIL-02", "SIL-04", "SIL-05", "SIL-06", "SIL-08", "SIL-09", "SIL-10")
def test_sillones(fab, api):
    uno = api.post("/sillones/", {"nombre": "Sala QA", "especialidad": "General"}).json()
    sin_nombre = api.post("/sillones/", {}).json()
    assert sin_nombre["nombre"] == f"Box {sin_nombre['numero']}"
    assert api.put(f"/sillones/{uno['id']}", {"nombre": "Sala Editada"}).json()["nombre"] == "Sala Editada"
    p = fab.paciente()["id"]
    cita = fab.cita(p, box=uno["numero"]).json()
    res = api.delete(f"/sillones/{uno['id']}")
    assert res.status == 409 and "cita(s) por atender" in res.detalle
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    assert api.delete(f"/sillones/{uno['id']}").json()["resultado"] == "DESACTIVADO"
    assert api.put(f"/sillones/{uno['id']}", {"activo": True}).json()["activo"] is True
    alto = api.post("/sillones/", {}).json()
    numero = sin_nombre["numero"]
    assert api.delete(f"/sillones/{sin_nombre['id']}").json()["resultado"] == "ELIMINADO"
    otro = api.post("/sillones/", {}).json()
    assert otro["numero"] not in (numero, alto["numero"]), "El número de un sillón intermedio no se reutiliza"
    for sobrante in (alto, otro):
        assert api.delete(f"/sillones/{sobrante['id']}").ok
    assert fab.usuario("RECEPCION").api.post("/sillones/", {}).status == 403


@caso("SIL-07")
def test_ultimo_sillon(fab, api):
    # Otras pruebas dejan citas pendientes en los demás sillones: se apartan directamente en la base
    activos = [s for s in api.get("/sillones/").json() if s["activo"]]
    otros = ",".join(f"'{s['id']}'" for s in activos[1:])
    sql(f"update sillones set activo = false where id in ({otros})")
    try:
        res = api.put(f"/sillones/{activos[0]['id']}", {"activo": False})
        assert res.status == 400 and "al menos un sillón" in res.detalle
    finally:
        sql(f"update sillones set activo = true where id in ({otros})")


# ---------------- Configuración ----------------

PNG = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64


@caso("CFG-03", "CFG-17", "CFG-18", "CFG-19", "CFG-20", "CFG-21", "AUD-05")
def test_configuracion(fab, api, sin_sesion):
    original = api.get("/configuracion/").json()
    try:
        assert api.put("/configuracion/", {"nombre_clinica": "  "}).status == 422 and api.put("/configuracion/", {"nombre_clinica": "x" * 121}).status == 422
        for malo in ("", "Bs1", "123456789"):
            assert api.put("/configuracion/", {"moneda_simbolo": malo}).status == 422, malo
        pago = fab.cobro_directo(fab.paciente()["id"], 123.45)
        assert api.put("/configuracion/", {"moneda_simbolo": "Bs."}).ok
        res = api.post("/caja/egresos", {"categoria": "OTRO", "monto": 99999999, "concepto_motivo": "x"})
        assert "Bs. 99.999.999,00" in res.detalle and "$" not in res.detalle
        assert float(pago["monto"]) == 123.45
        publica = sin_sesion.get("/configuracion/publica").text
        assert "moneda_simbolo" not in publica
        assert fab.usuario("DOCTOR").api.put("/configuracion/", {"moneda_simbolo": "€"}).status == 403
        assert any(r["seccion_consultada"] == "CONFIGURACION_CLINICA" for r in fab.auditoria("configuracion_clinica"))
    finally:
        assert api.put("/configuracion/", {"moneda_simbolo": original["moneda_simbolo"], "nombre_clinica": original["nombre_clinica"]}).ok
