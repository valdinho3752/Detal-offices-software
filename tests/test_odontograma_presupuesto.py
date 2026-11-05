import sys
import os
sys.path.insert(0, os.path.abspath("."))

from uuid import uuid4
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Usuario, Doctor, Paciente, CatalogoTratamiento, CategoriaTratamientoEnum, PlanTratamiento

client = TestClient(app)

def test_odontograma_y_presupuesto_exact_reproduction():
    db = SessionLocal()
    try:
        # 1. Login Admin
        res_login = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
        assert res_login.status_code == 200
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get or create a treatment catalog item
        cat = db.query(CatalogoTratamiento).filter(CatalogoTratamiento.activo == True).first()
        if not cat:
            cat = CatalogoTratamiento(
                codigo="ODON-TEST-01",
                categoria=CategoriaTratamientoEnum.OPERATORIA_DENTAL,
                nombre="Restauración Resina Simple",
                costo_base=Decimal("45.00"),
                duracion_estimada_min=30,
                activo=True
            )
            db.add(cat)
            db.commit()
            db.refresh(cat)
        tratamiento_id = str(cat.id)

        # 3. Create a patient
        doc_num = f"PAC-{uuid4().hex[:8]}"
        res_pac = client.post("/api/v1/pacientes/", json={
            "nombres": "Paciente",
            "apellidos": "Test Presupuesto",
            "tipo_documento": "CI",
            "numero_documento": doc_num,
            "genero": "FEMENINO",
            "fecha_nacimiento": "1995-05-15",
            "telefono": "78888888"
        }, headers=headers)
        assert res_pac.status_code == 201
        paciente_id = res_pac.json()["id"]

        # 4. Create an odontograma
        res_odonto = client.post("/api/v1/odontogramas/", json={
            "paciente_id": paciente_id,
            "tipo_denticion": "ADULTA_PERMANENTE",
            "tipo_registro": "INICIAL_INGRESO",
            "observaciones_generales": "Test Odontograma"
        }, headers=headers)
        assert res_odonto.status_code == 201
        odonto_id = res_odonto.json()["id"]

        # 5. Add a finding to tooth 16
        res_hallazgo = client.post("/api/v1/odontogramas/hallazgos", json={
            "odontograma_id": odonto_id,
            "pieza_fdi": 16,
            "superficie": "OCLUSAL_INCISAL",
            "condicion": "CARIES",
            "color_hex": "#EF4444",
            "estado_clinico": "REQUERIDO_PATOLOGIA"
        }, headers=headers)
        assert res_hallazgo.status_code == 201
        print("[OK] Hallazgo agregado a la pieza 16.")

        # 6. Create plan
        res_plan = client.post("/api/v1/tratamientos/planes", json={
            "paciente_id": paciente_id,
            "titulo": "Plan de Tratamiento Integral",
            "items": []
        }, headers=headers)
        assert res_plan.status_code == 201
        plan_id = res_plan.json()["id"]
        print(f"[OK] Plan de tratamiento creado: {plan_id}")

        # 7. EXACT REPRODUCTION of the payload from user's screenshot:
        # {"plan_id":"...","tratamiento_id":"...","pieza_fdi":16,"superficie":"OCLUSAL_INCISAL","precio_unitario":0,"descuento":0,"estado":"PENDIENTE","es_proxima_sesion":true}
        screenshot_payload = {
            "plan_id": plan_id,
            "tratamiento_id": tratamiento_id,
            "pieza_fdi": 16,
            "superficie": "OCLUSAL_INCISAL",
            "precio_unitario": 0,
            "descuento": 0,
            "estado": "PENDIENTE",
            "es_proxima_sesion": True
        }
        res_screenshot = client.post("/api/v1/tratamientos/items", json=screenshot_payload, headers=headers)
        assert res_screenshot.status_code == 201, f"Failed screenshot payload: {res_screenshot.text}"
        item1 = res_screenshot.json()
        assert item1["costo_acordado"] == "0.00" or item1["costo_acordado"] == 0
        assert item1["estado"] == "PROXIMA_SESION"
        print("[OK] Screenshot payload (without costo_acordado and with precio_unitario=0) passed with 201 Created!")

        # 8. Test with real prices: precio_unitario: 50.00, descuento: 5.00 -> costo_acordado: 45.00
        real_payload = {
            "plan_id": plan_id,
            "tratamiento_id": tratamiento_id,
            "pieza_fdi": 21,
            "superficie": "VESTIBULAR",
            "precio_unitario": 50.0,
            "descuento": 5.0,
            "es_proxima_sesion": False
        }
        res_real = client.post("/api/v1/tratamientos/items", json=real_payload, headers=headers)
        assert res_real.status_code == 201, f"Failed real price payload: {res_real.text}"
        item2 = res_real.json()
        assert float(item2["costo_acordado"]) == 45.0
        assert item2["estado"] == "PENDIENTE"
        print("[OK] Real price payload auto-calculated costo_acordado=45.00 correctly.")

        # 9. Verify getPlanes calculates total and returns properties
        res_get_planes = client.get(f"/api/v1/tratamientos/planes?paciente_id={paciente_id}", headers=headers)
        assert res_get_planes.status_code == 200
        planes = res_get_planes.json()
        assert len(planes) >= 1
        assert float(planes[0]["costo_total"]) == 45.0  # 0.0 + 45.0
        print(f"[OK] Total del plan recalculado en la base de datos: ${planes[0]['costo_total']}")

        print("\n>>> TEST DE PRESUPUESTACIÓN DE ODONTOGRAMA COMPLETADO CON ÉXITO <<<")

    finally:
        db.close()

if __name__ == "__main__":
    test_odontograma_y_presupuesto_exact_reproduction()
