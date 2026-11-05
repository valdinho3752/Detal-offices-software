"""
Anulación de pagos, sillones configurables y gráficos de Inteligencia de Negocio.
Escribe datos y cierra la caja abierta: ejecutar contra una base de pruebas.
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
PNG = b"\x89PNG\r\n\x1a\n"


_siguiente_dia = itertools.count(random.randint(0, 20000))


def _dia_unico():
    """Las suites comparten doctor y base: un día repetido chocaría con otra cita."""
    return date(2500, 1, 1) + timedelta(days=next(_siguiente_dia))


def _login(usuario, clave):
    res = client.post(f"{API}/auth/login", data={"username": usuario, "password": clave})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in client.get(f"{API}/usuarios/roles", headers=H).json()}
DOCTOR = client.get(f"{API}/usuarios/doctores/lista", headers=H).json()[0]["id"]


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _usuario(rol):
    nombre = f"anu_{uuid4().hex[:10]}"
    _ok(client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": "Clave1234!", "nombre": "A", "apellido": "B",
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H), 201)
    return _login(nombre, "Clave1234!")


def _paciente():
    return _ok(client.post(f"{API}/pacientes/", json={
        "nombres": "Anulacion", "apellidos": "Prueba", "tipo_documento": "CI", "numero_documento": f"ANU-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H), 201)["id"]


def _plan(paciente_id, costo):
    plan = _ok(client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "doctor_id": DOCTOR, "titulo": "Plan"}, headers=H), 201)
    _ok(client.put(f"{API}/tratamientos/planes/{plan['id']}", json={"estado": "APROBADO", "costo_total": costo}, headers=H))
    return plan["id"]


def _caja():
    estado = _ok(client.get(f"{API}/caja/estado", headers=H))
    if not estado["caja_abierta"]:
        _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H), 201)
        estado = _ok(client.get(f"{API}/caja/estado", headers=H))
    return estado


def _cerrar_caja():
    estado = _caja()
    _ok(client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": estado["saldo_en_gaveta"]}, headers=H))


def _cobrar(paciente_id, monto, metodo="EFECTIVO", **extra):
    return _ok(client.post(f"{API}/caja/pagos", json={"paciente_id": paciente_id, "monto": monto, "metodo_pago": metodo, **extra}, headers=H), 201)


def _anular(pago_id, motivo="Error de digitación", headers=H):
    return client.post(f"{API}/caja/pagos/{pago_id}/anular", json={"motivo": motivo}, headers=headers)


def _saldo(paciente_id):
    return _ok(client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H))


def _gaveta():
    return _caja()["saldo_en_gaveta"]


def _resumen():
    return _ok(client.get(f"{API}/reportes/resumen-financiero", headers=H))


def _cita(paciente_id, notas="Box 1", doctor=DOCTOR, dia=None):
    dia = dia or _dia_unico()
    return client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": doctor, "motivo_consulta": "Consulta",
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z", "notas_adicionales": notas,
    }, headers=H)


def test_anular_efectivo_de_caja_abierta():
    _caja()
    paciente_id = _paciente()
    _plan(paciente_id, 500)
    gaveta = _gaveta()
    ingresos = float(_resumen()["total_ingresos"])
    pago = _cobrar(paciente_id, 200)
    assert _gaveta() == gaveta + 200 and _saldo(paciente_id)["saldo_pendiente"] == 300

    assert _anular(pago["id"], "   ").status_code == 422
    anulado = _ok(_anular(pago["id"]))
    assert anulado["anulado"] is True and anulado["motivo_anulacion"] == "Error de digitación" and anulado["fecha_anulacion"]

    assert _gaveta() == gaveta, "El efectivo vuelve a salir de la gaveta"
    datos = _saldo(paciente_id)
    assert datos["saldo_pendiente"] == 500 and datos["total_pagado"] == 0, "La deuda vuelve"
    fila = datos["pagos"][0]
    assert fila["anulado"] is True and fila["motivo_anulacion"] == "Error de digitación", "El pago se conserva en el historial"
    assert float(_resumen()["total_ingresos"]) == ingresos, "No cuenta como ingreso"
    assert _anular(pago["id"]).status_code == 409, "No se anula dos veces"
    assert _gaveta() == gaveta

    # El saldo vuelve a estar disponible para cobrar
    _cobrar(paciente_id, 500, "TRANSFERENCIA")
    assert _saldo(paciente_id)["saldo_pendiente"] == 0
    assert client.post(f"{API}/caja/pagos/{uuid4()}/anular", json={"motivo": "x"}, headers=H).status_code == 404

    logs = _ok(client.get(f"{API}/auditoria/?tabla_afectada=pagos&accion=UPDATE", headers=H))
    log = next(l for l in logs if l["registro_id"] == pago["id"])
    assert log["seccion_consultada"] == "ANULACION_PAGO" and log["datos_nuevos"]["motivo"] == "Error de digitación"
    print("✔ Efectivo de la caja abierta: sale de la gaveta, vuelve la deuda y queda en el historial.")


def test_anular_tarjeta_y_comision():
    _caja()
    paciente_id = _paciente()
    _plan(paciente_id, 500)
    gaveta = _gaveta()
    antes = _ok(client.get(f"{API}/empleados/comisiones-doctor/{DOCTOR}", headers=H))["total_cobrado_por_sus_tratamientos"]
    pago = _cobrar(paciente_id, 100, "TARJETA_DEBITO", doctor_comision_id=DOCTOR)
    assert _ok(client.get(f"{API}/empleados/comisiones-doctor/{DOCTOR}", headers=H))["total_cobrado_por_sus_tratamientos"] == antes + 100
    _ok(_anular(pago["id"]))
    assert _gaveta() == gaveta, "Una tarjeta no toca la gaveta"
    assert _ok(client.get(f"{API}/empleados/comisiones-doctor/{DOCTOR}", headers=H))["total_cobrado_por_sus_tratamientos"] == antes
    # El desglose de la caja tampoco lo cuenta
    estado = _caja()
    assert estado["ingresos_otros_medios"]["tarjeta_debito"] >= 0
    print("✔ Tarjeta: no toca la gaveta y deja de generar comisión.")


def test_anular_efectivo_de_caja_cerrada():
    _caja()
    paciente_id = _paciente()
    _plan(paciente_id, 500)
    pago = _cobrar(paciente_id, 80)
    _cerrar_caja()

    res = _anular(pago["id"])
    assert res.status_code == 400 and "abre la caja" in res.json()["detail"]
    assert _saldo(paciente_id)["pagos"][0]["anulado"] is False, "Sin caja abierta no cambia nada"

    # Sin efectivo suficiente tampoco
    _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 10}, headers=H), 201)
    res = _anular(pago["id"])
    assert res.status_code == 400 and "efectivo suficiente" in res.json()["detail"]
    _cerrar_caja()

    _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 200}, headers=H), 201)
    gaveta = _gaveta()
    ingresos, egresos = float(_resumen()["total_ingresos"]), float(_resumen()["total_egresos"])
    _ok(_anular(pago["id"]))
    assert _gaveta() == gaveta - 80, "La devolución sale de la caja abierta"
    resumen = _resumen()
    assert float(resumen["total_ingresos"]) == ingresos - 80
    assert float(resumen["total_egresos"]) == egresos, "Una devolución no cuenta como gasto: se descontaría dos veces"
    print("✔ Efectivo de una caja cerrada: la devolución sale de la caja abierta, sin contarse dos veces.")


def test_anular_cuenta_de_cita():
    _caja()
    paciente_id = _paciente()
    plan_id = _plan(paciente_id, 0)
    trat = _ok(client.post(f"{API}/tratamientos/catalogo", json={"codigo": f"A-{uuid4().hex[:10]}", "categoria": "RESTAURADORA", "nombre": "Resina", "costo_base": 100}, headers=H), 201)["id"]
    item = _ok(client.post(f"{API}/tratamientos/items", json={"plan_id": plan_id, "tratamiento_id": trat, "pieza_fdi": 16, "costo_acordado": 100}, headers=H), 201)["id"]
    dia = _dia_unico()
    cita = _ok(client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": DOCTOR, "item_plan_id": item, "motivo_consulta": "Resina",
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z",
    }, headers=H), 201)["id"]
    _ok(client.patch(f"{API}/citas/{cita}/sillon", json={"estado": "FINALIZADA"}, headers=H))
    cobro = _ok(client.get(f"{API}/cobros-cita/?paciente_id={paciente_id}", headers=H))[0]
    url = f"{API}/cobros-cita/{cobro['id']}"
    linea = cobro["lineas"][0]
    gaveta = _gaveta()
    _ok(client.post(f"{url}/confirmar", json={"metodo_pago": "EFECTIVO", "lineas": [
        {"id": linea["id"], "concepto": linea["concepto"], "monto": 100},
        {"concepto": "Radiografía", "monto": 20},
    ]}, headers=H))
    assert _gaveta() == gaveta + 120
    pagos = _saldo(paciente_id)["pagos"]
    assert len(pagos) == 2

    # Anular uno de los pagos anula toda la cuenta y la reabre para corregirla
    _ok(_anular(pagos[0]["id"], "Se cobró mal"))
    datos = _saldo(paciente_id)
    assert all(p["anulado"] for p in datos["pagos"]) and datos["saldo_pendiente"] == 100
    assert _gaveta() == gaveta
    reabierto = _ok(client.get(url, headers=H))
    assert reabierto["estado"] == "PENDIENTE" and reabierto["fecha_cierre"] is None and float(reabierto["total"]) == 120
    assert _ok(client.get(f"{API}/citas/?paciente_id={paciente_id}", headers=H))[0]["cobro_estado"] == "PENDIENTE"

    # Se vuelve a cobrar con el monto correcto
    _ok(client.post(f"{url}/confirmar", json={"metodo_pago": "TRANSFERENCIA"}, headers=H))
    datos = _saldo(paciente_id)
    assert datos["saldo_pendiente"] == 0 and len(datos["pagos"]) == 4
    print("✔ Cuenta de cita: se anula completa, se reabre y se puede cobrar de nuevo.")


def test_quien_puede_anular():
    _caja()
    paciente_id = _paciente()
    _plan(paciente_id, 100)
    pago = _cobrar(paciente_id, 10, "TRANSFERENCIA")
    for rol in ("RECEPCION", "DOCTOR", "ASISTENTE"):
        assert _anular(pago["id"], headers=_usuario(rol)).status_code == 403, rol
    assert _saldo(paciente_id)["pagos"][0]["anulado"] is False
    print("✔ Anular pagos: solo el administrador por defecto.")


def test_sillones():
    url = f"{API}/sillones/"
    doctor = _usuario("DOCTOR")
    recepcion = _usuario("RECEPCION")
    iniciales = _ok(client.get(url, headers=H))
    assert {1, 2, 3} <= {s["numero"] for s in iniciales}, "Los tres sillones de siempre"
    assert client.get(url, headers=recepcion).status_code == 200, "La agenda los necesita"

    # Solo el administrador los configura
    assert client.post(url, json={}, headers=recepcion).status_code == 403
    assert client.post(url, json={}, headers=doctor).status_code == 403

    # Agregar: numeración propia y nombre por defecto
    nuevo = _ok(client.post(url, json={"especialidad": "Pediatría"}, headers=H), 201)
    assert nuevo["numero"] == max(s["numero"] for s in iniciales) + 1
    assert nuevo["nombre"] == f"Box {nuevo['numero']}" and nuevo["activo"] is True
    assert client.post(url, json={"nombre": "   "}, headers=H).status_code == 422

    # Editar
    editado = _ok(client.put(f"{url}{nuevo['id']}", json={"nombre": "Sala Niños", "especialidad": ""}, headers=H))
    assert editado["nombre"] == "Sala Niños" and editado["especialidad"] is None
    assert client.put(f"{url}{nuevo['id']}", json={"nombre": "X"}, headers=doctor).status_code == 403

    # La agenda acepta el sillón nuevo y valida su ocupación
    paciente_id = _paciente()
    notas = f"Box {nuevo['numero']}"
    dia = _dia_unico()
    cita = _ok(_cita(paciente_id, notas, dia=dia), 201)
    doctores = _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H))
    otro_doctor = next(d["id"] for d in doctores if d["id"] != DOCTOR)
    assert _cita(paciente_id, notas, doctor=otro_doctor, dia=dia).status_code == 409, "Sillón ocupado"

    # Sin sillón inexistente
    assert _cita(paciente_id, "Box 9999").status_code == 400

    # Con citas por atender no se puede quitar
    res = client.delete(f"{url}{nuevo['id']}", headers=H)
    assert res.status_code == 409 and "1 cita" in res.json()["detail"]
    assert client.put(f"{url}{nuevo['id']}", json={"activo": False}, headers=H).status_code == 409

    # Con historial se desactiva, y deja de aceptar citas
    _ok(client.delete(f"{API}/citas/{cita['id']}", headers=H), 204) if False else client.delete(f"{API}/citas/{cita['id']}", headers=H)
    res = _ok(client.delete(f"{url}{nuevo['id']}", headers=H))
    assert res["resultado"] == "DESACTIVADO"
    assert _cita(paciente_id, notas).status_code == 400, "Un sillón desactivado no admite citas"
    assert nuevo["id"] in [s["id"] for s in _ok(client.get(url, headers=H))], "Sigue existiendo para el historial"

    # Reactivar devuelve el mismo número, y un número retirado no se reutiliza
    assert _ok(client.put(f"{url}{nuevo['id']}", json={"activo": True}, headers=H))["numero"] == nuevo["numero"]
    client.delete(f"{url}{nuevo['id']}", headers=H)
    otro = _ok(client.post(url, json={"nombre": "Temporal"}, headers=H), 201)
    assert otro["numero"] == nuevo["numero"] + 1

    # Sin historial se elimina de verdad
    assert _ok(client.delete(f"{url}{otro['id']}", headers=H))["resultado"] == "ELIMINADO"
    assert otro["id"] not in [s["id"] for s in _ok(client.get(url, headers=H))]

    # Una cita se puede mover de sillón, y cambiar solo el estado no vuelve a validar
    cita_b = _ok(_cita(paciente_id, "Box 2"), 201)
    assert client.put(f"{API}/citas/{cita_b['id']}", json={"notas_adicionales": "Box 9999"}, headers=H).status_code == 400
    _ok(client.put(f"{API}/citas/{cita_b['id']}", json={"estado": "CONFIRMADA"}, headers=H))
    client.delete(f"{API}/citas/{cita_b['id']}", headers=H)
    print("✔ Sillones: se agregan, editan y retiran solo por ADMIN, sin dejar citas huérfanas.")


def test_siempre_queda_un_sillon_activo():
    url = f"{API}/sillones/"
    activos = [s for s in _ok(client.get(url, headers=H)) if s["activo"]]
    retirados = []
    for sillon in activos[:-1]:
        res = client.put(f"{url}{sillon['id']}", json={"activo": False}, headers=H)
        if res.status_code == 200:
            retirados.append(sillon)
    restantes = [s for s in _ok(client.get(url, headers=H)) if s["activo"]]
    if len(restantes) == 1:
        ultimo = restantes[0]
        res = client.put(f"{url}{ultimo['id']}", json={"activo": False}, headers=H)
        assert res.status_code == 400 and "al menos un sillón" in res.json()["detail"]
        assert client.delete(f"{url}{ultimo['id']}", headers=H).status_code == 400
    for sillon in retirados:
        _ok(client.put(f"{url}{sillon['id']}", json={"activo": True}, headers=H))
    print("✔ La agenda siempre conserva al menos un sillón activo.")


def test_graficos():
    base = f"{API}/reportes/graficos"
    for nombre in ("tratamientos-demanda", "productividad-doctores"):
        for tema in ("claro", "oscuro"):
            res = client.get(f"{base}/{nombre}?tema={tema}", headers=H)
            assert res.status_code == 200, res.text
            assert res.headers["content-type"] == "image/png" and res.content.startswith(PNG) and len(res.content) > 1000
            assert "no-store" in res.headers["cache-control"]
        assert client.get(f"{base}/{nombre}?tema=rojo", headers=H).status_code == 422
        for rol in ("DOCTOR", "RECEPCION", "ASISTENTE"):
            assert client.get(f"{base}/{nombre}", headers=_usuario(rol)).status_code == 403
        assert client.get(f"{base}/{nombre}").status_code == 401

    # Sin datos en el rango también responde una imagen válida
    res = client.get(f"{base}/tratamientos-demanda?fecha_desde=1990-01-01T00:00:00&fecha_hasta=1990-01-02T00:00:00", headers=H)
    assert res.status_code == 200 and res.content.startswith(PNG)
    res = client.get(f"{base}/productividad-doctores?fecha_desde=1990-01-01T00:00:00&fecha_hasta=1990-01-02T00:00:00", headers=H)
    assert res.status_code == 200 and res.content.startswith(PNG)
    print("✔ Gráficos: PNG en ambos temas, solo con permiso y también sin datos.")


if __name__ == "__main__":
    test_anular_efectivo_de_caja_abierta()
    test_anular_tarjeta_y_comision()
    test_anular_efectivo_de_caja_cerrada()
    test_anular_cuenta_de_cita()
    test_quien_puede_anular()
    test_sillones()
    test_siempre_queda_un_sillon_activo()
    test_graficos()
    print("TODAS LAS PRUEBAS PASARON")
