import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu02_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-02")
    print("Creación de Nuevos Usuarios y Asignación de Roles")
    print("==================================================")

    # 1. Autenticación como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✔ [Escenario 0] Login de Administrador autenticado.")

    # Obtener roles para conocer los IDs
    roles_res = client.get("/api/v1/usuarios/roles", headers=admin_headers)
    assert roles_res.status_code == 200
    roles = {r["codigo"]: r["id"] for r in roles_res.json()}

    import uuid
    suffix = uuid.uuid4().hex[:6]
    test_username = f"dr_roberto_{suffix}"
    test_email = f"roberto_{suffix}@clinica.com"

    # 2. Escenario 1: Registro exitoso de nuevo usuario con contraseña cifrada
    user_doctor_data = {
        "username": test_username,
        "email": test_email,
        "nombre": "Roberto",
        "apellido": "Silva",
        "telefono": "+591-70012345",
        "password": "PasswordSeguro2026*",
        "rol_id": roles["DOCTOR"],
        "doctor_perfil": {
            "especialidad": "Ortodoncia y Ortopedia Maxilar",
            "numero_colegiatura": "COL-OD-4589",
            "color_agenda": "#10B981"
        }
    }
    crear_res = client.post("/api/v1/usuarios/", json=user_doctor_data, headers=admin_headers)
    assert crear_res.status_code == 201, f"Error creando usuario: {crear_res.text}"
    user_creado = crear_res.json()
    assert user_creado["username"] == test_username
    assert user_creado["activo"] is True
    assert "password" not in user_creado # La contraseña nunca se expone
    assert user_creado["doctor_perfil"] is not None
    assert user_creado["doctor_perfil"]["especialidad"] == "Ortodoncia y Ortopedia Maxilar"
    user_id = user_creado["id"]
    print("✔ [Escenario 1] Usuario creado exitosamente con contraseña cifrada y perfil asignado.")

    # 3. Escenario 2: Rechazo de duplicados (username y email)
    # Intento 1: Mismo username
    dup_username = user_doctor_data.copy()
    dup_username["email"] = f"otro_{suffix}@clinica.com"
    res_dup1 = client.post("/api/v1/usuarios/", json=dup_username, headers=admin_headers)
    assert res_dup1.status_code == 400
    assert "nombre de usuario ya está en uso" in res_dup1.json()["detail"]

    # Intento 2: Mismo email
    dup_email = user_doctor_data.copy()
    dup_email["username"] = f"otro_{suffix}"
    res_dup2 = client.post("/api/v1/usuarios/", json=dup_email, headers=admin_headers)
    assert res_dup2.status_code == 400
    assert "correo electrónico ya está registrado" in res_dup2.json()["detail"]
    print("✔ [Escenario 2] Validaciones de unicidad de username y email pasaron con 400 Bad Request.")

    # 4. Escenario 3: Inicio de sesión del nuevo usuario creado
    login_nuevo = client.post("/api/v1/auth/login", data={"username": test_username, "password": "PasswordSeguro2026*"})
    assert login_nuevo.status_code == 200
    doctor_token = login_nuevo.json()["access_token"]
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

    me_res = client.get("/api/v1/auth/me", headers=doctor_headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == test_username
    assert me_res.json()["rol"] == "DOCTOR"
    print("✔ [Escenario 3] Inicio de sesión y verificación de sesión del nuevo doctor verificada.")

    # 5. Escenario 4: Desactivación preventiva y bloqueo de acceso inmediato
    # El Administrador desactiva al doctor (activo = false)
    update_res = client.put(f"/api/v1/usuarios/{user_id}", json={"activo": False}, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["activo"] is False
    print("✔ [Escenario 4] Usuario desactivado por el Administrador (activo: false).")

    # Intentar hacer login con cuenta desactivada
    login_bloqueado = client.post("/api/v1/auth/login", data={"username": test_username, "password": "PasswordSeguro2026*"})
    assert login_bloqueado.status_code == 403
    assert "inactivo" in login_bloqueado.json()["detail"].lower()
    print("✔ [Escenario 4] Intento de login de usuario desactivado rechazado con 403 Forbidden.")

    # Intentar usar el token previo emitido
    intento_token = client.get("/api/v1/auth/me", headers=doctor_headers)
    assert intento_token.status_code == 403
    assert "inactivo" in intento_token.json()["detail"].lower()
    print("✔ [Escenario 4] Token previo de usuario desactivado revocado con 403 Forbidden.")

    print("\n==================================================")
    print("¡TODOS LOS CRITERIOS DE ACEPTACIÓN DE HU-02 PASARON CON ÉXITO!")
    print("==================================================")

if __name__ == "__main__":
    test_hu02_completo()
