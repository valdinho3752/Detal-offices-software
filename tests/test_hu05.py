import sys
import os
import random
from datetime import date, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Fechas lejanas y aleatorias: la agenda rechaza citas superpuestas y la suite debe poder repetirse
DIA_BASE = date(2031, 1, 1) + timedelta(days=random.randint(0, 3650) * 5)
DIA_1, DIA_2, DIA_3 = (DIA_BASE + timedelta(days=i) for i in range(3))

def test_hu05_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-05")
    print("Agendamiento de Citas y Control de Flujo de Sillón")
    print("==================================================")

    # 1. Autenticación Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Doctor y Paciente
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0, "Debe existir al menos un paciente"
    paciente_id = pacientes_res.json()[0]["id"]

    doctores_res = client.get("/api/v1/usuarios/doctores/lista", headers=headers)
    assert len(doctores_res.json()) > 0, "Debe existir al menos un doctor"
    doctor_id = doctores_res.json()[0]["id"]

    # 3. Asegurar que existe un ítem en plan de tratamiento marcado como PROXIMA_SESION
    planes_res = client.get(f"/api/v1/tratamientos/planes?paciente_id={paciente_id}", headers=headers)
    assert planes_res.status_code == 200, f"Error listando planes: {planes_res.text}"
    planes = planes_res.json()
    item_plan_id = None
    if isinstance(planes, list):
        for p in planes:
            for item in p.get("items", []):
                if item["estado"] == "PROXIMA_SESION":
                    item_plan_id = item["id"]
                    break
            if item_plan_id:
                break

    if not item_plan_id:
        # Creamos un plan y un item rápido para asociar
        nuevo_plan = {
            "paciente_id": paciente_id,
            "doctor_id": doctor_id,
            "titulo": "Plan para prueba de cita HU-05"
        }
        res_plan = client.post("/api/v1/tratamientos/planes", json=nuevo_plan, headers=headers)
        assert res_plan.status_code == 201, f"Error creando plan: {res_plan.text}"
        plan_id = res_plan.json()["id"]

        cat_res = client.get("/api/v1/tratamientos/catalogo", headers=headers)
        catalogo_id = cat_res.json()[0]["id"]

        nuevo_item = {
            "plan_id": plan_id,
            "catalogo_tratamiento_id": catalogo_id,
            "pieza_fdi": 16,
            "orden_secuencia": 1,
            "costo_acordado": 90.00,
            "observaciones": "Procedimiento agendado para próxima cita"
        }
        res_item = client.post("/api/v1/tratamientos/items", json=nuevo_item, headers=headers)
        assert res_item.status_code == 201, f"Error creando item: {res_item.text}"
        item_plan_id = res_item.json()["id"]

        # Marcar item como PROXIMA_SESION
        client.put(f"/api/v1/tratamientos/items/{item_plan_id}", json={"estado": "PROXIMA_SESION"}, headers=headers)

    print(f"✔ [Setup] Ítem en plan de tratamiento listo: {item_plan_id}")

    # =========================================================================
    # ESCENARIO 1: Agendamiento con enlace a procedimiento planificado
    # =========================================================================
    cita_payload = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "item_plan_id": item_plan_id,
        "fecha_inicio_programada": f"{DIA_1}T10:00:00Z",
        "fecha_fin_programada": f"{DIA_1}T11:00:00Z",
        "motivo_consulta": "Endodoncia pieza 16 - Sesión 1",
        "notas_adicionales": "Paciente hipertenso controlado"
    }
    res_cita = client.post("/api/v1/citas/", json=cita_payload, headers=headers)
    assert res_cita.status_code == 201, f"Error al agendar cita: {res_cita.text}"
    cita_data = res_cita.json()
    cita_id = cita_data["id"]
    assert cita_data["estado"] == "PROGRAMADA"
    assert cita_data["item_plan_id"] == item_plan_id
    assert cita_data["duracion_sillon_minutos"] is None
    print(f"✔ [Escenario 1] Cita agendada exitosamente (ID: {cita_id}) en estado PROGRAMADA vinculada al ítem {item_plan_id}.")

    # =========================================================================
    # ESCENARIO 2: Recepción del paciente en sala de espera
    # =========================================================================
    llegada_payload = {
        "hora_llegada_recepcion": "2026-10-24T09:50:00Z",
        "estado": "EN_ESPERA"
    }
    res_llegada = client.patch(f"/api/v1/citas/{cita_id}/sillon", json=llegada_payload, headers=headers)
    assert res_llegada.status_code == 200, f"Error actualizando llegada: {res_llegada.text}"
    data_llegada = res_llegada.json()
    assert data_llegada["estado"] == "EN_ESPERA"
    assert data_llegada["hora_llegada_recepcion"] is not None
    print("✔ [Escenario 2] Paciente recibido en sala de espera. Estado: EN_ESPERA con hora de recepción.")

    # =========================================================================
    # ESCENARIO 3: Entrada del paciente al box (Inicio en sillón)
    # =========================================================================
    inicio_sillon_payload = {
        "hora_inicio_sillon": "2026-10-24T10:05:00Z",
        "estado": "EN_SILLON"
    }
    res_inicio = client.patch(f"/api/v1/citas/{cita_id}/sillon", json=inicio_sillon_payload, headers=headers)
    assert res_inicio.status_code == 200, f"Error inicio de sillón: {res_inicio.text}"
    data_inicio = res_inicio.json()
    assert data_inicio["estado"] == "EN_SILLON"
    assert data_inicio["hora_inicio_sillon"] is not None
    print("✔ [Escenario 3] Paciente ingresó al gabinete. Estado: EN_SILLON con timestamp registrado.")

    # =========================================================================
    # ESCENARIO 4: Finalización de la atención y cálculo automático del tiempo en sillón
    # =========================================================================
    fin_sillon_payload = {
        "hora_fin_sillon": "2026-10-24T10:50:00Z",  # Exactamente 45 minutos después
        "estado": "FINALIZADA"
    }
    res_fin = client.patch(f"/api/v1/citas/{cita_id}/sillon", json=fin_sillon_payload, headers=headers)
    assert res_fin.status_code == 200, f"Error fin de sillón: {res_fin.text}"
    data_fin = res_fin.json()
    assert data_fin["estado"] == "FINALIZADA"
    assert data_fin["hora_fin_sillon"] is not None
    # Verificación del trigger de PostgreSQL trg_calcular_duracion_sillon
    duracion = data_fin["duracion_sillon_minutos"]
    assert duracion == 45, f"Se esperaban 45 minutos calculados por trigger, se obtuvo: {duracion}"
    print(f"✔ [Escenario 4] Atención concluida. Estado: FINALIZADA. Duración calculada por Trigger: {duracion} minutos exactos.")

    # =========================================================================
    # ESCENARIO 5: Registro de inasistencia (NO_ASISTIO) y cancelación (CANCELADA)
    # =========================================================================
    # Cita 2 -> CANCELADA
    cita_canc_payload = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "fecha_inicio_programada": f"{DIA_2}T15:00:00Z",
        "fecha_fin_programada": f"{DIA_2}T16:00:00Z",
        "motivo_consulta": "Control de sensibilidad - Cancelada por el paciente"
    }
    res_c2 = client.post("/api/v1/citas/", json=cita_canc_payload, headers=headers)
    assert res_c2.status_code == 201
    c2_id = res_c2.json()["id"]

    res_cancelar = client.put(f"/api/v1/citas/{c2_id}", json={"estado": "CANCELADA", "notas_adicionales": "Aviso con 24h de anticipación"}, headers=headers)
    assert res_cancelar.status_code == 200
    assert res_cancelar.json()["estado"] == "CANCELADA"
    print("✔ [Escenario 5.1] Cita cancelada correctamente con estado CANCELADA.")

    # Cita 3 -> NO_ASISTIO
    cita_noasist_payload = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "fecha_inicio_programada": f"{DIA_3}T09:00:00Z",
        "fecha_fin_programada": f"{DIA_3}T10:00:00Z",
        "motivo_consulta": "Higiene y profilaxis - Inasistencia"
    }
    res_c3 = client.post("/api/v1/citas/", json=cita_noasist_payload, headers=headers)
    assert res_c3.status_code == 201
    c3_id = res_c3.json()["id"]

    res_noasist = client.put(f"/api/v1/citas/{c3_id}", json={"estado": "NO_ASISTIO", "notas_adicionales": "No respondió llamadas"}, headers=headers)
    assert res_noasist.status_code == 200
    assert res_noasist.json()["estado"] == "NO_ASISTIO"
    print("✔ [Escenario 5.2] Inasistencia registrada con estado NO_ASISTIO.")

    # =========================================================================
    # ESCENARIO 6: Filtros de la Agenda
    # =========================================================================
    filtro_canceladas = client.get(f"/api/v1/citas/?doctor_id={doctor_id}&estado=CANCELADA", headers=headers)
    assert filtro_canceladas.status_code == 200
    ids_canc = [c["id"] for c in filtro_canceladas.json()]
    assert c2_id in ids_canc

    filtro_noasist = client.get(f"/api/v1/citas/?doctor_id={doctor_id}&estado=NO_ASISTIO", headers=headers)
    assert filtro_noasist.status_code == 200
    ids_noasist = [c["id"] for c in filtro_noasist.json()]
    assert c3_id in ids_noasist

    filtro_fechas = client.get(f"/api/v1/citas/?doctor_id={doctor_id}&fecha_desde={DIA_1}T00:00:00Z", headers=headers)
    assert filtro_fechas.status_code == 200
    assert len(filtro_fechas.json()) >= 3
    print("✔ [Escenario 6] Filtros de agenda por Doctor, Fechas y Estados verificados exitosamente.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-05 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu05_completo()
