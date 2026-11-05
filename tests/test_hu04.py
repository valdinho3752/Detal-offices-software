import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu04_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-04")
    print("Odontograma Interactivo FDI y Planes Secuenciales")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener un Doctor y un Paciente existentes o crearlos
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0, "Debe existir al menos un paciente"
    paciente = pacientes_res.json()[0]
    paciente_id = paciente["id"]

    doctores_res = client.get("/api/v1/usuarios/doctores/lista", headers=headers)
    assert len(doctores_res.json()) > 0, "Debe existir al menos un doctor"
    doctor = doctores_res.json()[0]
    doctor_id = doctor["id"]

    # 3. Escenario 1: Inicialización automática de piezas dentales FDI (Adulto: 32 piezas 11-48)
    odontograma_adulto = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "tipo_denticion": "ADULTA_PERMANENTE",
        "tipo_registro": "INICIAL_INGRESO",
        "observaciones_generales": "Evaluación odontológica inicial. Presenta apiñamiento leve inferior."
    }
    res_odo = client.post("/api/v1/odontogramas/", json=odontograma_adulto, headers=headers)
    assert res_odo.status_code == 201, f"Error creando odontograma: {res_odo.text}"
    odo_data = res_odo.json()
    odontograma_id = odo_data["id"]
    piezas_adulto = odo_data["piezas"]
    assert len(piezas_adulto) == 32, f"Se esperaban 32 piezas dentales adultas, obtenidas: {len(piezas_adulto)}"
    fdis_adulto = [p["numero_fdi"] for p in piezas_adulto]
    assert 11 in fdis_adulto and 18 in fdis_adulto and 48 in fdis_adulto
    print(f"✔ [Escenario 1] Odontograma Adulto creado con las 32 piezas dentales FDI (11 al 48) generadas automáticamente.")

    # 4. Escenario 2: Inicialización automática para Odontograma Infantil (20 piezas 51-85)
    odontograma_infantil = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "tipo_denticion": "INFANTIL_DECIDUA",
        "tipo_registro": "INICIAL_INGRESO",
        "observaciones_generales": "Odontopediatría. Dentición temporal completa."
    }
    res_odo_ped = client.post("/api/v1/odontogramas/", json=odontograma_infantil, headers=headers)
    assert res_odo_ped.status_code == 201
    piezas_ped = res_odo_ped.json()["piezas"]
    assert len(piezas_ped) == 20, f"Se esperaban 20 piezas temporales, obtenidas: {len(piezas_ped)}"
    fdis_ped = [p["numero_fdi"] for p in piezas_ped]
    assert 51 in fdis_ped and 85 in fdis_ped
    print(f"✔ [Escenario 2] Odontograma Infantil creado con las 20 piezas de leche FDI (51 al 85) autogeneradas.")

    # 5. Escenario 3: Marcaje de patología en superficie con código de color (Rojo #FF0000)
    # Seleccionamos la pieza 16 (Primer Molar Superior Derecho)
    pieza_16 = next(p for p in piezas_adulto if p["numero_fdi"] == 16)
    pieza_16_id = pieza_16["id"]

    hallazgo_caries = {
        "pieza_dental_id": pieza_16_id,
        "superficie": "OCLUSAL_INCISAL",
        "condicion": "CARIES",
        "estado_clinico": "REQUERIDO_PATOLOGIA",
        "color_hex": "#FF0000",
        "detalle": "Caries profunda en fosa distal con dolor a la masticación"
    }
    res_hallazgo = client.post("/api/v1/odontogramas/hallazgos", json=hallazgo_caries, headers=headers)
    assert res_hallazgo.status_code == 201
    hallazgo_data = res_hallazgo.json()
    hallazgo_id = hallazgo_data["id"]
    assert hallazgo_data["color_hex"] == "#FF0000"
    print("✔ [Escenario 3] Caries registrada en cara oclusal de pieza 16 con color rojo (#FF0000).")

    # 6. Escenario 4: Creación de tratamientos en el catálogo
    t1_data = {
        "codigo": "REST-001",
        "categoria": "RESTAURADORA",
        "nombre": "Obturación con Resina Compuesta Fotocurable",
        "costo_base": 60.00,
        "duracion_estimada_min": 45,
        "activo": True
    }
    t2_data = {
        "codigo": "ENDO-001",
        "categoria": "ENDODONCIA",
        "nombre": "Tratamiento de Conducto Molar (Biopulpectomía)",
        "costo_base": 180.00,
        "duracion_estimada_min": 60,
        "activo": True
    }
    res_t1 = client.post("/api/v1/tratamientos/catalogo", json=t1_data, headers=headers)
    t1_id = res_t1.json()["id"] if res_t1.status_code == 201 else client.get("/api/v1/tratamientos/catalogo", headers=headers).json()[0]["id"]

    res_t2 = client.post("/api/v1/tratamientos/catalogo", json=t2_data, headers=headers)
    t2_id = res_t2.json()["id"] if res_t2.status_code == 201 else client.get("/api/v1/tratamientos/catalogo", headers=headers).json()[1]["id"]
    print("✔ [Escenario 4] Procedimientos del catálogo clínico asegurados.")

    # 7. Escenario 5: Creación de Plan de Tratamiento secuenciado a partir del odontograma
    plan_data = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "titulo": "Plan de Rehabilitación Integral Molar",
        "estado": "APROBADO",
        "items": [
            {
                "tratamiento_id": t2_id,
                "hallazgo_superficie_id": hallazgo_id,
                "pieza_fdi": 16,
                "orden_secuencia": 1,
                "costo_acordado": 180.00,
                "observaciones": "Paso 1: Endodoncia de urgencia para alivio del dolor"
            },
            {
                "tratamiento_id": t1_id,
                "hallazgo_superficie_id": None,
                "pieza_fdi": 16,
                "orden_secuencia": 2,
                "costo_acordado": 70.00,
                "observaciones": "Paso 2: Reconstrucción coronaria definitiva con resina"
            }
        ]
    }
    res_plan = client.post("/api/v1/tratamientos/planes", json=plan_data, headers=headers)
    assert res_plan.status_code == 201, f"Error creando plan: {res_plan.text}"
    plan_creado = res_plan.json()
    assert float(plan_creado["costo_total"]) == 250.00, f"Se esperaba costo total 250.00, obtenido {plan_creado['costo_total']}"
    assert len(plan_creado["items"]) == 2
    item_paso1_id = plan_creado["items"][0]["id"]
    print("✔ [Escenario 5] Plan de tratamiento secuencial (1º Endodoncia, 2º Resina) creado con costo total calculado ($250.00).")

    # 8. Escenario 6: Marcado de tratamiento para la siguiente sesión (PROXIMA_SESION)
    res_prox = client.put(f"/api/v1/tratamientos/items/{item_paso1_id}", json={"estado": "PROXIMA_SESION"}, headers=headers)
    assert res_prox.status_code == 200
    assert res_prox.json()["estado"] == "PROXIMA_SESION"
    print("✔ [Escenario 6] Procedimiento marcado explícitamente como PROXIMA_SESION para agendamiento futuro.")

    # 9. Escenario 7: Auditoría de visualización (Acción VIEW) al abrir el odontograma
    odo_get = client.get(f"/api/v1/odontogramas/{odontograma_id}", headers=headers)
    assert odo_get.status_code == 200
    audit_res = client.get("/api/v1/auditoria/?tabla_afectada=odontogramas&accion=VIEW", headers=headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1
    print("✔ [Escenario 7] Auditoría automática VIEW registrada al inspeccionar el odontograma interactivo.")

    print("\n==================================================")
    print("¡TODOS LOS CRITERIOS DE ACEPTACIÓN DE HU-04 PASARON CON ÉXITO!")
    print("==================================================")

if __name__ == "__main__":
    test_hu04_completo()
