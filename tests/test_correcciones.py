"""
Pruebas de regresión de los errores corregidos en agenda, odontograma, saldos, caja,
nómina y reportes. Escriben datos y cierran la caja abierta: ejecutar contra una base de pruebas.
"""
import itertools
import os
import random
import sys
from datetime import date, timedelta
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API = "/api/v1"


_siguiente_dia = itertools.count(random.randint(0, 20000))


def _dia_unico():
    """Las suites comparten doctor y base: un día repetido chocaría con otra cita."""
    return date(2600, 1, 1) + timedelta(days=next(_siguiente_dia))


def _login():
    res = client.post(f"{API}/auth/login", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


H = _login()


def _crear_paciente():
    res = client.post(f"{API}/pacientes/", json={
        "nombres": "Regresion",
        "apellidos": "Pruebas",
        "tipo_documento": "CI",
        "numero_documento": f"REG-{uuid4().hex[:10]}",
        "genero": "OTRO",
        "fecha_nacimiento": "1990-01-01",
        "telefono": "70000000",
    }, headers=H)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _doctor():
    return client.get(f"{API}/usuarios/doctores/lista", headers=H).json()[0]


def _crear_tratamiento(nombre, categoria):
    res = client.post(f"{API}/tratamientos/catalogo", json={
        "codigo": f"R-{uuid4().hex[:10]}",
        "categoria": categoria,
        "nombre": nombre,
        "costo_base": 100,
        "duracion_estimada_min": 30,
    }, headers=H)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _dia_libre():
    return _dia_unico()


def _cita(paciente_id, doctor_id, dia, inicio, fin, **extra):
    return client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "fecha_inicio_programada": f"{dia}T{inicio}:00Z",
        "fecha_fin_programada": f"{dia}T{fin}:00Z",
        "motivo_consulta": "Prueba de agenda",
        **extra,
    }, headers=H)


def _asegurar_caja(abierta):
    estado = client.get(f"{API}/caja/estado", headers=H).json()
    if estado["caja_abierta"] and not abierta:
        res = client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": estado["saldo_en_gaveta"]}, headers=H)
        assert res.status_code == 200, res.text
    if abierta and not estado["caja_abierta"]:
        res = client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H)
        assert res.status_code == 201, res.text


def test_agenda():
    paciente_id, doctor_id, dia = _crear_paciente(), _doctor()["id"], _dia_libre()

    assert _cita(paciente_id, doctor_id, dia, "11:00", "10:00").status_code == 400
    assert _cita(paciente_id, doctor_id, dia, "10:00", "10:00").status_code == 400
    assert client.post(f"{API}/citas/", json={"paciente_id": paciente_id, "doctor_id": doctor_id}, headers=H).status_code == 400

    primera = _cita(paciente_id, doctor_id, dia, "10:00", "11:00")
    assert primera.status_code == 201, primera.text
    cita_id = primera.json()["id"]

    assert _cita(paciente_id, doctor_id, dia, "10:30", "11:30").status_code == 409
    contigua = _cita(paciente_id, doctor_id, dia, "11:00", "12:00")
    assert contigua.status_code == 201, "Una cita contigua no es una superposición"

    # Mover una cita sobre otra también se rechaza y no deja cambios guardados
    mover = client.put(f"{API}/citas/{contigua.json()['id']}", json={"fecha_inicio_programada": f"{dia}T10:30:00Z"}, headers=H)
    assert mover.status_code == 409

    # Cambiar solo el estado no vuelve a validar el horario
    estado = client.put(f"{API}/citas/{cita_id}", json={"estado": "CONFIRMADA"}, headers=H)
    assert estado.status_code == 200, estado.text

    # Cancelar conserva el registro y libera el horario
    assert client.delete(f"{API}/citas/{cita_id}", headers=H).status_code == 204
    citas = client.get(f"{API}/citas/?paciente_id={paciente_id}&estado=CANCELADA", headers=H).json()
    assert [c["id"] for c in citas] == [cita_id]
    nueva = _cita(paciente_id, doctor_id, dia, "10:00", "11:00")
    assert nueva.status_code == 201, "Una cita cancelada no debe ocupar el horario"

    # Reactivar la cancelada sobre un horario ya ocupado se rechaza
    assert client.put(f"{API}/citas/{cita_id}", json={"estado": "PROGRAMADA"}, headers=H).status_code == 409

    # Una cita atendida no se puede cancelar
    fin = client.put(f"{API}/citas/{nueva.json()['id']}", json={"estado": "FINALIZADA"}, headers=H)
    assert fin.status_code == 200, fin.text
    assert client.delete(f"{API}/citas/{nueva.json()['id']}", headers=H).status_code == 400
    print("✔ Agenda: horario válido, sin doble reserva y cancelación sin borrado.")


