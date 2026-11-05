"""
Correcciones de marcajes por el administrador. Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import RegistroAsistencia

client = TestClient(app)
API = "/api/v1"
URL = f"{API}/personal/asistencia"
MOTIVO = "Olvidó marcar la salida"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave):
    return {"Authorization": f"Bearer {_ok(client.post(f'{API}/auth/login', data={'username': usuario, 'password': clave}))['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}


def _usuario(rol="ASISTENTE"):
    nombre = f"cor_{uuid4().hex[:10]}"
    creado = _ok(client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": "Clave1234!", "nombre": "Correccion", "apellido": "Prueba",
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H), 201)
    return creado["id"], _login(nombre, "Clave1234!")


def _marcar(cabeceras, tipo):
    return _ok(client.post(f"{API}/auth/fichar", json={"tipo_evento": tipo}, headers=cabeceras))


def _retroceder(usuario_id, dias=1):
    """Lleva sus marcajes al pasado, como si hubieran ocurrido otro día."""
    db = SessionLocal()
    try:
        for registro in db.query(RegistroAsistencia).filter(RegistroAsistencia.usuario_id == usuario_id):
            registro.fecha_hora = registro.fecha_hora - timedelta(days=dias)
        db.commit()
    finally:
        db.close()


def _registros(usuario_id):
    return _ok(client.get(URL, params={"usuario_id": usuario_id}, headers=H))


def _corregir(usuario_id, tipo, fecha, motivo=MOTIVO, cabeceras=H):
    return client.post(f"{URL}/correcciones", json={
        "usuario_id": usuario_id, "tipo_evento": tipo,
        "fecha_hora": fecha.isoformat() if hasattr(fecha, "isoformat") else fecha, "motivo": motivo,
    }, headers=cabeceras)


def _hora(registro, **delta):
    return datetime.fromisoformat(registro["fecha_hora"]) + timedelta(**delta)


def _pendientes():
    return _ok(client.get(f"{URL}/jornadas-sin-salida", headers=H))


def test_corregir_una_salida_olvidada():
    usuario_id, c = _usuario()
    _marcar(c, "ENTRADA")
    _retroceder(usuario_id)
    entrada = _registros(usuario_id)[0]

    assert _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))["jornada_sin_salida"]
    pendiente = next(j for j in _pendientes() if j["usuario_id"] == usuario_id)
    assert pendiente["ultimo_evento"] == "ENTRADA" and pendiente["empleado_nombre"] == "Correccion Prueba"

    corregido = _ok(_corregir(usuario_id, "SALIDA", _hora(entrada, minutes=1)), 201)
    assert corregido["es_correccion"] is True and corregido["motivo_correccion"] == MOTIVO
    assert corregido["corregido_por_nombre"] and corregido["ip_registro"] is None, "La persona no marcó desde ningún equipo"

    assert _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))["jornada_sin_salida"] is None
    assert not [j for j in _pendientes() if j["usuario_id"] == usuario_id]

    original = next(r for r in _registros(usuario_id) if r["tipo_evento"] == "ENTRADA")
    assert original["es_correccion"] is False and original["fecha_hora"] == entrada["fecha_hora"], "El marcaje original no cambia"
    print("✔ Corrección: una salida olvidada cierra la jornada y conserva el marcaje original.")


def test_el_orden_debe_ser_posible():
    usuario_id, c = _usuario()
    _marcar(c, "ENTRADA")
    _marcar(c, "SALIDA")
    _retroceder(usuario_id)
    salida, entrada = _registros(usuario_id)

    casos = (
        ("ENTRADA", _hora(entrada, seconds=-60), "No puede haber otra entrada seguida de una entrada"),
        ("SALIDA", _hora(entrada, seconds=-60), "No puede salir antes de entrar"),
        ("FIN_DESCANSO", _hora(salida, seconds=60), "No hay descanso que terminar"),
        ("SALIDA", _hora(salida, seconds=60), "Ya salió"),
    )
    for tipo, fecha, explicacion in casos:
        res = _corregir(usuario_id, tipo, fecha)
        assert res.status_code == 409 and res.json()["detail"], f"{explicacion}: {res.status_code}"
    assert len(_registros(usuario_id)) == 2, "Una corrección rechazada no queda registrada"

    # Un turno más, después de la salida, sí es posible
    _ok(_corregir(usuario_id, "ENTRADA", _hora(salida, seconds=60)), 201)
    print("✔ Corrección: se rechaza si deja la jornada en un orden imposible.")


def test_agregar_un_descanso_en_medio():
    usuario_id, c = _usuario()
    _marcar(c, "ENTRADA")
    _marcar(c, "SALIDA")
    _retroceder(usuario_id)
    salida, entrada = _registros(usuario_id)
    medio = _hora(entrada) + (_hora(salida) - _hora(entrada)) / 2
    # Un inicio de descanso sin su fin dejaría una salida imposible
    assert _corregir(usuario_id, "INICIO_DESCANSO", medio).status_code == 409
    print("✔ Corrección: un descanso sin fin antes de la salida se rechaza.")


def test_entrada_olvidada_hoy_habilita_los_botones():
    usuario_id, c = _usuario()
    assert _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))["estado"] == "SIN_TURNO"
    _ok(_corregir(usuario_id, "ENTRADA", datetime.now(timezone.utc) - timedelta(seconds=30), "Olvidó marcar al llegar"), 201)
    estado = _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))
    assert estado["estado"] == "EN_TURNO" and "SALIDA" in estado["permitidos"]
    _marcar(c, "SALIDA")
    print("✔ Corrección: una entrada olvidada hoy permite seguir el turno.")


def test_validaciones():
    usuario_id, _ = _usuario()
    ahora = datetime.now(timezone.utc)
    assert _corregir(usuario_id, "ENTRADA", ahora + timedelta(hours=1)).status_code == 400, "No se corrige el futuro"
    assert _corregir(str(uuid4()), "ENTRADA", ahora - timedelta(hours=1)).status_code == 404
    for motivo in ("", "    "):
        assert _corregir(usuario_id, "ENTRADA", ahora - timedelta(hours=1), motivo).status_code == 422, "El motivo es obligatorio"
    assert _corregir(usuario_id, "ENTRADA", "2026-01-01T08:00:00").status_code == 422, "Sin zona horaria sería ambiguo"
    assert _corregir(usuario_id, "OTRO", ahora - timedelta(hours=1)).status_code == 422
    assert _registros(usuario_id) == []
    print("✔ Corrección: exige motivo, una fecha pasada y una persona existente.")


def test_solo_el_administrador():
    usuario_id, c = _usuario()
    ahora = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert client.get(f"{URL}/jornadas-sin-salida").status_code == 401
    assert client.post(f"{URL}/correcciones", json={}).status_code == 401
    for rol in ("DOCTOR", "RECEPCION", "ASISTENTE"):
        _, otro = _usuario(rol)
        assert client.get(f"{URL}/jornadas-sin-salida", headers=otro).status_code == 403
        assert _corregir(usuario_id, "ENTRADA", ahora, cabeceras=otro).status_code == 403
    assert _corregir(usuario_id, "ENTRADA", ahora, cabeceras=c).status_code == 403, "Tampoco la propia persona"
    print("✔ Corrección: solo el administrador corrige y ve las jornadas pendientes.")


def test_queda_en_auditoria():
    usuario_id, _ = _usuario()
    corregido = _ok(_corregir(usuario_id, "ENTRADA", datetime.now(timezone.utc) - timedelta(minutes=1), "Falló el equipo"), 201)
    registros = _ok(client.get(f"{API}/auditoria/?tabla_afectada=registro_asistencia", headers=H))
    registro = next(r for r in registros if r["registro_id"] == corregido["id"])
    assert registro["accion"] == "INSERT"
    assert registro["datos_nuevos"]["motivo"] == "Falló el equipo" and registro["datos_nuevos"]["tipo_evento"] == "ENTRADA"
    print("✔ Corrección: queda en la auditoría con su motivo.")


def test_jornada_cerrada_y_la_de_hoy_no_estan_pendientes():
    cerrada, c = _usuario()
    _marcar(c, "ENTRADA")
    _marcar(c, "SALIDA")
    _retroceder(cerrada)
    hoy, h = _usuario()
    _marcar(h, "ENTRADA")
    ids = {j["usuario_id"] for j in _pendientes()}
    assert cerrada not in ids and hoy not in ids, "Un turno abierto hoy sigue en curso"

    # Dos días sin salida de la misma persona aparecen por separado
    varias, v = _usuario()
    _marcar(v, "ENTRADA")
    _retroceder(varias, 3)
    _marcar(v, "ENTRADA")
    _retroceder(varias, 1)
    assert len([j for j in _pendientes() if j["usuario_id"] == varias]) == 2
    print("✔ Pendientes: solo jornadas de días anteriores sin salida, cada una por separado.")


if __name__ == "__main__":
    test_corregir_una_salida_olvidada()
    test_el_orden_debe_ser_posible()
    test_agregar_un_descanso_en_medio()
    test_entrada_olvidada_hoy_habilita_los_botones()
    test_validaciones()
    test_solo_el_administrador()
    test_queda_en_auditoria()
    test_jornada_cerrada_y_la_de_hoy_no_estan_pendientes()
    print("TODAS LAS PRUEBAS PASARON")
