import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu03_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-03")
    print("Registro y Ficha Médica Integral de Pacientes")
    print("==================================================")

    # 1. Login como Recepcionista o Admin
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    import random
    rand_doc = f"CI-{random.randint(1000000, 9999999)}"
    rand_email = f"valeria.{random.randint(1000, 9999)}@gmail.com"

    # 2. Escenario 1: Registro de paciente con anamnesis inicial en una sola transacción
    paciente_nuevo = {
        "nombres": "Valeria",
        "apellidos": "Rojas Morales",
        "tipo_documento": "CI",
        "numero_documento": rand_doc,
        "fecha_nacimiento": "1994-08-22",
        "genero": "FEMENINO",
        "telefono": "+591-71234567",
        "email": rand_email,
        "direccion": "Av. Las Américas #450, Edif. Los Pinos Apto 3B",
        "ocupacion": "Arquitecta",
        "contacto_emergencia_nombre": "Carlos Rojas (Padre)",
        "contacto_emergencia_telefono": "+591-72345678",
        "antecedentes": {
            "enfermedades_sistemicas": "Hipertensión controlada",
            "alergias": "Alérgica a la Penicilina y AINES (Ibuprofeno)",
            "medicamentos_actuales": "Losartán 50mg/día",
            "cirugias_previas": "Apendicectomía (2018)",
            "fuma": False,
            "embarazada": False,
            "observaciones": "Paciente ansiosa ante el torno dental, requiere anestesia profunda sin epinefrina"
        }
    }
    crear_res = client.post("/api/v1/pacientes/", json=paciente_nuevo, headers=headers)
    assert crear_res.status_code == 201, f"Error al crear paciente: {crear_res.text}"
    paciente_creado = crear_res.json()
    paciente_id = paciente_creado["id"]
    assert paciente_creado["nombres"] == "Valeria"
    assert paciente_creado["numero_documento"] == rand_doc
    assert paciente_creado["antecedentes"] is not None
    assert "Penicilina" in paciente_creado["antecedentes"]["alergias"]
    print("✔ [Escenario 1] Paciente y antecedentes médicos persistidos simultáneamente con éxito.")

    # 3. Escenario 2: Rechazo de documento duplicado
    dup_res = client.post("/api/v1/pacientes/", json=paciente_nuevo, headers=headers)
    assert dup_res.status_code == 400
    assert "Ya existe un paciente registrado con el documento" in dup_res.json()["detail"]
    print("✔ [Escenario 2] Validación de unicidad de documento cumplida (HTTP 400 Bad Request).")

    # 4. Escenario 3: Búsqueda ágil de pacientes por coincidencia parcial
    busqueda_res = client.get("/api/v1/pacientes/?q=rojas", headers=headers)
    assert busqueda_res.status_code == 200
    encontrados = busqueda_res.json()
    assert len(encontrados) >= 1
    assert any(p["numero_documento"] == rand_doc for p in encontrados)

    busqueda_doc = client.get(f"/api/v1/pacientes/?q={rand_doc.split('-')[-1]}", headers=headers)
    assert busqueda_doc.status_code == 200
    assert len(busqueda_doc.json()) >= 1
    print("✔ [Escenario 3] Búsqueda predictiva por nombre, apellido y documento validada.")

    # 5. Escenario 4: Auditoría de visualización (Acción VIEW)
    # Contar logs antes de la consulta
    audit_antes = client.get("/api/v1/auditoria/?accion=VIEW&tabla_afectada=pacientes", headers=headers).json()
    conteo_antes = len(audit_antes)

    # Abrir la ficha del paciente
    ficha_res = client.get(f"/api/v1/pacientes/{paciente_id}", headers=headers)
    assert ficha_res.status_code == 200
    assert ficha_res.json()["nombres"] == "Valeria"

    # Verificar que se emitió el log VIEW
    audit_despues = client.get("/api/v1/auditoria/?accion=VIEW&tabla_afectada=pacientes", headers=headers).json()
    assert len(audit_despues) >= conteo_antes + 1 or audit_despues[0]["registro_id"] == paciente_id
    ultimo_log = audit_despues[0]
    assert ultimo_log["accion"] == "VIEW"
    assert ultimo_log["tabla_afectada"] == "pacientes"
    assert str(ultimo_log["registro_id"]) == paciente_id
    assert ultimo_log["seccion_consultada"] == "FICHA_DATOS_PERSONALES"
    print("✔ [Escenario 4] Auditoría automática de visualización médica (VIEW) certificada.")

    # 6. Escenario 5: Actualización de antecedentes médicos
    nuevas_alertas = {
        "alergias": "Penicilina, Ibuprofeno y Látex",
        "medicamentos_actuales": "Losartán 50mg, Complejo B",
        "observaciones": "Usar guantes de nitrilo obligatoriamente"
    }
    ant_res = client.put(f"/api/v1/pacientes/{paciente_id}/antecedentes", json=nuevas_alertas, headers=headers)
    assert ant_res.status_code == 200
    assert "Látex" in ant_res.json()["alergias"]
    print("✔ [Escenario 5] Actualización de alertas médicas y alergias críticas verificada.")

    # 7. Escenario 6: Consulta en tiempo real de saldo y estado de cuenta financiero
    saldo_inicial = client.get(f"/api/v1/pacientes/{paciente_id}/saldo", headers=headers).json()
    assert saldo_inicial["total_presupuestado"] == 0.0
    assert saldo_inicial["total_pagado"] == 0.0
    assert saldo_inicial["saldo_pendiente"] == 0.0
    assert saldo_inicial["estado_saldo"] == "AL_DIA"
    print(f"✔ [Escenario 6] Estado financiero en vivo verificado: {saldo_inicial['estado_saldo']} ($0.00).")

    print("\n==================================================")
    print("¡TODOS LOS CRITERIOS DE ACEPTACIÓN DE HU-03 PASARON CON ÉXITO!")
    print("==================================================")

if __name__ == "__main__":
    test_hu03_completo()