def _odontograma_con_caries(paciente_id, fdi):
    res = client.post(f"{API}/odontogramas/", json={
        "paciente_id": paciente_id,
        "tipo_denticion": "ADULTA_PERMANENTE",
        "tipo_registro": "INICIAL_INGRESO",
    }, headers=H)
    assert res.status_code == 201, res.text
    res_h = client.post(f"{API}/odontogramas/hallazgos", json={
        "odontograma_id": res.json()["id"],
        "pieza_fdi": fdi,
        "superficie": "OCLUSAL_INCISAL",
        "condicion": "CARIES",
        "estado_clinico": "REQUERIDO_PATOLOGIA",
        "color_hex": "#EF4444",
    }, headers=H)
    assert res_h.status_code == 201, res_h.text
    return res.json()["id"]


def _realizar(paciente_id, doctor_id, tratamiento_id, fdi, superficie):
    plan = client.post(f"{API}/tratamientos/planes", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "titulo": "Plan regresión", "items": [],
    }, headers=H)
    assert plan.status_code == 201, plan.text
    item = client.post(f"{API}/tratamientos/items", json={
        "plan_id": plan.json()["id"],
        "tratamiento_id": tratamiento_id,
        "pieza_fdi": fdi,
        "superficie": superficie,
        "costo_acordado": 100,
    }, headers=H)
    assert item.status_code == 201, item.text
    cita = _cita(paciente_id, doctor_id, _dia_libre(), "09:00", "10:00", item_plan_id=item.json()["id"])
    assert cita.status_code == 201, cita.text
    res = client.put(f"{API}/citas/{cita.json()['id']}", json={"estado": "FINALIZADA"}, headers=H)
    assert res.status_code == 200, res.text
    return item.json()["id"]


def _pieza(odontograma_id, fdi):
    data = client.get(f"{API}/odontogramas/{odontograma_id}", headers=H).json()
    return next(p for p in data["piezas"] if p["numero_fdi"] == fdi)


def _evolucion(paciente_id):
    res = client.get(f"{API}/odontogramas/?paciente_id={paciente_id}&tipo_registro=EVOLUCION_ACTUAL", headers=H).json()
    assert len(res) == 1, "Debe existir un único odontograma de evolución"
    return res[0]["id"]


def test_odontograma():
    doctor_id = _doctor()["id"]

    # Endodoncia: registra la condición real y no altera el diagnóstico inicial
    paciente_id = _crear_paciente()
    inicial_id = _odontograma_con_caries(paciente_id, 16)
    endo = _crear_tratamiento("Endodoncia molar", "ENDODONCIA")
    _realizar(paciente_id, doctor_id, endo, 16, "OCLUSAL_INCISAL")

    inicial = _pieza(inicial_id, 16)["hallazgos"]
    assert len(inicial) == 1
    assert inicial[0]["condicion"] == "CARIES" and inicial[0]["estado_clinico"] == "REQUERIDO_PATOLOGIA"

    evolucion_id = _evolucion(paciente_id)
    pieza = _pieza(evolucion_id, 16)
    assert pieza["tiene_endodoncia"] is True
    assert pieza["hallazgos"][0]["condicion"] == "ENDODONCIA"
    assert pieza["hallazgos"][0]["estado_clinico"] == "REALIZADO_EN_CLINICA"

    # Un segundo tratamiento reutiliza la misma evolución y crea el hallazgo si no había
    resina = _crear_tratamiento("Restauración con resina", "RESTAURADORA")
    _realizar(paciente_id, doctor_id, resina, 21, "VESTIBULAR")
    assert _evolucion(paciente_id) == evolucion_id
    assert _pieza(evolucion_id, 21)["hallazgos"][0]["condicion"] == "OBTURACION_RESINA"
    assert _pieza(inicial_id, 21)["hallazgos"] == []

    # Extracción: la pieza queda extraída, sin obturación ni patología pendiente
    paciente_id = _crear_paciente()
    _odontograma_con_caries(paciente_id, 36)
    extraccion = _crear_tratamiento("Extracción simple", "CIRUGIA_PERIODONCIA")
    _realizar(paciente_id, doctor_id, extraccion, 36, "GENERAL")
    pieza = _pieza(_evolucion(paciente_id), 36)
    assert pieza["estado_general"] == "EXTRAIDO"
    assert pieza["hallazgos"] == []

    # Un tratamiento sin condición dental asociada no inventa una obturación
    paciente_id = _crear_paciente()
    res = client.post(f"{API}/odontogramas/", json={"paciente_id": paciente_id, "tipo_denticion": "ADULTA_PERMANENTE"}, headers=H)
    assert res.status_code == 201
    ortodoncia = _crear_tratamiento("Control de brackets", "ORTODONCIA")
    _realizar(paciente_id, doctor_id, ortodoncia, 11, "VESTIBULAR")
    assert _pieza(_evolucion(paciente_id), 11)["hallazgos"] == []
    print("✔ Odontograma: inicial intacto y resultado clínico según el tratamiento.")


