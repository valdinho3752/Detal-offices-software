"""
Tope de comisiones y adelantos del personal con sueldo fijo.
Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import sys
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API = "/api/v1"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave):
    return {"Authorization": f"Bearer {_ok(client.post(f'{API}/auth/login', data={'username': usuario, 'password': clave}))['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}


def _usuario(rol, **contrato):
    nombre = f"nom_{uuid4().hex[:10]}"
    creado = _ok(client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": "Clave1234!", "nombre": "Nomina", "apellido": rol.title(),
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H), 201)
    if contrato:
        _ok(client.post(f"{API}/personal/contratos", json={"usuario_id": creado["id"], **contrato}, headers=H), 201)
    return creado["id"], _login(nombre, "Clave1234!")


def _paciente():
    return _ok(client.post(f"{API}/pacientes/", json={
        "nombres": "Nomina", "apellidos": "Prueba", "tipo_documento": "CI", "numero_documento": f"NOM-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H), 201)["id"]


def _pagar(usuario_id, tipo, neto, metodo="TRANSFERENCIA", **extra):
    return client.post(f"{API}/empleados/pagos", json={
        "usuario_empleado_id": usuario_id, "tipo_pago": tipo, "monto_neto_pagado": neto, "metodo_pago": metodo, **extra,
    }, headers=H)


def _liquidacion(usuario_id, cabeceras=H):
    return _ok(client.get(f"{API}/empleados/liquidacion/{usuario_id}", headers=cabeceras))


def _caja():
    estado = _ok(client.get(f"{API}/caja/estado", headers=H))
    if estado["caja_abierta"] and estado["saldo_en_gaveta"] >= 2000:
        return estado
    if estado["caja_abierta"]:
        _ok(client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": estado["saldo_en_gaveta"]}, headers=H))
    _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 5000}, headers=H), 201)
    return _ok(client.get(f"{API}/caja/estado", headers=H))


def _doctor_con_cobro(monto, porcentaje=40):
    usuario_id, cabeceras = _usuario("DOCTOR", tipo_remuneracion="PORCENTAJE_COMISION", porcentaje_comision=porcentaje)
    doctor_id = _ok(client.get(f"{API}/auth/me", headers=cabeceras))["doctor_id"]
    cobro = _ok(client.post(f"{API}/caja/pagos", json={
        "paciente_id": _paciente(), "monto": monto, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True,
        "observaciones": "Consulta", "doctor_comision_id": doctor_id,
    }, headers=H), 201)
    return usuario_id, cobro["id"]


def test_tope_de_comisiones():
    usuario_id, _ = _doctor_con_cobro(1000)
    assert _liquidacion(usuario_id)["saldo_comision_por_pagar"] == 400

    excedido = _pagar(usuario_id, "COMISION_TRATAMIENTOS", 400.01)
    assert excedido.status_code == 400 and "$400.00" in excedido.json()["detail"]
    _ok(_pagar(usuario_id, "COMISION_TRATAMIENTOS", 150), 201)
    datos = _liquidacion(usuario_id)
    assert datos["comisiones_ya_liquidadas"] == 150, "El monto liquidado no depende de lo que envíe la pantalla"
    assert datos["saldo_comision_por_pagar"] == 250

    # El adelanto reduce lo que se puede liquidar
    _ok(_pagar(usuario_id, "ADELANTO", 50), 201)
    assert _pagar(usuario_id, "COMISION_TRATAMIENTOS", 201).status_code == 400
    _ok(_pagar(usuario_id, "COMISION_TRATAMIENTOS", 200), 201)
    assert _liquidacion(usuario_id)["saldo_comision_por_pagar"] == 0
    assert _pagar(usuario_id, "COMISION_TRATAMIENTOS", 0.01).status_code == 400
    print("✔ Comisiones: no se puede pagar más que el saldo.")


def test_anular_un_cobro_liquidado_compensa_lo_futuro():
    usuario_id, cobro = _doctor_con_cobro(1000)
    _ok(_pagar(usuario_id, "COMISION_TRATAMIENTOS", 400), 201)
    _caja()
    _ok(client.post(f"{API}/caja/pagos/{cobro}/anular", json={"motivo": "Error"}, headers=H))

    datos = _liquidacion(usuario_id)
    assert datos["saldo_comision_por_pagar"] == -400, "Lo pagado de más queda visible como saldo negativo"
    assert _pagar(usuario_id, "COMISION_TRATAMIENTOS", 1).status_code == 400

    # Un cobro nuevo de $1.500 genera $600: primero compensa los $400 pagados de más
    doctor_id = next(d["id"] for d in _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H)) if d["usuario_id"] == usuario_id)
    _ok(client.post(f"{API}/caja/pagos", json={
        "paciente_id": _paciente(), "monto": 1500, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True,
        "observaciones": "Consulta", "doctor_comision_id": doctor_id,
    }, headers=H), 201)
    assert _liquidacion(usuario_id)["saldo_comision_por_pagar"] == 200
    print("✔ Comisiones: lo pagado de más tras una anulación se compensa con comisiones futuras.")


def test_adelanto_de_sueldo_fijo():
    usuario_id, cabeceras = _usuario("RECEPCION", tipo_remuneracion="SUELDO_FIJO_MENSUAL", salario_base=3000)
    _caja()
    egresos = _ok(client.get(f"{API}/caja/estado", headers=H))["total_egresos_efectivo"]

    _ok(_pagar(usuario_id, "ADELANTO", 500, "EFECTIVO_CAJA"), 201)
    assert _ok(client.get(f"{API}/caja/estado", headers=H))["total_egresos_efectivo"] == egresos + 500
    datos = _liquidacion(usuario_id)
    assert datos["salario_base"] == 3000 and datos["total_anticipos"] == 500

    # Descuentos inconsistentes o mayores a lo pendiente
    assert _pagar(usuario_id, "SUELDO_MENSUAL", 2500, monto_base=3000, deducciones_descuentos=600).status_code == 422
    assert _pagar(usuario_id, "SUELDO_MENSUAL", 2400, monto_base=3000, deducciones_descuentos=600).status_code == 400
    assert _pagar(usuario_id, "BONO", 100, deducciones_descuentos=10).status_code == 422

    _ok(_pagar(usuario_id, "SUELDO_MENSUAL", 2500, monto_base=3000, deducciones_descuentos=500), 201)
    datos = _liquidacion(usuario_id)
    assert datos["total_anticipos"] == 0 and datos["adelantos_descontados_en_sueldo"] == 500
    assert _pagar(usuario_id, "SUELDO_MENSUAL", 2900, monto_base=3000, deducciones_descuentos=100).status_code == 400, "No se descuenta dos veces"
    print("✔ Sueldo fijo: el adelanto sale de caja y se descuenta una sola vez del sueldo.")


def test_sueldo_cubierto_por_adelantos():
    usuario_id, _ = _usuario("ASISTENTE", salario_base=1000)
    _caja()
    _ok(_pagar(usuario_id, "ADELANTO", 1000), 201)
    egresos = _ok(client.get(f"{API}/caja/estado", headers=H))["total_egresos_efectivo"]
    _ok(_pagar(usuario_id, "SUELDO_MENSUAL", 0, "EFECTIVO_CAJA", monto_base=1000, deducciones_descuentos=1000), 201)
    assert _ok(client.get(f"{API}/caja/estado", headers=H))["total_egresos_efectivo"] == egresos, "No sale dinero de la gaveta"
    assert _liquidacion(usuario_id)["total_anticipos"] == 0
    assert _pagar(usuario_id, "ADELANTO", 0).status_code == 422
    print("✔ Sueldo fijo: un sueldo cubierto por adelantos se registra sin mover la gaveta.")


def test_sueldo_y_comision_no_cuentan_dos_veces():
    usuario_id, _ = _doctor_con_cobro(1000)
    _ok(_pagar(usuario_id, "ADELANTO", 100), 201)
    assert _liquidacion(usuario_id)["saldo_comision_por_pagar"] == 300
    # Si el adelanto se recupera del sueldo, deja de descontarse de las comisiones
    _ok(_pagar(usuario_id, "SUELDO_MENSUAL", 900, monto_base=1000, deducciones_descuentos=100), 201)
    assert _liquidacion(usuario_id)["saldo_comision_por_pagar"] == 400
    print("✔ Contrato mixto: el adelanto se recupera una sola vez.")


def test_no_sale_mas_efectivo_del_que_hay():
    usuario_id, _ = _usuario("RECEPCION", salario_base=100000)
    gaveta = _caja()["saldo_en_gaveta"]
    exceso = round(gaveta + 0.01, 2)

    res = _pagar(usuario_id, "ADELANTO", exceso, "EFECTIVO_CAJA")
    assert res.status_code == 400 and "efectivo suficiente" in res.json()["detail"]
    res = client.post(f"{API}/caja/egresos", json={"categoria": "OTRO", "monto": exceso, "concepto_motivo": "Excede"}, headers=H)
    assert res.status_code == 400 and "efectivo suficiente" in res.json()["detail"]
    assert _caja()["saldo_en_gaveta"] == gaveta, "Un pago rechazado no mueve la gaveta"
    assert _liquidacion(usuario_id)["adelantos_entregados"] == 0, "Ni queda registrado"

    # Por transferencia no depende de la gaveta, y se puede retirar hasta el último centavo
    _ok(_pagar(usuario_id, "ADELANTO", exceso), 201)
    _ok(_pagar(usuario_id, "BONO", gaveta, "EFECTIVO_CAJA"), 201)
    assert _ok(client.get(f"{API}/caja/estado", headers=H))["saldo_en_gaveta"] == 0
    print("✔ Caja: no sale más efectivo del que hay en la gaveta.")


def test_privacidad():
    propio, cabeceras = _usuario("DOCTOR")
    otro, _ = _usuario("RECEPCION", salario_base=2000)

    lista = _ok(client.get(f"{API}/empleados/personal", headers=cabeceras))
    assert [p["usuario_id"] for p in lista] == [propio]
    assert client.get(f"{API}/empleados/liquidacion/{otro}", headers=cabeceras).status_code == 403
    assert _liquidacion(propio, cabeceras)["salario_base"] == 0

    todos = {p["usuario_id"]: p for p in _ok(client.get(f"{API}/empleados/personal", headers=H))}
    assert todos[otro]["contrato"]["salario_base"] == 2000 and todos[otro]["doctor_id"] is None
    assert client.post(f"{API}/empleados/pagos", json={
        "usuario_empleado_id": str(uuid4()), "tipo_pago": "BONO", "monto_neto_pagado": 1, "metodo_pago": "TRANSFERENCIA",
    }, headers=H).status_code == 404
    print("✔ Nómina: cada empleado solo ve lo suyo.")


def test_contrato_rechaza_valores_invalidos():
    usuario_id, _ = _usuario("ASISTENTE")
    url = f"{API}/personal/contratos"
    assert client.post(url, json={"usuario_id": usuario_id, "porcentaje_comision": 101}, headers=H).status_code == 422
    assert client.post(url, json={"usuario_id": usuario_id, "salario_base": -1}, headers=H).status_code == 422
    contrato = _ok(client.post(url, json={"usuario_id": usuario_id, "salario_base": 1000}, headers=H), 201)
    assert client.put(f"{url}/{contrato['id']}", json={"porcentaje_comision": -1}, headers=H).status_code == 422
    print("✔ Contratos: rechazan montos y porcentajes inválidos.")


if __name__ == "__main__":
    test_tope_de_comisiones()
    test_anular_un_cobro_liquidado_compensa_lo_futuro()
    test_adelanto_de_sueldo_fijo()
    test_sueldo_cubierto_por_adelantos()
    test_sueldo_y_comision_no_cuentan_dos_veces()
    test_no_sale_mas_efectivo_del_que_hay()
    test_privacidad()
    test_contrato_rechaza_valores_invalidos()
    print("TODAS LAS PRUEBAS PASARON")
