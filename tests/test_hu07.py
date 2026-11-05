import sys
import os
from datetime import date, datetime, timezone, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu07_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-07")
    print("Evolución Clínica Diaria, Procedimientos y Recetas")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Paciente, Doctor y Asistente
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0
    paciente_id = pacientes_res.json()[0]["id"]

    doctores_res = client.get("/api/v1/usuarios/doctores/lista", headers=headers)
    assert len(doctores_res.json()) > 0
    doctor_id = doctores_res.json()[0]["id"]

    asistentes_res = client.get("/api/v1/usuarios/asistentes/lista", headers=headers)
    assert len(asistentes_res.json()) > 0
    asistente_id = asistentes_res.json()[0]["id"]

    # 3. Preparar Plan de Tratamiento con al menos dos ítems (uno para hoy y otro para la próxima sesión)
    cat_res = client.get("/api/v1/tratamientos/catalogo", headers=headers)
    assert len(cat_res.json()) >= 2
    cat_items = cat_res.json()
    cat_1_id = cat_items[0]["id"]
    cat_2_id = cat_items[1]["id"]

    nuevo_plan = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "titulo": "Plan para prueba de Evolución HU-07"
    }
    res_plan = client.post("/api/v1/tratamientos/planes", json=nuevo_plan, headers=headers)
    assert res_plan.status_code == 201
    plan_id = res_plan.json()["id"]

    # Ítem 1 (el que se realizará hoy)
    res_item1 = client.post("/api/v1/tratamientos/items", json={
        "plan_id": plan_id,
        "tratamiento_id": cat_1_id,
        "pieza_fdi": 16,
        "orden_secuencia": 1,
        "costo_acordado": 80.00,
        "observaciones": "Endodoncia Sesión 1"
    }, headers=headers)
    assert res_item1.status_code == 201, f"Error creando item 1: {res_item1.text}"
    item1_id = res_item1.json()["id"]
    # Lo ponemos en PROXIMA_SESION
    client.put(f"/api/v1/tratamientos/items/{item1_id}", json={"estado": "PROXIMA_SESION"}, headers=headers)

    # Ítem 2 (el que se realizará en la siguiente cita)
    res_item2 = client.post("/api/v1/tratamientos/items", json={
        "plan_id": plan_id,
        "tratamiento_id": cat_2_id,
        "pieza_fdi": 16,
        "orden_secuencia": 2,
        "costo_acordado": 120.00,
        "observaciones": "Reconstrucción con perno y composite"
    }, headers=headers)
    assert res_item2.status_code == 201, f"Error creando item 2: {res_item2.text}"
    item2_id = res_item2.json()["id"]

    # Agendar cita previa vinculada a item1
    res_cita = client.post("/api/v1/citas/", json={
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "item_plan_id": item1_id,
        "fecha_inicio_programada": "2026-10-24T16:00:00Z",
        "fecha_fin_programada": "2026-10-24T17:00:00Z",
        "motivo_consulta": "Conductometría e instrumentación pieza 16"
    }, headers=headers)
    assert res_cita.status_code == 201
    cita_id = res_cita.json()["id"]
    print(f"✔ [Setup] Plan con 2 ítems y Cita preparados (Plan: {plan_id}, Cita: {cita_id})")

    # =========================================================================
    # ESCENARIO 1: Registro de evolución diaria y avance automático de estados
    # =========================================================================
    proximo_control = (date.today() + timedelta(days=7)).isoformat()
    visita_payload = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "asistente_id": asistente_id,
        "cita_id": cita_id,
        "item_plan_id": item1_id,
        "proximo_item_plan_id": item2_id,
        "motivo_visita": "Continuación de tratamiento endodóntico pieza 16",
        "diagnostico": "Pulpitis irreversible sintomática tratada",
        "procedimiento_realizado": "Apertura cameral, localización de 3 conductos (MV, DV, P), instrumentación rotatoria hasta calibre 25/06, irrigación copiosa con NaOCl al 2.5%, medicación intracanal con hidróxido de calcio y sellado provisional con Cavit.",
        "receta_medicamentos": "1. Ibuprofeno 600mg: 1 comprimido cada 8 horas por 3 días en caso de dolor.\n2. Amoxicilina 500mg: 1 cápsula cada 8 horas por 7 días.",
        "recomendaciones": "No masticar alimentos duros del lado derecho. Evitar cambios bruscos de temperatura.",
        "fecha_proximo_control": proximo_control,
        "indicaciones_proxima_visita": "Obturación definitiva de conductos con conos de gutapercha y cemento sellador."
    }

    res_visita = client.post("/api/v1/visitas/", json=visita_payload, headers=headers)
    assert res_visita.status_code == 201, f"Error registrando visita: {res_visita.text}"
    visita_data = res_visita.json()
    visita_id = visita_data["id"]
    assert visita_data["diagnostico"] == visita_payload["diagnostico"]
    assert visita_data["asistente_id"] == asistente_id
    print(f"✔ [Escenario 1.1] Visita de evolución clínica registrada con éxito (ID: {visita_id}).")

    # Verificación del avance de estados de los ítems del plan:
    # 1. El ítem ejecutado hoy debe estar en COMPLETADO
    planes_check = client.get(f"/api/v1/tratamientos/planes?paciente_id={paciente_id}", headers=headers).json()
    item1_estado = None
    item2_estado = None
    for p in planes_check:
        if p["id"] == plan_id:
            for it in p["items"]:
                if it["id"] == item1_id:
                    item1_estado = it["estado"]
                elif it["id"] == item2_id:
                    item2_estado = it["estado"]

    assert item1_estado == "COMPLETADO", f"El ítem realizado hoy debería ser COMPLETADO, obtenido: {item1_estado}"
    assert item2_estado == "PROXIMA_SESION", f"El ítem siguiente debería ser PROXIMA_SESION, obtenido: {item2_estado}"
    print(f"✔ [Escenario 1.2] Avance de fases verificado: Ítem 1 -> {item1_estado}, Ítem 2 -> {item2_estado}.")

    # =========================================================================
    # ESCENARIO 2: Consulta médica y Auditoría de visualización (VIEW)
    # =========================================================================
    res_get_visita = client.get(f"/api/v1/visitas/{visita_id}", headers=headers)
    assert res_get_visita.status_code == 200
    nota_consultada = res_get_visita.json()
    assert "Ibuprofeno" in nota_consultada["receta_medicamentos"]
    assert "instrumentación rotatoria" in nota_consultada["procedimiento_realizado"]

    # Verificar registro en auditoria_logs
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=visitas_evolucion", headers=headers)
    assert res_audit.status_code == 200, f"Error consultando auditoria: {res_audit.text}"
    logs = res_audit.json()
    view_logs = [l for l in logs if l["registro_id"] == visita_id and l["accion"] == "VIEW"]
    insert_logs = [l for l in logs if l["registro_id"] == visita_id and l["accion"] == "INSERT"]

    assert len(insert_logs) >= 1, "Debe existir log INSERT para la creación de la visita"
    assert len(view_logs) >= 1, "Debe existir log VIEW para la lectura del expediente"
    assert view_logs[0]["seccion_consultada"] == "HISTORIA_CLINICA_SESION"
    print(f"✔ [Escenario 2] Auditoría legal confirmada: Log VIEW emitido para seccion='HISTORIA_CLINICA_SESION'.")

    # =========================================================================
    # ESCENARIO 3: Listado de evoluciones del paciente y actualización
    # =========================================================================
    res_lista_paciente = client.get(f"/api/v1/visitas/?paciente_id={paciente_id}", headers=headers)
    assert res_lista_paciente.status_code == 200
    ids_visitas = [v["id"] for v in res_lista_paciente.json()]
    assert visita_id in ids_visitas
    print(f"✔ [Escenario 3.1] Listado cronológico de evoluciones del paciente validado.")

    # Actualización menor de notas
    update_payload = {"recomendaciones": "No masticar alimentos duros. Control de dolor favorable."}
    res_update = client.put(f"/api/v1/visitas/{visita_id}", json=update_payload, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["recomendaciones"] == update_payload["recomendaciones"]
    print("✔ [Escenario 3.2] Actualización de notas clínicas efectuada correctamente.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-07 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu07_completo()
