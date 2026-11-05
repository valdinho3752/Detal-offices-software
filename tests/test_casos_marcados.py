"""
Defectos detectados al redactar el plan de QA. Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import random
import sys
from datetime import date, timedelta
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
API = "/api/v1"
CLAVE = "Clave1234!"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave=CLAVE):
    return client.post(f"{API}/auth/login", data={"username": usuario, "password": clave})


H = {"Authorization": f"Bearer {_ok(_login('admin', 'admin123'))['access_token']}"}
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}
DOCTOR = _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H))[0]["id"]


def _usuario(rol="ASISTENTE"):
    nombre = f"mar_{uuid4().hex[:10]}"
    correo = f"{nombre}@clinica-pruebas.com"
    _ok(client.post(f"{API}/usuarios/", json={"username": nombre, "password": CLAVE, "nombre": "Mar", "apellido": "Cado", "email": correo, "rol_id": ROLES[rol]}, headers=H), 201)
    return nombre, correo


def _paciente():
    return _ok(client.post(f"{API}/pacientes/", json={
        "nombres": "Mar", "apellidos": "Cado", "tipo_documento": "CI", "numero_documento": f"MAR-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H), 201)["id"]


def _tratamiento():
    return _ok(client.post(f"{API}/tratamientos/catalogo", json={"codigo": f"M{uuid4().hex[:8]}", "categoria": "PREVENCION", "nombre": "Limpieza", "costo_base": 100}, headers=H), 201)["id"]


def _plan(paciente_id, costo=None):
    plan = _ok(client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "doctor_id": DOCTOR, "titulo": "Plan"}, headers=H), 201)["id"]
    if costo:
        _ok(client.put(f"{API}/tratamientos/planes/{plan}", json={"estado": "APROBADO", "costo_total": costo}, headers=H))
    return plan


def _pagar(paciente_id, plan_id, monto):
    return _ok(client.post(f"{API}/caja/pagos", json={"paciente_id": paciente_id, "plan_id": plan_id, "monto": monto, "metodo_pago": "TRANSFERENCIA"}, headers=H), 201)


def _dia():
    return date(2300, 1, 1) + timedelta(days=random.randint(0, 30000))


def _cita(paciente_id, dia, box=1, doctor=DOCTOR):
    return client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": doctor, "motivo_consulta": "Control",
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z", "notas_adicionales": f"Box {box}",
    }, headers=H)


def test_login_con_correo():
    nombre, correo = _usuario()
    assert _login(nombre).status_code == 200
    assert _login(correo).status_code == 200
    assert _login(correo.upper()).status_code == 200, "El correo no distingue mayúsculas"
    assert _login(correo, "Incorrecta1").status_code == 401
    print("✔ ACC-22: se entra con usuario o con correo.")


def test_cambio_obligatorio_en_la_api():
    nombre, _ = _usuario("RECEPCION")
    c = {"Authorization": f"Bearer {_ok(_login(nombre))['access_token']}"}
    assert client.get(f"{API}/pacientes/", headers=c).status_code == 200, "Fuera de producción no se exige"
    original = settings.ENV
    settings.ENV = "production"
    try:
        res = client.get(f"{API}/pacientes/", headers=c)
        assert res.status_code == 403 and "cambiar tu contraseña" in res.json()["detail"]
        assert client.post(f"{API}/citas/", json={}, headers=c).status_code == 403
        assert client.get(f"{API}/auth/me", headers=c).status_code == 200, "La pantalla necesita sus datos"
        assert client.get(f"{API}/configuracion/", headers=c).status_code == 200
        token = _ok(client.post(f"{API}/auth/cambiar-contrasena", json={"actual": CLAVE, "nueva": "Nueva1234!"}, headers=c))["access_token"]
        assert client.get(f"{API}/pacientes/", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    finally:
        settings.ENV = original
    print("✔ PWD-18: en producción la API también exige cambiar la contraseña inicial.")


def test_piezas_fdi():
    pid = _paciente()
    plan = _plan(pid)
    tratamiento = _tratamiento()
    item = {"plan_id": plan, "tratamiento_id": tratamiento, "costo_acordado": 10}
    for invalida in (0, 9, 10, 19, 30, 56, 59, 86, 99, 100, -1):
        assert client.post(f"{API}/tratamientos/items", json={**item, "pieza_fdi": invalida}, headers=H).status_code == 422, invalida
    for valida in (11, 18, 28, 38, 48, 51, 55, 65, 75, 85):
        _ok(client.post(f"{API}/tratamientos/items", json={**item, "pieza_fdi": valida}, headers=H), 201)
    _ok(client.post(f"{API}/tratamientos/items", json=item, headers=H), 201)

    rx = {"paciente_id": pid, "tipo_estudio": "PERIAPICAL", "titulo": "Rx", "archivo_url": "https://ejemplo.test/a.jpg"}
    assert client.post(f"{API}/radiografias/", json={**rx, "pieza_fdi": 99}, headers=H).status_code == 422
    _ok(client.post(f"{API}/radiografias/", json={**rx, "pieza_fdi": 16}, headers=H), 201)
    print("✔ ODO-35: solo se aceptan piezas de la numeración FDI.")


def test_montos_de_tratamiento():
    pid = _paciente()
    plan = _plan(pid)
    tratamiento = _tratamiento()
    base = {"plan_id": plan, "tratamiento_id": tratamiento}
    assert client.post(f"{API}/tratamientos/items", json={**base, "costo_acordado": -1}, headers=H).status_code == 422
    assert client.post(f"{API}/tratamientos/items", json={**base, "precio_unitario": -1}, headers=H).status_code == 422
    assert client.post(f"{API}/tratamientos/items", json={**base, "precio_unitario": 10, "descuento": -5}, headers=H).status_code == 422
    item = _ok(client.post(f"{API}/tratamientos/items", json={**base, "costo_acordado": 10}, headers=H), 201)
    assert client.put(f"{API}/tratamientos/items/{item['id']}", json={"costo_acordado": -1}, headers=H).status_code == 422
    assert client.put(f"{API}/tratamientos/planes/{plan}", json={"costo_total": -1}, headers=H).status_code == 422
    print("✔ TRA-18: los montos de un plan no pueden ser negativos.")


def test_total_no_baja_de_lo_pagado():
    pid = _paciente()
    plan = _plan(pid)
    tratamiento = _tratamiento()
    uno = _ok(client.post(f"{API}/tratamientos/items", json={"plan_id": plan, "tratamiento_id": tratamiento, "costo_acordado": 100}, headers=H), 201)
    dos = _ok(client.post(f"{API}/tratamientos/items", json={"plan_id": plan, "tratamiento_id": tratamiento, "costo_acordado": 100}, headers=H), 201)
    _ok(client.put(f"{API}/tratamientos/planes/{plan}", json={"estado": "APROBADO"}, headers=H))
    pago = _pagar(pid, plan, 150)

    assert client.put(f"{API}/tratamientos/planes/{plan}", json={"costo_total": 149}, headers=H).status_code == 409
    assert client.put(f"{API}/tratamientos/items/{uno['id']}", json={"costo_acordado": 10}, headers=H).status_code == 409
    assert client.delete(f"{API}/tratamientos/items/{dos['id']}", headers=H).status_code == 409
    assert client.put(f"{API}/tratamientos/planes/{plan}", json={"estado": "CANCELADO"}, headers=H).status_code == 409
    assert client.put(f"{API}/tratamientos/planes/{plan}", json={"estado": "PROPUESTO"}, headers=H).status_code == 409
    assert _ok(client.get(f"{API}/pacientes/{pid}/saldo", headers=H))["saldo_pendiente"] == 50, "Nada cambió"

    _ok(client.put(f"{API}/tratamientos/items/{uno['id']}", json={"costo_acordado": 50}, headers=H))
    assert _ok(client.get(f"{API}/pacientes/{pid}/saldo", headers=H))["saldo_pendiente"] == 0, "Hasta lo pagado sí se permite"

    _ok(client.post(f"{API}/caja/pagos/{pago['id']}/anular", json={"motivo": "Error"}, headers=H))
    _ok(client.put(f"{API}/tratamientos/planes/{plan}", json={"estado": "CANCELADO"}, headers=H))
    print("✔ TRA-19: el total de un plan no baja de lo pagado, y un plan con pagos no se cancela.")


def test_estados_de_cita():
    pid = _paciente()
    dia = _dia()
    cita = _ok(_cita(pid, dia), 201)
    url = f"{API}/citas/{cita['id']}"

    # AGE-36: se puede saltar pasos, y la evolución y la cuenta se crean igual
    _ok(client.put(url, json={"estado": "FINALIZADA"}, headers=H))
    assert len(_ok(client.get(f"{API}/visitas/?paciente_id={pid}", headers=H))) == 1
    cuentas = [c for c in _ok(client.get(f"{API}/cobros-cita/", headers=H)) if c["cita_id"] == cita["id"]]
    assert len(cuentas) == 1

    # AGE-34: una cita atendida ya no cambia, por ninguna vía
    for cuerpo in ({"estado": "PROGRAMADA"}, {"estado": "CANCELADA"}, {"motivo_consulta": "Otro"}, {"fecha_inicio_programada": f"{dia}T08:00:00Z"}):
        assert client.put(url, json=cuerpo, headers=H).status_code == 409, cuerpo
    assert client.patch(f"{url}/sillon", json={"estado": "EN_SILLON"}, headers=H).status_code == 409
    assert client.put(url, json={"estado": "FINALIZADA"}, headers=H).status_code == 409, "Tampoco se finaliza dos veces"
    assert len(_ok(client.get(f"{API}/visitas/?paciente_id={pid}", headers=H))) == 1

    # Una cancelada solo puede volver a programarse
    otra = _ok(_cita(pid, _dia()), 201)
    _ok(client.delete(f"{API}/citas/{otra['id']}", headers=H), 204) if False else client.delete(f"{API}/citas/{otra['id']}", headers=H)
    assert client.put(f"{API}/citas/{otra['id']}", json={"estado": "FINALIZADA"}, headers=H).status_code == 409
    assert client.put(f"{API}/citas/{otra['id']}", json={"estado": "EN_SILLON"}, headers=H).status_code == 409
    _ok(client.put(f"{API}/citas/{otra['id']}", json={"estado": "PROGRAMADA"}, headers=H))
    print("✔ AGE-34 y AGE-36: una cita atendida no cambia; una descartada solo vuelve a programarse.")


def test_reactivar_sobre_horario_ocupado():
    pid = _paciente()
    dia = _dia()
    cancelada = _ok(_cita(pid, dia), 201)
    client.delete(f"{API}/citas/{cancelada['id']}", headers=H)
    _ok(_cita(pid, dia), 201)
    res = client.put(f"{API}/citas/{cancelada['id']}", json={"estado": "PROGRAMADA"}, headers=H)
    assert res.status_code == 409, res.text
    print("✔ AGE-35: reactivar una cita sobre un horario ocupado se rechaza.")


def test_protesis():
    pid = _paciente()
    base = {"paciente_id": pid, "doctor_id": DOCTOR, "laboratorio_nombre": "Lab", "tipo_trabajo": "CORONA_ZIRCONIO"}
    assert client.post(f"{API}/protesis/", json={**base, "costo_laboratorio": -1}, headers=H).status_code == 422
    assert client.post(f"{API}/protesis/", json={**base, "fecha_envio": "2030-01-10", "fecha_entrega_esperada": "2030-01-05"}, headers=H).status_code == 400
    orden = _ok(client.post(f"{API}/protesis/", json={**base, "fecha_envio": "2030-01-10", "fecha_entrega_esperada": "2030-01-10", "costo_laboratorio": 50}, headers=H), 201)
    url = f"{API}/protesis/{orden['id']}"
    assert client.put(url, json={"costo_laboratorio": -5}, headers=H).status_code == 422
    assert client.put(url, json={"fecha_entrega_esperada": "2030-01-01"}, headers=H).status_code == 400
    _ok(client.put(url, json={"fecha_entrega_esperada": "2030-02-01"}, headers=H))
    print("✔ PRO-13 y PRO-14: costo no negativo y entrega no anterior al envío.")


def test_metodo_de_pago_de_nomina():
    nombre, _ = _usuario()
    uid = next(p["usuario_id"] for p in _ok(client.get(f"{API}/empleados/personal", headers=H)) if nombre in str(p) or p["nombre_completo"] == "Mar Cado")
    base = {"usuario_empleado_id": uid, "tipo_pago": "BONO", "monto_neto_pagado": 1}
    assert client.post(f"{API}/empleados/pagos", json={**base, "metodo_pago": "INVENTADO"}, headers=H).status_code == 422
    _ok(client.post(f"{API}/empleados/pagos", json={**base, "metodo_pago": "TRANSFERENCIA"}, headers=H), 201)
    print("✔ NOM-29: el método de pago de nómina solo admite valores válidos.")


def test_productividad_agrupada():
    pid = _paciente()
    nombre = f"mar_{uuid4().hex[:10]}"
    creado = _ok(client.post(f"{API}/usuarios/", json={"username": nombre, "password": CLAVE, "nombre": "Pro", "apellido": "Ductiva", "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES["DOCTOR"]}, headers=H), 201)
    doctor = next(d["id"] for d in _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H)) if d["usuario_id"] == creado["id"])
    dia = _dia()

    def nueva(hora):
        return _ok(client.post(f"{API}/citas/", json={
            "paciente_id": pid, "doctor_id": doctor, "motivo_consulta": "x", "notas_adicionales": "Box 1",
            "fecha_inicio_programada": f"{dia}T{hora}:00:00Z", "fecha_fin_programada": f"{dia}T{hora}:30:00Z",
        }, headers=H), 201)["id"]

    # Dos atendidas: una con 30 minutos de sillón y otra sin pasar por él
    a, b, c, d = nueva("08"), nueva("09"), nueva("10"), nueva("11")
    _ok(client.patch(f"{API}/citas/{a}/sillon", json={"hora_inicio_sillon": f"{dia}T08:00:00Z", "hora_fin_sillon": f"{dia}T08:30:00Z", "estado": "FINALIZADA"}, headers=H))
    _ok(client.put(f"{API}/citas/{b}", json={"estado": "FINALIZADA"}, headers=H))
    _ok(client.put(f"{API}/citas/{c}", json={"estado": "NO_ASISTIO"}, headers=H))
    client.delete(f"{API}/citas/{d}", headers=H)

    datos = _ok(client.get(f"{API}/reportes/productividad-doctores", params={"doctor_id": doctor}, headers=H))["doctores"][0]
    assert (datos["total_citas"], datos["citas_finalizadas"], datos["citas_no_asistio"], datos["citas_canceladas"]) == (4, 2, 1, 1), datos
    assert datos["tiempo_total_sillon_minutos"] == 30 and datos["promedio_minutos_por_cita"] == 30, "La cita sin duración no baja el promedio"
    assert datos["tasa_ausentismo_porcentaje"] == 25

    sin_citas = _ok(client.get(f"{API}/reportes/productividad-doctores", params={"doctor_id": doctor, "fecha_desde": "1990-01-01T00:00:00Z", "fecha_hasta": "1990-01-02T00:00:00Z"}, headers=H))["doctores"][0]
    assert sin_citas["total_citas"] == 0 and sin_citas["promedio_minutos_por_cita"] == 0
    print("✔ REN-07 y AGE-36: productividad en una consulta, sin que las citas sin duración afecten el promedio.")


if __name__ == "__main__":
    test_login_con_correo()
    test_cambio_obligatorio_en_la_api()
    test_piezas_fdi()
    test_montos_de_tratamiento()
    test_total_no_baja_de_lo_pagado()
    test_estados_de_cita()
    test_reactivar_sobre_horario_ocupado()
    test_protesis()
    test_metodo_de_pago_de_nomina()
    test_productividad_agrupada()
    print("TODAS LAS PRUEBAS PASARON")