def test_saldo_presupuesto():
    paciente_id, doctor_id = _crear_paciente(), _doctor()["id"]
    plan = client.post(f"{API}/tratamientos/planes", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "titulo": "Presupuesto", "items": [],
    }, headers=H).json()
    tratamiento = _crear_tratamiento("Profilaxis", "PREVENCION")
    client.post(f"{API}/tratamientos/items", json={
        "plan_id": plan["id"], "tratamiento_id": tratamiento, "costo_acordado": 300,
    }, headers=H)

    saldo = client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H).json()
    assert saldo["saldo_pendiente"] == 0.0 and saldo["estado_saldo"] == "AL_DIA"

    client.put(f"{API}/tratamientos/planes/{plan['id']}", json={"estado": "APROBADO"}, headers=H)
    saldo = client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H).json()
    assert saldo["saldo_pendiente"] == 300.0 and saldo["estado_saldo"] == "DEUDOR"
    print("✔ Saldo: un presupuesto propuesto no genera deuda; uno aprobado sí.")


def test_caja():
    paciente_id = _crear_paciente()
    plan = client.post(f"{API}/tratamientos/planes", json={
        "paciente_id": paciente_id, "titulo": "Plan con saldo", "items": [],
    }, headers=H).json()
    client.put(f"{API}/tratamientos/planes/{plan['id']}", json={"estado": "APROBADO", "costo_total": 1000}, headers=H)
    _asegurar_caja(abierta=False)

    pago = {"paciente_id": paciente_id, "monto": 50}
    assert client.post(f"{API}/caja/pagos", json={**pago, "metodo_pago": "EFECTIVO"}, headers=H).status_code == 400
    tarjeta = client.post(f"{API}/caja/pagos", json={**pago, "metodo_pago": "TARJETA_DEBITO"}, headers=H)
    assert tarjeta.status_code == 201, "Un cobro con tarjeta no depende de la gaveta"

    _asegurar_caja(abierta=True)
    antes = client.get(f"{API}/caja/estado", headers=H).json()

    # Montos inválidos y campos con nombre incorrecto se rechazan
    assert client.post(f"{API}/caja/pagos", json={**pago, "monto": -10}, headers=H).status_code == 422
    assert client.post(f"{API}/caja/pagos", json={**pago, "monto": 0}, headers=H).status_code == 422
    assert client.post(f"{API}/caja/pagos", json={**pago, "medio_pago": "TARJETA_DEBITO"}, headers=H).status_code == 422
    egreso = {"categoria": "COMPRA_INSUMOS", "concepto_motivo": "Guantes"}
    assert client.post(f"{API}/caja/egresos", json={**egreso, "monto": -5}, headers=H).status_code == 422
    assert client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": -1}, headers=H).status_code == 422

    # Una tarjeta no altera el efectivo; un egreso válido sí lo descuenta
    assert client.post(f"{API}/caja/pagos", json={**pago, "metodo_pago": "TARJETA_CREDITO"}, headers=H).status_code == 201
    medio = client.get(f"{API}/caja/estado", headers=H).json()
    assert medio["saldo_en_gaveta"] == antes["saldo_en_gaveta"]
    assert client.post(f"{API}/caja/egresos", json={**egreso, "monto": 5}, headers=H).status_code == 201

    # Cerrar exige el conteo y no asume cero
    assert client.post(f"{API}/caja/cerrar", json={"observaciones": "Sin conteo"}, headers=H).status_code == 400
    assert client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": -1}, headers=H).status_code == 422
    assert client.get(f"{API}/caja/estado", headers=H).json()["caja_abierta"] is True
    print("✔ Caja: montos y conteo validados; el efectivo solo cambia con efectivo.")


