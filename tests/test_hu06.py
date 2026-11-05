import sys
import os
from datetime import datetime, timezone, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu06_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-06")
    print("Control de Asistencia y Fichaje Laboral")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200, f"Error login admin: {login_admin.text}"
    token_admin = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    print("✔ [Escenario 0] Admin autenticado con éxito.")

    # 2. Asegurar la existencia de un usuario DOCTOR y un usuario ASISTENTE
    # Obtener rol DOCTOR y ASISTENTE
    roles_res = client.get("/api/v1/usuarios/roles", headers=headers_admin)
    assert roles_res.status_code == 200
    roles = {r["codigo"]: r["id"] for r in roles_res.json()}
    rol_doctor_id = roles.get("DOCTOR")
    rol_asistente_id = roles.get("ASISTENTE")

    # Usuario Doctor
    doc_username = "dr_hu06_fichaje"
    doc_password = "DoctorPassword123"
    doc_login = client.post("/api/v1/auth/login", data={"username": doc_username, "password": doc_password})
    if doc_login.status_code != 200:
        # Creamos al doctor
        doc_data = {
            "rol_id": rol_doctor_id,
            "username": doc_username,
            "password": doc_password,
            "nombre": "Esteban",
            "apellido": "Vargas",
            "email": "dr_hu06@clinica.com",
            "telefono": "+59171122334"
        }
        res_create_doc = client.post("/api/v1/usuarios/", json=doc_data, headers=headers_admin)
        assert res_create_doc.status_code == 201
        doc_user_id = res_create_doc.json()["id"]

        # Perfil de doctor
        client.post("/api/v1/usuarios/doctores/perfil", json={
            "usuario_id": doc_user_id,
            "especialidad": "Endodoncia",
            "numero_colegiatura": "COL-HU06-123"
        }, headers=headers_admin)

        doc_login = client.post("/api/v1/auth/login", data={"username": doc_username, "password": doc_password})
        assert doc_login.status_code == 200

    token_doc = doc_login.json()["access_token"]
    headers_doc = {"Authorization": f"Bearer {token_doc}"}
    doc_me = client.get("/api/v1/auth/me", headers=headers_doc).json()
    doc_user_id = doc_me["id"]
    print(f"✔ [Setup] Doctor disponible: {doc_username} (ID: {doc_user_id})")

    # Usuario Asistente
    asist_username = "asist_hu06_fichaje"
    asist_password = "AsistPassword123"
    asist_login = client.post("/api/v1/auth/login", data={"username": asist_username, "password": asist_password})
    if asist_login.status_code != 200:
        asist_data = {
            "rol_id": rol_asistente_id,
            "username": asist_username,
            "password": asist_password,
            "nombre": "Carla",
            "apellido": "Mendoza",
            "email": "asist_hu06@clinica.com",
            "telefono": "+59172233445"
        }
        res_create_asist = client.post("/api/v1/usuarios/", json=asist_data, headers=headers_admin)
        assert res_create_asist.status_code == 201
        asist_user_id = res_create_asist.json()["id"]

        client.post("/api/v1/usuarios/asistentes/perfil", json={
            "usuario_id": asist_user_id,
            "notas": "Asistente dental turno mañana"
        }, headers=headers_admin)

        asist_login = client.post("/api/v1/auth/login", data={"username": asist_username, "password": asist_password})
        assert asist_login.status_code == 200

    token_asist = asist_login.json()["access_token"]
    headers_asist = {"Authorization": f"Bearer {token_asist}"}
    asist_me = client.get("/api/v1/auth/me", headers=headers_asist).json()
    asist_user_id = asist_me["id"]
    print(f"✔ [Setup] Asistente disponible: {asist_username} (ID: {asist_user_id})")

    # =========================================================================
    # ESCENARIO 1: Fichaje de entrada, descansos y salida del Doctor
    # =========================================================================
    eventos = [
        ("ENTRADA", "Inicio de jornada matutina"),
        ("INICIO_DESCANSO", "Almuerzo"),
        ("FIN_DESCANSO", "Regreso de almuerzo"),
        ("SALIDA", "Fin de jornada diaria")
    ]
    for tipo, obs in eventos:
        payload = {"tipo_evento": tipo, "observaciones": obs}
        res_fichar = client.post("/api/v1/auth/fichar", json=payload, headers=headers_doc)
        assert res_fichar.status_code == 200, f"Error al fichar {tipo}: {res_fichar.text}"
        data = res_fichar.json()
        assert data["tipo_evento"] == tipo
        assert data["usuario_id"] == doc_user_id
        assert data["fecha_hora"] is not None
        assert data["observaciones"] == obs
        print(f"✔ [Escenario 1] Doctor fichó evento '{tipo}' con marca de tiempo e IP registradas.")

    # =========================================================================
    # ESCENARIO 2: Asistente realiza su fichaje de entrada
    # =========================================================================
    payload_asist = {"tipo_evento": "ENTRADA", "observaciones": "Llegada turno regular"}
    res_asist_fichar = client.post("/api/v1/auth/fichar", json=payload_asist, headers=headers_asist)
    assert res_asist_fichar.status_code == 200
    assert res_asist_fichar.json()["usuario_id"] == asist_user_id
    print("✔ [Escenario 2] Asistente fichó su 'ENTRADA'.")

    # =========================================================================
    # ESCENARIO 3: Restricción de visibilidad (Empleado solo ve sus propios fichajes)
    # =========================================================================
    res_asist_list = client.get("/api/v1/personal/asistencia", headers=headers_asist)
    assert res_asist_list.status_code == 200
    asist_fichajes = res_asist_list.json()
    assert len(asist_fichajes) > 0
    # Ningún fichaje debe pertenecer al doctor
    for reg in asist_fichajes:
        assert reg["usuario_id"] == asist_user_id, "Un asistente no debe ver fichajes de otros empleados"
    print("✔ [Escenario 3] Aislamiento de privacidad comprobado: Asistente solo ve sus propios registros.")

    # Lo mismo para el Doctor: solo ve sus fichajes
    res_doc_list = client.get("/api/v1/personal/asistencia", headers=headers_doc)
    assert res_doc_list.status_code == 200
    doc_fichajes = res_doc_list.json()
    assert len(doc_fichajes) >= 4
    for reg in doc_fichajes:
        assert reg["usuario_id"] == doc_user_id, "Un doctor no debe ver fichajes de otros empleados"
    print("✔ [Escenario 3] Aislamiento de privacidad comprobado: Doctor solo ve sus propios registros.")

    # =========================================================================
    # ESCENARIO 4: Administrador supervisa y filtra asistencias globales
    # =========================================================================
    # 4.1 Admin consulta todos los fichajes de la clínica
    res_admin_all = client.get("/api/v1/personal/asistencia", headers=headers_admin)
    assert res_admin_all.status_code == 200
    all_registros = res_admin_all.json()
    usuarios_en_lista = {r["usuario_id"] for r in all_registros}
    assert doc_user_id in usuarios_en_lista, "Admin debe ver los fichajes del doctor"
    assert asist_user_id in usuarios_en_lista, "Admin debe ver los fichajes del asistente"
    print(f"✔ [Escenario 4.1] Admin tiene acceso global a todos los fichajes ({len(all_registros)} encontrados).")

    # 4.2 Admin filtra específicamente por doctor_user_id
    res_admin_filter_doc = client.get(f"/api/v1/personal/asistencia?usuario_id={doc_user_id}", headers=headers_admin)
    assert res_admin_filter_doc.status_code == 200
    for reg in res_admin_filter_doc.json():
        assert reg["usuario_id"] == doc_user_id
    print("✔ [Escenario 4.2] Filtro por usuario específico verificado para Administrador.")

    # 4.3 Admin filtra por rango de fechas
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = (ahora + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_admin_fechas = client.get(f"/api/v1/personal/asistencia?fecha_desde={desde}&fecha_hasta={hasta}", headers=headers_admin)
    assert res_admin_fechas.status_code == 200, f"Error filtrando por fechas: {res_admin_fechas.text}"
    assert len(res_admin_fechas.json()) >= 5
    print("✔ [Escenario 4.3] Filtro por rango temporal verificado para Administrador.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-06 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu06_completo()
