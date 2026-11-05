"""
Reportes filtrados por periodo: la demanda usa la fecha de realización del tratamiento.
Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


login = client.post(f"{API}/auth/login", data={"username": "admin", "password": "admin123"})
H = {"Authorization": f"Bearer {_ok(login)['access_token']}"}
DOCTOR = _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H))[0]["id"]


def _dia():
    return date(2150, 1, 1) + timedelta(days=random.randint(0, 30000))


def _paciente():
    return _ok(client.post(f"{API}/pacientes/", json={
        "nombres": "Periodo", "apellidos": "Prueba", "tipo_documento": "CI", "numero_documento": f"PER-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H), 201)["id"]


def _tratamiento():
    codigo = f"PER-{uuid4().hex[:8]}"
    return _ok(client.post(f"{API}/tratamientos/catalogo", json={
        "codigo": codigo, "categoria": "PREVENCION", "nombre": f"Tratamiento {codigo}", "costo_base": 100,
    }, headers=H), 201)["id"]


def _item(tratamiento_id, paciente_id=None):
    paciente_id = paciente_id or _paciente()
    plan = _ok(client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "doctor_id": DOCTOR, "titulo": "Plan"}, headers=H), 201)
    item = _ok(client.post(f"{API}/tratamientos/items", json={
        "plan_id": plan["id"], "tratamiento_id": tratamiento_id, "costo_acordado": 100,
    }, headers=H), 201)
    return paciente_id, item["id"]


def _cita(paciente_id, inicio, fin, item_id=None):
    return _ok(client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": DOCTOR, "motivo_consulta": "Control", "item_plan_id": item_id,
        "fecha_inicio_programada": inicio, "fecha_fin_programada": fin, "notas_adicionales": "Box 1",
    }, headers=H), 201)


def _finalizar(cita_id):
    _ok(client.put(f"{API}/citas/{cita_id}", json={"estado": "FINALIZADA"}, headers=H))


def _rango(desde, hasta):
    return {"fecha_desde": f"{desde}T00:00:00Z", "fecha_hasta": f"{hasta}T23:59:59Z"}


def _cantidad(tratamiento_id, **periodo):
    reporte = _ok(client.get(f"{API}/reportes/tratamientos-demanda", params={"limit": 1000, **periodo}, headers=H))
    return next((i["cantidad_realizada"] for i in reporte["ranking_tratamientos"] if i["tratamiento_id"] == tratamiento_id), 0)


def test_demanda_usa_la_fecha_de_la_cita():
    tratamiento = _tratamiento()
    paciente, item = _item(tratamiento)
    dia = _dia()
    cita = _cita(paciente, f"{dia}T09:00:00Z", f"{dia}T10:00:00Z", item)
    hoy = datetime.now(timezone.utc).date()

    assert _cantidad(tratamiento) == 0, "Un tratamiento pendiente no cuenta"
    _finalizar(cita["id"])
    assert _cantidad(tratamiento) == 1
    assert _cantidad(tratamiento, **_rango(dia, dia)) == 1
    assert _cantidad(tratamiento, **_rango(dia + timedelta(days=1), dia + timedelta(days=30))) == 0
    assert _cantidad(tratamiento, **_rango(dia - timedelta(days=30), dia - timedelta(days=1))) == 0
    assert _cantidad(tratamiento, **_rango(hoy, hoy)) == 0, "No debe contar el día en que se creó el plan"
    print("✔ Demanda: cuenta el tratamiento el día de la cita, no el de su creación.")


def test_cambios_manuales_de_estado():
    tratamiento = _tratamiento()
    _, item = _item(tratamiento)
    hoy = datetime.now(timezone.utc).date()
    alrededor = _rango(hoy - timedelta(days=1), hoy + timedelta(days=1))
    url = f"{API}/tratamientos/items/{item}"

    _ok(client.put(url, json={"estado": "COMPLETADO"}, headers=H))
    assert _cantidad(tratamiento, **alrededor) == 1

    _ok(client.put(url, json={"estado": "PENDIENTE"}, headers=H))
    assert _cantidad(tratamiento) == 0

    _ok(client.put(url, json={"estado": "COMPLETADO"}, headers=H))
    assert _cantidad(tratamiento, **alrededor) == 1
    print("✔ Demanda: el estado manual fija y limpia la fecha de realización.")


def test_una_segunda_cita_no_cambia_la_fecha():
    tratamiento = _tratamiento()
    paciente, item = _item(tratamiento)
    primero = _dia()
    segundo = primero + timedelta(days=40)
    _finalizar(_cita(paciente, f"{primero}T09:00:00Z", f"{primero}T10:00:00Z", item)["id"])
    _finalizar(_cita(paciente, f"{segundo}T09:00:00Z", f"{segundo}T10:00:00Z", item)["id"])

    assert _cantidad(tratamiento, **_rango(primero, primero)) == 1
    assert _cantidad(tratamiento, **_rango(segundo, segundo)) == 0
    print("✔ Demanda: un tratamiento en varias citas conserva la fecha de la primera.")


def test_evolucion_manual_usa_su_fecha():
    tratamiento = _tratamiento()
    paciente, item = _item(tratamiento)
    dia = _dia()
    _ok(client.post(f"{API}/visitas/", json={
        "paciente_id": paciente, "doctor_id": DOCTOR, "item_plan_id": item, "fecha_hora": f"{dia}T09:00:00Z",
        "motivo_visita": "Control", "diagnostico": "Sin hallazgos", "procedimiento_realizado": "Control",
    }, headers=H), 201)

    assert _cantidad(tratamiento, **_rango(dia, dia)) == 1
    hoy = datetime.now(timezone.utc).date()
    assert _cantidad(tratamiento, **_rango(hoy, hoy)) == 0
    print("✔ Demanda: la evolución manual usa la fecha registrada en ella.")


def _productividad(**periodo):
    reporte = _ok(client.get(f"{API}/reportes/productividad-doctores", params={"doctor_id": DOCTOR, **periodo}, headers=H))
    return reporte["doctores"][0]


def test_productividad_por_periodo():
    dia = _dia()
    siguiente = dia + timedelta(days=1)
    # Empieza un día y termina al siguiente: pertenece al día en que empieza
    cita = _cita(_paciente(), f"{dia}T23:30:00Z", f"{siguiente}T00:30:00Z")
    assert _productividad(**_rango(dia, dia))["total_citas"] == 1
    assert _productividad(**_rango(siguiente, siguiente))["total_citas"] == 0

    _ok(client.patch(f"{API}/citas/{cita['id']}/sillon", json={
        "hora_inicio_sillon": f"{dia}T23:30:00Z", "hora_fin_sillon": f"{siguiente}T00:15:00Z", "estado": "FINALIZADA",
    }, headers=H))
    resultado = _productividad(**_rango(dia, dia))
    assert resultado["citas_finalizadas"] == 1 and resultado["tiempo_total_sillon_minutos"] == 45
    print("✔ Productividad: la cita cuenta el día en que empieza, aunque cruce la medianoche.")


def test_limites_con_zona_horaria():
    dia = _dia()
    # 03:00 UTC sigue siendo el día anterior en UTC-4
    _cita(_paciente(), f"{dia}T03:00:00Z", f"{dia}T03:30:00Z")
    anterior = dia - timedelta(days=1)
    del_dia_local = {"fecha_desde": f"{anterior}T00:00:00-04:00", "fecha_hasta": f"{anterior}T23:59:59-04:00"}
    assert _productividad(**del_dia_local)["total_citas"] == 1
    assert _productividad(fecha_desde=f"{dia}T00:00:00-04:00", fecha_hasta=f"{dia}T23:59:59-04:00")["total_citas"] == 0
    print("✔ Reportes: los límites respetan la zona horaria que envía el navegador.")


def test_finanzas_por_periodo():
    url = f"{API}/reportes/resumen-financiero"
    _ok(client.post(f"{API}/caja/pagos", json={
        "paciente_id": _paciente(), "monto": 150, "metodo_pago": "TARJETA_DEBITO", "es_cobro_directo": True, "referencia_comprobante": "T-1",
        "observaciones": "Consulta",
    }, headers=H), 201)
    hoy = datetime.now(timezone.utc).date()
    alrededor = _rango(hoy - timedelta(days=1), hoy + timedelta(days=1))
    assert float(_ok(client.get(url, params=alrededor, headers=H))["total_ingresos"]) >= 150
    otro = _ok(client.get(url, params=_rango(date(1990, 1, 1), date(1990, 1, 31)), headers=H))
    assert float(otro["total_ingresos"]) == 0 and float(otro["total_egresos"]) == 0
    print("✔ Finanzas: ingresos y egresos respetan el periodo.")


def test_graficos_siguen_el_periodo():
    tratamiento = _tratamiento()
    paciente, item = _item(tratamiento)
    dia = _dia()
    _finalizar(_cita(paciente, f"{dia}T09:00:00Z", f"{dia}T10:00:00Z", item)["id"])

    for nombre in ("tratamientos-demanda", "productividad-doctores"):
        url = f"{API}/reportes/graficos/{nombre}"
        con_datos = client.get(url, params=_rango(dia, dia), headers=H)
        sin_datos = client.get(url, params=_rango(date(1990, 1, 1), date(1990, 1, 2)), headers=H)
        assert con_datos.status_code == sin_datos.status_code == 200
        assert con_datos.content.startswith(PNG) and sin_datos.content.startswith(PNG)
        assert con_datos.content != sin_datos.content, f"{nombre} debe cambiar con el periodo"
        assert client.get(url, params={"fecha_desde": "no-es-fecha"}, headers=H).status_code == 422
    print("✔ Gráficos: la imagen cambia según el periodo.")


if __name__ == "__main__":
    test_demanda_usa_la_fecha_de_la_cita()
    test_cambios_manuales_de_estado()
    test_una_segunda_cita_no_cambia_la_fecha()
    test_evolucion_manual_usa_su_fecha()
    test_productividad_por_periodo()
    test_limites_con_zona_horaria()
    test_finanzas_por_periodo()
    test_graficos_siguen_el_periodo()
    print("TODAS LAS PRUEBAS PASARON")
