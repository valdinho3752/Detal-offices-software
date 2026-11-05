"""
Moneda configurable de la clínica. Cambia el ajuste y lo restaura: ejecutar contra una base de pruebas.
"""
import os
import sys
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API = "/api/v1"
URL = f"{API}/configuracion/"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave):
    return {"Authorization": f"Bearer {_ok(client.post(f'{API}/auth/login', data={'username': usuario, 'password': clave}))['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}


def _usuario(rol):
    nombre = f"cfg_{uuid4().hex[:10]}"
    _ok(client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": "Clave1234!", "nombre": "Conf", "apellido": "Prueba",
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H), 201)
    return _login(nombre, "Clave1234!")


def _fijar(simbolo):
    return _ok(client.put(URL, json={"moneda_simbolo": simbolo}, headers=H))


def test_permisos():
    assert client.get(URL).status_code == 401
    for rol in ("DOCTOR", "RECEPCION", "ASISTENTE"):
        cabeceras = _usuario(rol)
        assert _ok(client.get(URL, headers=cabeceras))["moneda_simbolo"], "Todos necesitan leerla para mostrar montos"
        assert client.put(URL, json={"moneda_simbolo": "€"}, headers=cabeceras).status_code == 403
    print("✔ Moneda: todos la leen y solo el administrador la cambia.")


def test_valida_el_simbolo():
    for invalido in ("", "   ", "123456789", "Bs1", "S/ 1"):
        assert client.put(URL, json={"moneda_simbolo": invalido}, headers=H).status_code == 422, invalido
    assert _fijar("  Bs.  ")["moneda_simbolo"] == "Bs.", "Sin espacios sobrantes"
    print("✔ Moneda: el símbolo se valida.")


def test_se_aplica_a_los_mensajes_y_se_audita():
    original = _ok(client.get(URL, headers=H))["moneda_simbolo"]
    try:
        _fijar("Bs.")
        estado = _ok(client.get(f"{API}/caja/estado", headers=H))
        if not estado["caja_abierta"]:
            _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H), 201)
        res = client.post(f"{API}/caja/egresos", json={"categoria": "OTRO", "monto": 99999999, "concepto_motivo": "Excede"}, headers=H)
        assert res.status_code == 400
        detalle = res.json()["detail"]
        assert "Bs. 99.999.999,00" in detalle and "$" not in detalle, detalle

        _fijar("$")
        detalle = client.post(f"{API}/caja/egresos", json={"categoria": "OTRO", "monto": 99999999, "concepto_motivo": "Excede"}, headers=H).json()["detail"]
        assert "$99.999.999,00" in detalle, detalle

        registros = _ok(client.get(f"{API}/auditoria/?tabla_afectada=configuracion_clinica", headers=H))
        assert registros, "El cambio de moneda queda auditado"
    finally:
        _fijar(original)
    print("✔ Moneda: los mensajes usan el símbolo elegido y el cambio queda auditado.")


if __name__ == "__main__":
    test_permisos()
    test_valida_el_simbolo()
    test_se_aplica_a_los_mensajes_y_se_audita()
    print("TODAS LAS PRUEBAS PASARON")
