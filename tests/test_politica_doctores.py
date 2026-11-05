import sys
import os
sys.path.insert(0, os.path.abspath("."))
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import Usuario, Doctor, Rol, RolCodigoEnum, Paciente, GeneroEnum

client = TestClient(app)

def test_admin_and_doctor_assignment_policy():
    db = SessionLocal()
    try:
        # 1. Login Admin
        res_admin_login = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
        assert res_admin_login.status_code == 200, f"Admin login failed: {res_admin_login.text}"
        admin_token = res_admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Check me
        res_me = client.get("/api/v1/auth/me", headers=admin_headers)
        assert res_me.status_code == 200
        me_data = res_me.json()
        print(f"[OK] Admin logged in. Doctor profile ID: {me_data.get('doctor_id')}")

        # 2. Get doctors list
        res_docs = client.get("/api/v1/usuarios/doctores/lista", headers=admin_headers)
        assert res_docs.status_code == 200
        docs = res_docs.json()
        print(f"[OK] Found {len(docs)} doctors in system.")
        assert len(docs) >= 2, "Expected at least 2 doctors (admin doctor and test doctor)"
        
        doc_1 = docs[0]
        doc_2 = docs[1]

        # 3. Create a test patient
        doc_num = f"DOC-{uuid4().hex[:8]}"
        res_pac = client.post("/api/v1/pacientes/", json={
            "nombres": "Paciente",
            "apellidos": "Prueba Politica",
            "tipo_documento": "CI",
            "numero_documento": doc_num,
            "genero": "MASCULINO",
            "fecha_nacimiento": "1990-01-01",
            "telefono": "70000000"
        }, headers=admin_headers)
        assert res_pac.status_code == 201, f"Failed creating patient: {res_pac.text}"
        paciente_id = res_pac.json()["id"]

        # 4. Admin creates odontograma assigned to doc_2
        res_odonto_admin = client.post("/api/v1/odontogramas/", json={
            "paciente_id": paciente_id,
            "doctor_id": doc_2["id"],
            "tipo": "ADULTO",
            "observaciones_generales": "Creado por admin para doc_2"
        }, headers=admin_headers)
        assert res_odonto_admin.status_code == 201, f"Admin odonto create failed: {res_odonto_admin.text}"
        odonto_id = res_odonto_admin.json()["id"]
        assert res_odonto_admin.json()["doctor_id"] == doc_2["id"], "Doctor ID not assigned properly by admin"
        print("[OK] Admin successfully assigned odontograma to another doctor.")

        # 5. Admin edits odontograma and reassigns to doc_1
        res_odonto_edit = client.put(f"/api/v1/odontogramas/{odonto_id}", json={
            "doctor_id": doc_1["id"]
        }, headers=admin_headers)
        assert res_odonto_edit.status_code == 200, f"Admin odonto edit failed: {res_odonto_edit.text}"
        assert res_odonto_edit.json()["doctor_id"] == doc_1["id"], "Admin reassign failed"
        print("[OK] Admin successfully reassigned existing odontograma to doc_1.")

        # 6. Admin creates plan for doc_2
        res_plan_admin = client.post("/api/v1/tratamientos/planes", json={
            "paciente_id": paciente_id,
            "doctor_id": doc_2["id"],
            "titulo": "Plan de Tratamiento Integral",
            "items": []
        }, headers=admin_headers)
        assert res_plan_admin.status_code == 201, f"Admin plan create failed: {res_plan_admin.text}"
        plan_id = res_plan_admin.json()["id"]
        assert res_plan_admin.json()["doctor_id"] == doc_2["id"]
        print("[OK] Admin successfully assigned plan to doc_2.")

        # 7. Admin creates clinical note (visita) for doc_2
        res_visita_admin = client.post("/api/v1/visitas/", json={
            "paciente_id": paciente_id,
            "doctor_id": doc_2["id"],
            "motivo_consulta": "Control SOEP asignado por Admin",
            "diagnostico": "Caries oclusal en pieza 16",
            "procedimiento_realizado": "Examen periodontal"
        }, headers=admin_headers)
        assert res_visita_admin.status_code == 201, f"Admin visita create failed: {res_visita_admin.text}"
        assert res_visita_admin.json()["doctor_id"] == doc_2["id"]
        print("[OK] Admin successfully created clinical note assigned to doc_2.")

        # 8. Test Doctor (non-admin) login: dr_hu06_fichaje
        res_doc_login = client.post("/api/v1/auth/login", data={"username": "dr_hu06_fichaje", "password": "DoctorPassword123"})
        assert res_doc_login.status_code == 200, f"Doctor login failed: {res_doc_login.text}"
        doc_token = res_doc_login.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}

        res_doc_me = client.get("/api/v1/auth/me", headers=doc_headers)
        assert res_doc_me.status_code == 200
        doc_me_data = res_doc_me.json()
        doc_self_id = doc_me_data["doctor_id"]
        print(f"[OK] Regular Doctor logged in: {doc_me_data['username']} (doctor_id={doc_self_id})")

        # 9. Doctor tries to create odontogram attempting to assign doc_1 (different doctor)
        other_doc_id = doc_1["id"] if doc_1["id"] != doc_self_id else doc_2["id"]
        res_doc_odonto = client.post("/api/v1/odontogramas/", json={
            "paciente_id": paciente_id,
            "doctor_id": other_doc_id,
            "tipo": "ADULTO",
            "observaciones_generales": "Intento de doctor de asignar a otro"
        }, headers=doc_headers)
        assert res_doc_odonto.status_code == 403, f"Expected 403 Forbidden for doctor assigning another doctor, got {res_doc_odonto.status_code}"
        print("[OK] Regular Doctor was correctly FORBIDDEN (403) from assigning an odontogram to another doctor.")

        # 10. Doctor creates odontogram with own ID
        res_doc_self_odonto = client.post("/api/v1/odontogramas/", json={
            "paciente_id": paciente_id,
            "doctor_id": doc_self_id,
            "tipo": "ADULTO",
            "observaciones_generales": "Odontograma de doctor propio"
        }, headers=doc_headers)
        assert res_doc_self_odonto.status_code == 201, f"Doctor self create failed: {res_doc_self_odonto.text}"
        doc_odonto_id = res_doc_self_odonto.json()["id"]
        print("[OK] Regular Doctor successfully created odontogram with their own identity.")

        # 11. Doctor attempts to edit odontograma to reassign doctor_id to someone else -> Must get 403 Forbidden
        res_doc_reassign = client.put(f"/api/v1/odontogramas/{doc_odonto_id}", json={
            "doctor_id": other_doc_id
        }, headers=doc_headers)
        assert res_doc_reassign.status_code == 403, f"Expected 403 Forbidden on doctor reassigning odontograma, got: {res_doc_reassign.status_code}"
        print("[OK] Regular Doctor was correctly FORBIDDEN (403) from reassigning doctor on an existing odontograma.")

        print("\n>>> ALL ADMIN ASSIGNMENT & DOCTOR RESTRICTION POLICIES VALIDATED SUCCESSFULLY! <<<")

    finally:
        db.close()

if __name__ == "__main__":
    test_admin_and_doctor_assignment_policy()