def test_nomina():
    doctor = _doctor()
    # La comisión no puede superar el saldo: el doctor necesita porcentaje y un cobro a su nombre
    _asegurar_caja(abierta=True)
    contratos = client.get(f"{API}/personal/contratos", headers=H).json()
    contrato = next((c for c in contratos if c["usuario_id"] == doctor["usuario_id"]), None)
    if contrato:
        client.put(f"{API}/personal/contratos/{contrato['id']}", json={"porcentaje_comision": 50}, headers=H)
    else:
        client.post(f"{API}/personal/contratos", json={"usuario_id": doctor["usuario_id"], "porcentaje_comision": 50}, headers=H)
    cobro = client.post(f"{API}/caja/pagos", json={
        "paciente_id": _crear_paciente(), "monto": 100, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True,
        "observaciones": "Consulta", "doctor_comision_id": doctor["id"],
    }, headers=H)
    assert cobro.status_code == 201, cobro.text

    pago = {
        "usuario_empleado_id": doctor["usuario_id"],
        "tipo_pago": "COMISION_TRATAMIENTOS",
        "monto_comisiones": 10,
        "monto_neto_pagado": 10,
        "metodo_pago": "EFECTIVO_CAJA",
    }

    _asegurar_caja(abierta=False)
    previos = len(client.get(f"{API}/empleados/pagos?usuario_empleado_id={doctor['usuario_id']}", headers=H).json())
    assert client.post(f"{API}/empleados/pagos", json=pago, headers=H).status_code == 400
    actuales = client.get(f"{API}/empleados/pagos?usuario_empleado_id={doctor['usuario_id']}", headers=H).json()
    assert len(actuales) == previos, "Un pago rechazado no debe quedar registrado"

    _asegurar_caja(abierta=True)
    desde = date.today().isoformat()
    res = client.post(f"{API}/empleados/pagos", json=pago, headers=H)
    assert res.status_code == 201, res.text
    assert client.post(f"{API}/empleados/pagos", json={**pago, "monto_neto_pagado": 0}, headers=H).status_code == 422

    resumen = client.get(f"{API}/reportes/resumen-financiero?fecha_desde={desde}T00:00:00", headers=H).json()
    assert float(resumen["egresos_por_categoria"]["COMISION_DOCTOR"]) >= 10
    print("✔ Nómina: exige caja abierta y clasifica la comisión correctamente.")


def test_reporte_productividad():
    doctor_id = _doctor()["id"]
    dia = date(2099, 1, 1) + timedelta(days=random.randint(0, 3000))
    cita = _cita(_crear_paciente(), doctor_id, dia, "09:00", "10:00").json()
    res = client.patch(f"{API}/citas/{cita['id']}/sillon", json={
        "hora_inicio_sillon": f"{dia}T09:00:00Z",
        "hora_fin_sillon": f"{dia}T09:30:00Z",
        "estado": "FINALIZADA",
    }, headers=H)
    assert res.status_code == 200, res.text

    def tiempo(desde, hasta):
        data = client.get(
            f"{API}/reportes/productividad-doctores?doctor_id={doctor_id}"
            f"&fecha_desde={desde}T00:00:00&fecha_hasta={hasta}T23:59:59",
            headers=H,
        ).json()
        return data["doctores"][0]["tiempo_total_sillon_minutos"]

    assert tiempo(dia, dia) == 30
    otro_periodo = dia + timedelta(days=4000)
    assert tiempo(otro_periodo, otro_periodo) == 0, "El tiempo debe respetar el rango de fechas"
    print("✔ Reportes: el tiempo en sillón respeta el rango de fechas.")


