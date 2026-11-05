"""
Reglas de marcaje de turnos, y nombre, logo y tema de la clínica.
Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import sys
from datetime import timedelta
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import RegistroAsistencia

client = TestClient(app)
API = "/api/v1"
URL = f"{API}/configuracion"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave):
    return {"Authorization": f"Bearer {_ok(client.post(f'{API}/auth/login', data={'username': usuario, 'password': clave}))['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}


def _usuario(rol="ASISTENTE"):
    nombre = f"fic_{uuid4().hex[:10]}"
    creado = _ok(client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": "Clave1234!", "nombre": "Fichaje", "apellido": "Prueba",
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H), 201)
    return creado["id"], _login(nombre, "Clave1234!")


def _estado(cabeceras):
    return _ok(client.get(f"{API}/auth/fichaje/estado", headers=cabeceras))


def _marcar(cabeceras, tipo):
    return client.post(f"{API}/auth/fichar", json={"tipo_evento": tipo}, headers=cabeceras)


TODOS = {"ENTRADA", "INICIO_DESCANSO", "FIN_DESCANSO", "SALIDA"}


def _comprobar_bloqueos(cabeceras, estado, permitidos):
    datos = _estado(cabeceras)
    assert datos["estado"] == estado and set(datos["permitidos"]) == set(permitidos), datos
    for tipo in TODOS - set(permitidos):
        res = _marcar(cabeceras, tipo)
        assert res.status_code == 409, f"{estado}: {tipo} debía rechazarse, respondió {res.status_code}"
        assert res.json()["detail"], "Debe explicar por qué"


def test_recorrido_del_turno():
    _, c = _usuario()
    _comprobar_bloqueos(c, "SIN_TURNO", {"ENTRADA"})
    _ok(_marcar(c, "ENTRADA"))
    _comprobar_bloqueos(c, "EN_TURNO", {"INICIO_DESCANSO", "SALIDA"})
    _ok(_marcar(c, "INICIO_DESCANSO"))
    _comprobar_bloqueos(c, "EN_DESCANSO", {"FIN_DESCANSO"})
    _ok(_marcar(c, "FIN_DESCANSO"))
    _comprobar_bloqueos(c, "EN_TURNO", {"INICIO_DESCANSO", "SALIDA"})
    _ok(_marcar(c, "INICIO_DESCANSO"))
    _ok(_marcar(c, "FIN_DESCANSO"))
    _ok(_marcar(c, "SALIDA"))
    _comprobar_bloqueos(c, "TURNO_CERRADO", {"ENTRADA"})
    _ok(_marcar(c, "ENTRADA"))
    _comprobar_bloqueos(c, "EN_TURNO", {"INICIO_DESCANSO", "SALIDA"})
    print("✔ Marcajes: cada estado solo permite el marcaje que corresponde.")


def test_un_rechazo_no_queda_registrado():
    usuario_id, c = _usuario()
    assert _marcar(c, "SALIDA").status_code == 409
    assert _ok(client.get(f"{API}/personal/asistencia?usuario_id={usuario_id}", headers=H)) == []
    print("✔ Marcajes: un marcaje rechazado no queda en la bitácora.")


def test_cada_persona_tiene_su_turno():
    _, a = _usuario()
    _, b = _usuario()
    _ok(_marcar(a, "ENTRADA"))
    assert _estado(b)["estado"] == "SIN_TURNO"
    _ok(_marcar(b, "ENTRADA"))
    print("✔ Marcajes: el turno de una persona no afecta a otra.")


def _mover_ultimo_marcaje(usuario_id, dias):
    db = SessionLocal()
    try:
        ultimo = db.query(RegistroAsistencia).filter(RegistroAsistencia.usuario_id == usuario_id).order_by(RegistroAsistencia.fecha_hora.desc()).first()
        ultimo.fecha_hora = ultimo.fecha_hora - timedelta(days=dias)
        db.commit()
    finally:
        db.close()


def test_jornada_anterior_sin_salida():
    usuario_id, c = _usuario()
    _ok(_marcar(c, "ENTRADA"))
    _mover_ultimo_marcaje(usuario_id, 1)
    datos = _estado(c)
    assert datos["estado"] == "SIN_TURNO" and datos["permitidos"] == ["ENTRADA"], "Olvidar la salida no bloquea el día siguiente"
    assert datos["jornada_sin_salida"], "Avisa que quedó una jornada abierta"
    _ok(_marcar(c, "ENTRADA"))
    assert _estado(c)["jornada_sin_salida"] is None

    otro_id, o = _usuario()
    _ok(_marcar(o, "ENTRADA"))
    _ok(_marcar(o, "SALIDA"))
    _mover_ultimo_marcaje(otro_id, 1)
    assert _estado(o)["jornada_sin_salida"] is None, "Una jornada cerrada no genera aviso"
    print("✔ Marcajes: una salida olvidada avisa, pero no impide trabajar al día siguiente.")


def test_bitacora_identifica_a_la_persona():
    usuario_id, c = _usuario("RECEPCION")
    _ok(_marcar(c, "ENTRADA"))
    registro = _ok(client.get(f"{API}/personal/asistencia?usuario_id={usuario_id}", headers=H))[0]
    assert registro["empleado_nombre"] == "Fichaje Prueba" and registro["empleado_rol"], registro
    assert registro["fecha_hora"] and registro["ip_registro"]
    print("✔ Bitácora: muestra la hora real, la persona, su rol y la IP.")


def test_permisos_de_estado():
    assert client.get(f"{API}/auth/fichaje/estado").status_code == 401
    print("✔ Marcajes: consultar el estado exige sesión.")


def test_nombre_y_tema():
    original = _ok(client.get(f"{URL}/", headers=H))
    try:
        for invalido in ({"nombre_clinica": "  "}, {"nombre_clinica": "x" * 121}, {"tema_por_defecto": "rojo"},
                         {"tema_por_defecto": None}, {"nombre_clinica": None}, {"moneda_simbolo": None}):
            assert client.put(f"{URL}/", json=invalido, headers=H).status_code == 422, invalido

        datos = _ok(client.put(f"{URL}/", json={"nombre_clinica": "  Sonrisas  ", "tema_por_defecto": "claro"}, headers=H))
        assert datos["nombre_clinica"] == "Sonrisas" and datos["tema_por_defecto"] == "claro"
        assert datos["moneda_simbolo"] == original["moneda_simbolo"], "Lo no enviado no cambia"

        publica = _ok(client.get(f"{URL}/publica"))
        assert publica["nombre_clinica"] == "Sonrisas" and publica["tema_por_defecto"] == "claro"
        assert "moneda_simbolo" not in publica, "Sin sesión solo se expone lo necesario para la pantalla de acceso"

        _, doctor = _usuario("DOCTOR")
        assert client.put(f"{URL}/", json={"nombre_clinica": "Otra"}, headers=doctor).status_code == 403
        registros = _ok(client.get(f"{API}/auditoria/?tabla_afectada=configuracion_clinica", headers=H))
        assert registros, "El cambio queda auditado"
    finally:
        _ok(client.put(f"{URL}/", json={"nombre_clinica": original["nombre_clinica"], "tema_por_defecto": original["tema_por_defecto"]}, headers=H))
    print("✔ Clínica: el nombre y el tema se validan, y solo el administrador los cambia.")


def _subir(contenido, cabeceras=H, nombre="logo.png", tipo="image/png"):
    return client.post(f"{URL}/logo", files={"archivo": (nombre, contenido, tipo)}, headers=cabeceras)


def test_logo():
    assert _ok(client.delete(f"{URL}/logo", headers=H))["logo_url"] is None
    assert client.get(f"{URL}/logo").status_code == 404
    assert _ok(client.get(f"{URL}/publica"))["logo_url"] is None

    _, doctor = _usuario("DOCTOR")
    assert _subir(PNG, doctor).status_code == 403
    assert client.delete(f"{URL}/logo", headers=doctor).status_code == 403
    assert client.post(f"{URL}/logo", files={"archivo": ("a.png", PNG, "image/png")}).status_code == 401

    # El contenido manda: no basta con el nombre o el tipo que declare el archivo
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for malo in (svg, b"no es una imagen", b""):
        assert _subir(malo).status_code == 400, malo[:20]
    assert _subir(PNG + b"\x00" * (1024 * 1024)).status_code == 413
    assert _ok(client.get(f"{URL}/publica"))["logo_url"] is None, "Un archivo rechazado no cambia nada"

    for contenido, tipo in ((PNG, "image/png"), (JPG, "image/jpeg"), (WEBP, "image/webp")):
        datos = _ok(_subir(contenido))
        res = client.get(datos["logo_url"].replace("/api/v1", API))
        assert res.status_code == 200 and res.content == contenido and res.headers["content-type"] == tipo
        assert res.headers["x-content-type-options"] == "nosniff"

    assert _ok(client.get(f"{URL}/publica"))["logo_url"], "Se ve sin iniciar sesión, en la pantalla de acceso"
    assert _ok(client.delete(f"{URL}/logo", headers=H))["logo_url"] is None
    assert client.get(f"{URL}/logo").status_code == 404
    print("✔ Logo: solo imágenes reales de hasta 1 MB, y solo el administrador lo cambia.")


if __name__ == "__main__":
    test_recorrido_del_turno()
    test_un_rechazo_no_queda_registrado()
    test_cada_persona_tiene_su_turno()
    test_jornada_anterior_sin_salida()
    test_bitacora_identifica_a_la_persona()
    test_permisos_de_estado()
    test_nombre_y_tema()
    test_logo()
    print("TODAS LAS PRUEBAS PASARON")
