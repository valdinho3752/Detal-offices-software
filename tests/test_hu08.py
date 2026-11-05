import sys
import os
from datetime import date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu08_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-08")
    print("Gestión y Visor de Radiografías e Imágenes Dentales")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token_admin = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token_admin}"}
    admin_id = login_admin.json().get("user_id")
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Paciente
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0
    paciente_id = pacientes_res.json()[0]["id"]
    print(f"✔ [Setup] Paciente seleccionado: {paciente_id}")

    # =========================================================================
    # ESCENARIO 1: Subida de radiografías con metadatos clínicos
    # =========================================================================
    # 1.1 Radiografía Panorámica general
    rx_panoramica = {
        "paciente_id": paciente_id,
        "tipo_estudio": "PANORAMICA",
        "titulo": "Ortopantomografía diagnóstica inicial",
        "archivo_url": "https://storage.clinicagustavo.com/radiografias/rx_panoramica_001.jpg",
        "mime_type": "image/jpeg",
        "tamano_bytes": 2048500,
        "informe_diagnostico": "Se observa reabsorción ósea horizontal leve generalizada. Ausencia de pieza 38. Diente 16 con compromiso cameral.",
        "fecha_toma": date.today().isoformat()
    }
    res_pan = client.post("/api/v1/radiografias/", json=rx_panoramica, headers=headers)
    assert res_pan.status_code == 201, f"Error subiendo panorámica: {res_pan.text}"
    pan_data = res_pan.json()
    pan_id = pan_data["id"]
    assert pan_data["tipo_estudio"] == "PANORAMICA"
    assert pan_data["pieza_fdi"] is None
    print(f"✔ [Escenario 1.1] Radiografía Panorámica subida exitosamente (ID: {pan_id}).")

    # 1.2 Radiografía Periapical vinculada a pieza dental FDI 16
    rx_periapical = {
        "paciente_id": paciente_id,
        "pieza_fdi": 16,
        "tipo_estudio": "PERIAPICAL",
        "titulo": "Radiografía Periapical pieza 16 (Pre-endodoncia)",
        "archivo_url": "https://storage.clinicagustavo.com/radiografias/rx_periapical_16_pre.jpg",
        "mime_type": "image/jpeg",
        "tamano_bytes": 850200,
        "informe_diagnostico": "Se evidencia radiolucidez periapical en raíz mesiovestibular compatible con periodontitis apical crónica.",
        "fecha_toma": date.today().isoformat()
    }
    res_peri = client.post("/api/v1/radiografias/", json=rx_periapical, headers=headers)
    assert res_peri.status_code == 201, f"Error subiendo periapical: {res_peri.text}"
    peri_data = res_peri.json()
    peri_id = peri_data["id"]
    assert peri_data["pieza_fdi"] == 16
    assert peri_data["tipo_estudio"] == "PERIAPICAL"
    print(f"✔ [Escenario 1.2] Radiografía Periapical de pieza FDI 16 subida exitosamente (ID: {peri_id}).")

    # =========================================================================
    # ESCENARIO 2: Filtrado por Paciente y por Pieza Dental FDI
    # =========================================================================
    # 2.1 Todas las radiografías del paciente
    res_todas = client.get(f"/api/v1/radiografias/?paciente_id={paciente_id}", headers=headers)
    assert res_todas.status_code == 200
    lista_todas = res_todas.json()
    ids_todas = [r["id"] for r in lista_todas]
    assert pan_id in ids_todas and peri_id in ids_todas
    print(f"✔ [Escenario 2.1] Galería completa del paciente recuperada ({len(lista_todas)} estudios).")

    # 2.2 Filtro exclusivo por pieza FDI 16
    res_fdi = client.get(f"/api/v1/radiografias/?paciente_id={paciente_id}&pieza_fdi=16", headers=headers)
    assert res_fdi.status_code == 200
    lista_fdi = res_fdi.json()
    assert all(r["pieza_fdi"] == 16 for r in lista_fdi)
    assert peri_id in [r["id"] for r in lista_fdi]
    print(f"✔ [Escenario 2.2] Filtro anatómico por Pieza FDI 16 verificado.")

    # =========================================================================
    # ESCENARIO 3: Consulta en Visor y Auditoría de Lectura (VIEW)
    # =========================================================================
    res_visor = client.get(f"/api/v1/radiografias/{peri_id}", headers=headers)
    assert res_visor.status_code == 200
    rx_detalle = res_visor.json()
    assert rx_detalle["id"] == peri_id
    assert "periodontitis apical crónica" in rx_detalle["informe_diagnostico"]

    # Verificar que se emitió el log de auditoría VIEW en auditoria_logs
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=radiografias_estudios", headers=headers)
    assert res_audit.status_code == 200
    audit_logs = res_audit.json()
    view_logs = [l for l in audit_logs if l["registro_id"] == peri_id and l["accion"] == "VIEW"]
    assert len(view_logs) >= 1, "Debe existir un log de auditoría VIEW para la radiografía"
    assert view_logs[0]["seccion_consultada"] == "VISOR_RADIOGRAFIA"
    print("✔ [Escenario 3] Inspección en Visor completada con log forense de auditoría VIEW ('VISOR_RADIOGRAFIA').")

    # =========================================================================
    # ESCENARIO 4: Actualización de Informe Diagnóstico y Eliminación
    # =========================================================================
    # 4.1 Actualizar informe diagnóstico tras interconsulta
    update_data = {
        "informe_diagnostico": "Informe ampliado: Periodontitis apical crónica con conductometría confirmada en 21mm."
    }
    res_update = client.put(f"/api/v1/radiografias/{peri_id}", json=update_data, headers=headers)
    assert res_update.status_code == 200
    assert "21mm" in res_update.json()["informe_diagnostico"]
    print("✔ [Escenario 4.1] Informe diagnóstico radiológico actualizado correctamente.")

    # 4.2 Crear un estudio temporal y eliminarlo
    temp_rx = {
        "paciente_id": paciente_id,
        "tipo_estudio": "FOTOGRAFIA_CLINICA",
        "titulo": "Foto intraoral previa a descarte",
        "archivo_url": "https://storage.clinicagustavo.com/radiografias/temp_foto.jpg"
    }
    res_temp = client.post("/api/v1/radiografias/", json=temp_rx, headers=headers)
    assert res_temp.status_code == 201
    temp_id = res_temp.json()["id"]

    res_del = client.delete(f"/api/v1/radiografias/{temp_id}", headers=headers)
    assert res_del.status_code == 204

    # Verificar que ya no existe (404)
    res_get_deleted = client.get(f"/api/v1/radiografias/{temp_id}", headers=headers)
    assert res_get_deleted.status_code == 404
    print("✔ [Escenario 4.2] Eliminación de estudio radiológico y código HTTP 204 validado.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-08 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu08_completo()