def test_box_y_horas_de_sillon():
    doctores = client.get(f"{API}/usuarios/doctores/lista", headers=H).json()
    assert len(doctores) >= 2, "La prueba necesita dos doctores"
    paciente_id, dia = _crear_paciente(), _dia_libre()

    primera = _cita(paciente_id, doctores[0]["id"], dia, "09:00", "10:00", notas_adicionales="Box 2")
    assert primera.status_code == 201, primera.text
    # Otro doctor no puede usar el mismo box a la misma hora, pero sí otro box
    assert _cita(paciente_id, doctores[1]["id"], dia, "09:30", "10:30", notas_adicionales="Box 2").status_code == 409
    otro_box = _cita(paciente_id, doctores[1]["id"], dia, "09:30", "10:30", notas_adicionales="Box 3")
    assert otro_box.status_code == 201, otro_box.text
    mover = client.put(f"{API}/citas/{otro_box.json()['id']}", json={"notas_adicionales": "Box 2"}, headers=H)
    assert mover.status_code == 409

    # Los botones de la agenda solo envían el estado: la API registra cada hora
    cita_id = primera.json()["id"]
    for estado, campo in [
        ("EN_ESPERA", "hora_llegada_recepcion"),
        ("EN_SILLON", "hora_inicio_sillon"),
        ("FINALIZADA", "hora_fin_sillon"),
    ]:
        res = client.patch(f"{API}/citas/{cita_id}/sillon", json={"estado": estado}, headers=H)
        assert res.status_code == 200, res.text
        assert res.json()[campo] is not None
    assert res.json()["duracion_sillon_minutos"] is not None
    print("✔ Agenda: el box no se comparte y las horas de sillón se registran solas.")


