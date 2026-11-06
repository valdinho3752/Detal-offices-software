"""
Cobro que se crea al finalizar una cita: edición, confirmación y efecto en saldos, caja y comisiones.
Escribe datos: ejecutar contra una base de pruebas.
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
    return date(2400, 1, 1) + timedelta(days=next(_siguiente_dia))


def _login(usuario, clave):
    res = client.post(f"{API}/auth/login", data={"username": usuario, "password": clave})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


H = _login("admin", "admin123")
DOCTOR = client.get(f"{API}/usuarios/doctores/lista", headers=H).json()[0]["id"]
ROLES = {r["codigo"]: r["id"] for r in client.get(f"{API}/usuarios/roles", headers=H).json()}


def _ok(res, codigo=201):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _paciente():
    return _ok(client.post(f"{API}/pacientes/", json={
        "nombres": "Cobro", "apellidos": "Cita", "tipo_documento": "CI", "numero_documento": f"COB-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H))["id"]


def _tratamiento(nombre="Resina simple", costo=80):
    return _ok(client.post(f"{API}/tratamientos/catalogo", json={
        "codigo": f"C-{uuid4().hex[:10]}", "categoria": "RESTAURADORA", "nombre": nombre, "costo_base": costo,
    }, headers=H))["id"]


def _plan(paciente_id, estado="APROBADO"):
    plan = _ok(client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "doctor_id": DOCTOR, "titulo": "Plan cobro"}, headers=H))
    _ok(client.put(f"{API}/tratamientos/planes/{plan['id']}", json={"estado": estado}, headers=H), 200)
    return plan["id"]


def _item(plan_id, costo, tratamiento=None, pieza=16):
    return _ok(client.post(f"{API}/tratamientos/items", json={
        "plan_id": plan_id, "tratamiento_id": tratamiento or _tratamiento(), "pieza_fdi": pieza,
        "superficie": "OCLUSAL_INCISAL", "costo_acordado": costo,
    }, headers=H))["id"]


def _cita(paciente_id, item=None, notas=None, tratamiento=None):
    dia = _dia_unico()
    return _ok(client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": DOCTOR, "item_plan_id": item, "tratamiento_id": tratamiento,
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z",
        "motivo_consulta": "Consulta de prueba", "notas_adicionales": notas,
    }, headers=H))["id"]


def _finalizar(cita_id, por_put=False):
    if por_put:
        _ok(client.put(f"{API}/citas/{cita_id}", json={"estado": "FINALIZADA"}, headers=H), 200)
    else:
        _ok(client.patch(f"{API}/citas/{cita_id}/sillon", json={"estado": "FINALIZADA"}, headers=H), 200)


def _cobros(paciente_id):
    return _ok(client.get(f"{API}/cobros-cita/?paciente_id={paciente_id}", headers=H), 200)


def _saldo(paciente_id):
    return _ok(client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H), 200)


def _caja():
    estado = _ok(client.get(f"{API}/caja/estado", headers=H), 200)
    if not estado["caja_abierta"]:
        _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H))
        estado = _ok(client.get(f"{API}/caja/estado", headers=H), 200)
    return estado


def _lineas(cobro):
    return [{"id": l["id"], "concepto": l["concepto"], "monto": l["monto"]} for l in cobro["lineas"]]


def test_se_crea_al_finalizar():
    paciente_id = _paciente()
    plan_id = _plan(paciente_id)
    trat = _tratamiento("Endodoncia premolar")
    item_a = _item(plan_id, 100, trat, 16)
    item_b = _item(plan_id, 50, None, 21)
    cita_id = _cita(paciente_id, item_a, f"Box 1 | ItemsPlan: [{item_a}, {item_b}]")
    assert _cobros(paciente_id) == [], "Sin finalizar no hay cobro"

    _finalizar(cita_id)
    cobro = _cobros(paciente_id)[0]
    assert cobro["cita_id"] == cita_id and cobro["estado"] == "PENDIENTE" and cobro["doctor_id"] == DOCTOR
    assert float(cobro["total"]) == 150 and len(cobro["lineas"]) == 2
    assert any("Endodoncia premolar - Pieza 16" in l["concepto"] for l in cobro["lineas"])
    assert all(l["aplica_a_plan"] for l in cobro["lineas"])

    cita = next(c for c in _ok(client.get(f"{API}/citas/?paciente_id={paciente_id}", headers=H), 200) if c["id"] == cita_id)
    assert cita["cobro_id"] == cobro["id"] and cita["cobro_estado"] == "PENDIENTE"

    # Crear la cuenta no registra ningún pago, y volver a guardar la cita no la duplica
    assert _saldo(paciente_id)["pagos"] == [] and _saldo(paciente_id)["saldo_pendiente"] == 150
    _ok(client.put(f"{API}/citas/{cita_id}", json={"estado": "FINALIZADA", "motivo_consulta": "Otra"}, headers=H), 409)
    assert len(_cobros(paciente_id)) == 1

    # Sin tratamientos: toma el precio del catálogo, o queda en cero con el motivo
    paciente_id = _paciente()
    _finalizar(_cita(paciente_id, tratamiento=_tratamiento("Consulta", 30)), por_put=True)
    cobro = _cobros(paciente_id)[0]
    assert float(cobro["total"]) == 30 and cobro["lineas"][0]["concepto"] == "Consulta" and not cobro["lineas"][0]["aplica_a_plan"]
    paciente_id = _paciente()
    _finalizar(_cita(paciente_id))
    cobro = _cobros(paciente_id)[0]
    assert float(cobro["total"]) == 0 and cobro["lineas"][0]["concepto"] == "Consulta de prueba"
    print("✔ Se crea una sola vez al finalizar, con los tratamientos de la cita y sin registrar pagos.")


def test_abonos_anteriores_no_se_cobran_dos_veces():
    _caja()
    paciente_id = _paciente()
    plan_id = _plan(paciente_id)
    item = _item(plan_id, 100)
    # Adelanto general, como los que registra Cobranzas sin indicar plan
    _ok(client.post(f"{API}/caja/pagos", json={"paciente_id": paciente_id, "monto": 60, "metodo_pago": "TRANSFERENCIA"}, headers=H))
    _finalizar(_cita(paciente_id, item))
    linea = _cobros(paciente_id)[0]["lineas"][0]
    assert float(linea["monto"]) == 40 and float(linea["costo_referencia"]) == 100

    # Totalmente cubierto: propone cero y se cierra sin pago
    paciente_id = _paciente()
    plan_id = _plan(paciente_id)
    item = _item(plan_id, 100)
    _ok(client.post(f"{API}/caja/pagos", json={"paciente_id": paciente_id, "monto": 100, "plan_id": plan_id, "metodo_pago": "TRANSFERENCIA"}, headers=H))
    _finalizar(_cita(paciente_id, item))
    cobro = _cobros(paciente_id)[0]
    assert float(cobro["total"]) == 0
    res = client.post(f"{API}/cobros-cita/{cobro['id']}/confirmar", json={"metodo_pago": "TRANSFERENCIA"}, headers=H)
    assert res.status_code == 400 and "sin pago" in res.json()["detail"]
    assert client.post(f"{API}/cobros-cita/{cobro['id']}/cerrar-sin-pago", json={"motivo": "  "}, headers=H).status_code == 422
    cerrado = _ok(client.post(f"{API}/cobros-cita/{cobro['id']}/cerrar-sin-pago", json={"motivo": "Cubierto por abonos"}, headers=H), 200)
    assert cerrado["estado"] == "ANULADO" and cerrado["motivo_cierre"] == "Cubierto por abonos"
    assert len(_saldo(paciente_id)["pagos"]) == 1
    print("✔ Lo ya abonado no se vuelve a cobrar; una cuenta en cero se cierra con su motivo.")


def test_editar_y_confirmar():
    estado_caja = _caja()
    paciente_id = _paciente()
    plan_id = _plan(paciente_id)
    item = _item(plan_id, 100)
    _finalizar(_cita(paciente_id, item))
    cobro = _cobros(paciente_id)[0]
    url = f"{API}/cobros-cita/{cobro['id']}"

    # Editar: cambiar concepto y monto, y agregar una línea manual; sigue pendiente
    linea = cobro["lineas"][0]
    editado = _ok(client.put(url, json={"lineas": [
        {"id": linea["id"], "concepto": "Resina con descuento", "monto": 80},
        {"concepto": "Radiografía", "monto": 15},
    ]}, headers=H), 200)
    assert editado["estado"] == "PENDIENTE" and float(editado["total"]) == 95 and _saldo(paciente_id)["pagos"] == []
    guardada = next(l for l in editado["lineas"] if l["id"] == linea["id"])
    assert guardada["aplica_a_plan"] is True and guardada["item_plan_id"] == item, "Editar no pierde el vínculo con el plan"
    manual = next(l for l in editado["lineas"] if l["concepto"] == "Radiografía")
    assert manual["aplica_a_plan"] is False

    # Validaciones
    assert client.put(url, json={"lineas": []}, headers=H).status_code == 422
    assert client.put(url, json={"lineas": [{"concepto": "x", "monto": -1}]}, headers=H).status_code == 422
    assert client.put(url, json={"lineas": [{"concepto": " ", "monto": 1}]}, headers=H).status_code == 422
    assert client.put(url, json={"lineas": [{"id": str(uuid4()), "concepto": "x", "monto": 1}]}, headers=H).status_code == 400

    # Superar el saldo del plan se rechaza y no guarda nada
    res = client.post(f"{url}/confirmar", json={"metodo_pago": "TRANSFERENCIA", "lineas": [
        {"id": linea["id"], "concepto": "Resina", "monto": 500},
    ]}, headers=H)
    assert res.status_code == 400 and "supera el saldo" in res.json()["detail"]
    assert float(_ok(client.get(url, headers=H), 200)["total"]) == 95 and _saldo(paciente_id)["pagos"] == []

    # Confirmar: la línea del plan abona al plan y la manual es cobro directo
    gaveta = estado_caja["saldo_en_gaveta"] if estado_caja.get("saldo_en_gaveta") is not None else _caja()["saldo_en_gaveta"]
    gaveta = _caja()["saldo_en_gaveta"]
    comision_antes = _ok(client.get(f"{API}/empleados/comisiones-doctor/{DOCTOR}", headers=H), 200)["total_cobrado_por_sus_tratamientos"]
    pagado = _ok(client.post(f"{url}/confirmar", json={
        "metodo_pago": "EFECTIVO", "referencia_comprobante": "REC-77", "doctor_comision_id": DOCTOR, "observaciones": "Paga completo",
    }, headers=H), 200)
    assert pagado["estado"] == "PAGADO" and pagado["fecha_cierre"]
    saldo = _saldo(paciente_id)
    assert saldo["saldo_pendiente"] == 20 and saldo["total_pagado"] == 80
    assert sorted((p["monto"], p["es_cobro_directo"]) for p in saldo["pagos"]) == [(15.0, True), (80.0, False)]
    assert all("Cobro de cita" in p["observaciones"] and "Paga completo" in p["observaciones"] for p in saldo["pagos"])
    assert all(p["numero_comprobante"] == "REC-77" for p in saldo["pagos"])
    assert _caja()["saldo_en_gaveta"] == gaveta + 95
    comision = _ok(client.get(f"{API}/empleados/comisiones-doctor/{DOCTOR}", headers=H), 200)["total_cobrado_por_sus_tratamientos"]
    assert comision == comision_antes + 95

    # Ya pagado no se puede editar, confirmar ni cerrar
    assert client.put(url, json={"lineas": _lineas(pagado)}, headers=H).status_code == 409
    assert client.post(f"{url}/confirmar", json={"metodo_pago": "EFECTIVO"}, headers=H).status_code == 409
    assert client.post(f"{url}/cerrar-sin-pago", json={"motivo": "x"}, headers=H).status_code == 409
    assert len(_saldo(paciente_id)["pagos"]) == 2

    logs = _ok(client.get(f"{API}/auditoria/?tabla_afectada=cobros_cita", headers=H), 200)
    secciones = {l["seccion_consultada"] for l in logs if l["registro_id"] == cobro["id"]}
    assert secciones == {"COBRO_CITA_CREADO", "COBRO_CITA_EDITADO", "COBRO_CITA_PAGADO"}, secciones
    print("✔ Editable hasta confirmar; el pago se reparte entre plan y cobro directo, con caja y comisión.")


def test_plan_propuesto_es_cobro_directo():
    _caja()
    paciente_id = _paciente()
    plan_id = _plan(paciente_id, "PROPUESTO")
    item = _item(plan_id, 70)
    _finalizar(_cita(paciente_id, item))
    cobro = _cobros(paciente_id)[0]
    assert float(cobro["total"]) == 70 and cobro["lineas"][0]["aplica_a_plan"] is False
    _ok(client.post(f"{API}/cobros-cita/{cobro['id']}/confirmar", json={"metodo_pago": "TARJETA_DEBITO"}, headers=H), 200)
    saldo = _saldo(paciente_id)
    assert saldo["pagos"][0]["es_cobro_directo"] is True and saldo["saldo_pendiente"] == 0
    print("✔ Un tratamiento de un plan solo propuesto se cobra como directo.")


def test_efectivo_requiere_caja():
    estado = _caja()
    paciente_id = _paciente()
    _finalizar(_cita(paciente_id, tratamiento=_tratamiento("Consulta", 30)))
    cobro = _cobros(paciente_id)[0]
    _ok(client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": _caja()["saldo_en_gaveta"]}, headers=H), 200)
    url = f"{API}/cobros-cita/{cobro['id']}/confirmar"
    assert client.post(url, json={"metodo_pago": "EFECTIVO"}, headers=H).status_code == 400
    assert _ok(client.get(f"{API}/cobros-cita/{cobro['id']}", headers=H), 200)["estado"] == "PENDIENTE"
    assert client.post(url, json={"metodo_pago": "TRANSFERENCIA"}, headers=H).status_code == 400
    assert _ok(client.get(f"{API}/cobros-cita/{cobro['id']}", headers=H), 200)["estado"] == "PENDIENTE"
    _caja()
    _ok(client.post(url, json={"metodo_pago": "TRANSFERENCIA"}, headers=H), 200)
    print("✔ Sin caja abierta no se confirma con ningún medio de pago, y la cuenta sigue pendiente.")


def test_permisos():
    paciente_id = _paciente()
    _finalizar(_cita(paciente_id, tratamiento=_tratamiento("Consulta", 30)))
    cobro = _cobros(paciente_id)[0]

    def usuario(rol):
        nombre = f"cob_{uuid4().hex[:10]}"
        _ok(client.post(f"{API}/usuarios/", json={
            "username": nombre, "password": "Clave1234!", "nombre": "A", "apellido": "B",
            "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
        }, headers=H))
        return _login(nombre, "Clave1234!")

    for rol in ("DOCTOR", "ASISTENTE"):
        cabeceras = usuario(rol)
        assert client.get(f"{API}/cobros-cita/", headers=cabeceras).status_code == 403
        assert client.post(f"{API}/cobros-cita/{cobro['id']}/confirmar", json={}, headers=cabeceras).status_code == 403

    recepcion = usuario("RECEPCION")
    assert cobro["id"] in [c["id"] for c in _ok(client.get(f"{API}/cobros-cita/?estado=PENDIENTE", headers=recepcion), 200)]
    _ok(client.post(f"{API}/cobros-cita/{cobro['id']}/confirmar", json={"metodo_pago": "TRANSFERENCIA"}, headers=recepcion), 200)
    print("✔ Recepción y administración cobran; doctor y asistente no acceden.")


if __name__ == "__main__":
    test_se_crea_al_finalizar()
    test_abonos_anteriores_no_se_cobran_dos_veces()
    test_editar_y_confirmar()
    test_plan_propuesto_es_cobro_directo()
    test_efectivo_requiere_caja()
    test_permisos()
    print("TODAS LAS PRUEBAS DE COBROS DE CITAS PASARON")