def _usuario_con_rol(rol):
    username = f"reg_{rol.lower()}_{uuid4().hex[:8]}"
    roles = client.get(f"{API}/usuarios/roles", headers=H).json()
    rol_id = next(r["id"] for r in roles if r["codigo"] == rol)
    res = client.post(f"{API}/usuarios/", json={
        "username": username, "password": "Clave1234!", "nombre": "Regresion", "apellido": rol.title(),
        "email": f"{username}@clinica-pruebas.com", "rol_id": rol_id,
    }, headers=H)
    assert res.status_code == 201, res.text
    token = client.post(f"{API}/auth/login", data={"username": username, "password": "Clave1234!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_evolucion_automatica():
    doctor_id = _doctor()["id"]
    paciente_id = _crear_paciente()
    _odontograma_con_caries(paciente_id, 16)
    tratamiento = _crear_tratamiento("Endodoncia premolar", "ENDODONCIA")
    plan = client.post(f"{API}/tratamientos/planes", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "titulo": "Plan", "items": [],
    }, headers=H).json()
    item = client.post(f"{API}/tratamientos/items", json={
        "plan_id": plan["id"], "tratamiento_id": tratamiento, "pieza_fdi": 16,
        "superficie": "OCLUSAL_INCISAL", "costo_acordado": 100,
    }, headers=H).json()
    dia = _dia_libre()
    cita = _cita(paciente_id, doctor_id, dia, "09:00", "10:00", item_plan_id=item["id"]).json()

    def visitas():
        return client.get(f"{API}/visitas/?paciente_id={paciente_id}", headers=H).json()

    assert visitas() == [], "Antes de finalizar la cita no hay evolución"

    res = client.patch(f"{API}/citas/{cita['id']}/sillon", json={"estado": "FINALIZADA"}, headers=H)
    assert res.status_code == 200, res.text
    lista = visitas()
    assert len(lista) == 1
    visita = lista[0]
    assert visita["cita_id"] == cita["id"] and visita["item_plan_id"] == item["id"]
    assert visita["generada_automaticamente"] is True
    assert visita["fecha_hora"][:10] == str(dia), "La evolución lleva la fecha de la cita"
    assert visita["doctor_nombre"]
    assert "Endodoncia premolar - Pieza 16" in visita["procedimiento_realizado"]
    assert "Caries en pieza 16" in visita["diagnostico"], visita["diagnostico"]

    # Guardar otra vez la cita finalizada no duplica la evolución
    assert client.put(f"{API}/citas/{cita['id']}", json={"estado": "FINALIZADA", "motivo_consulta": "Otro"}, headers=H).status_code == 409
    assert len(visitas()) == 1

    # El contenido no se edita, y no se crea otra evolución para la misma cita
    bloqueo = client.put(f"{API}/visitas/{visita['id']}", json={"diagnostico": "Cambiado"}, headers=H)
    assert bloqueo.status_code == 405
    assert visitas()[0]["diagnostico"] == visita["diagnostico"]
    duplicada = client.post(f"{API}/visitas/", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "cita_id": cita["id"],
        "diagnostico": "x", "procedimiento_realizado": "y",
    }, headers=H)
    assert duplicada.status_code == 409

    # Doctor y asistente agregan observaciones; recepción no
    url = f"{API}/visitas/{visita['id']}/observaciones"
    assert client.post(url, json={"texto": "Control en 7 días"}, headers=_usuario_con_rol("DOCTOR")).status_code == 201
    assert client.post(url, json={"texto": "Paciente toleró bien"}, headers=_usuario_con_rol("ASISTENTE")).status_code == 201
    assert client.post(url, json={"texto": "No autorizada"}, headers=_usuario_con_rol("RECEPCION")).status_code == 403
    assert client.post(url, json={"texto": "   "}, headers=H).status_code == 422
    observaciones = visitas()[0]["observaciones"]
    assert [o["texto"] for o in observaciones] == ["Control en 7 días", "Paciente toleró bien"]
    assert [o["rol_autor"] for o in observaciones] == ["DOCTOR", "ASISTENTE"]
    assert all(o["autor_nombre"] for o in observaciones)

    # Las observaciones no tienen ninguna ruta para editarlas o borrarlas
    obs_id = observaciones[0]["id"]
    assert client.put(f"{url}/{obs_id}", json={"texto": "Cambiada"}, headers=H).status_code in (404, 405)
    assert client.delete(f"{url}/{obs_id}", headers=H).status_code in (404, 405)

    # Una nota escrita antes por el doctor se conserva y no se duplica
    paciente_id = _crear_paciente()
    cita = _cita(paciente_id, doctor_id, _dia_libre(), "09:00", "10:00").json()
    manual = client.post(f"{API}/visitas/", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "cita_id": cita["id"],
        "diagnostico": "Manual", "procedimiento_realizado": "Manual",
    }, headers=H)
    assert manual.status_code == 201, manual.text
    client.patch(f"{API}/citas/{cita['id']}/sillon", json={"estado": "FINALIZADA"}, headers=H)
    lista = visitas()
    assert len(lista) == 1 and lista[0]["generada_automaticamente"] is False
    assert client.put(f"{API}/visitas/{lista[0]['id']}", json={"diagnostico": "Editada"}, headers=H).status_code == 405, "Una evolución manual tampoco se edita"
    assert client.delete(f"{API}/visitas/{lista[0]['id']}", headers=H).status_code == 405
    observada = client.post(f"{API}/visitas/{lista[0]['id']}/observaciones", json={"texto": "Aclaración posterior"}, headers=H)
    assert observada.status_code == 201, "La forma de corregirla es agregar una observación"
    permisos = client.get(f"{API}/usuarios/permisos", headers=H).json()
    assert not [p for p in permisos if p["codigo_permiso"] == "HISTORIA_CLINICA_UPDATE"], "Ya no hay permiso para editarlas"

    # Una cita sin plan también genera su evolución con el motivo de la consulta
    paciente_id = _crear_paciente()
    cita = _cita(paciente_id, doctor_id, _dia_libre(), "09:00", "10:00").json()
    client.put(f"{API}/citas/{cita['id']}", json={"estado": "FINALIZADA"}, headers=H)
    lista = visitas()
    assert len(lista) == 1 and lista[0]["procedimiento_realizado"] == "Prueba de agenda"
    print("✔ Evolución: creada al finalizar, con la fecha de la cita y solo admite observaciones.")


if __name__ == "__main__":
    test_box_y_horas_de_sillon()
    test_evolucion_automatica()
    test_agenda()
    test_odontograma()
    test_saldo_presupuesto()
    test_caja()
    test_nomina()
    test_reporte_productividad()
    print("TODAS LAS PRUEBAS DE REGRESIÓN PASARON")
