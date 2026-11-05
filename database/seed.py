import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Rol, RolCodigoEnum, Usuario, Permiso, RolPermiso, Doctor, Sillon
from app.core.security import hash_password

def seed_database():
    db = SessionLocal()
    try:
        print("Iniciando seed de datos iniciales...")

        # 1. Catálogo Completo de Permisos por Módulo
        catalogo_permisos = [
            # Módulo Pacientes
            ("PACIENTES", "READ", "PACIENTES_READ", "Visualizar listado y fichas de pacientes"),
            ("PACIENTES", "CREATE", "PACIENTES_CREATE", "Registrar nuevos pacientes"),
            ("PACIENTES", "UPDATE", "PACIENTES_UPDATE", "Editar datos de pacientes"),
            ("PACIENTES", "DELETE", "PACIENTES_DELETE", "Eliminar o dar de baja a pacientes"),
            ("PACIENTES", "UPDATE", "ANTECEDENTES_UPDATE", "Modificar anamnesis y alertas médicas"),

            # Módulo Citas y Agenda
            ("CITAS", "READ", "CITAS_READ", "Ver calendario y agenda de citas"),
            ("CITAS", "CREATE", "CITAS_CREATE", "Agendar nuevas citas médicas"),
            ("CITAS", "UPDATE", "CITAS_UPDATE", "Reagendar, modificar o cancelar citas"),
            ("CITAS", "UPDATE", "CITAS_SILLON", "Controlar tiempos de entrada/salida de sillón"),

            # Módulo Odontograma (Tooth Chart)
            ("ODONTOGRAMA", "READ", "ODONTOGRAMA_READ", "Visualizar odontograma y piezas dentales"),
            ("ODONTOGRAMA", "CREATE", "ODONTOGRAMA_CREATE", "Generar odontogramas iniciales o de evolución"),
            ("ODONTOGRAMA", "UPDATE", "ODONTOGRAMA_UPDATE", "Marcar patologías o caras dentales"),
            ("ODONTOGRAMA", "DELETE", "ODONTOGRAMA_DELETE", "Eliminar hallazgos del odontograma"),

            # Módulo Tratamientos y Presupuestos
            ("TRATAMIENTOS", "READ", "TRATAMIENTOS_READ", "Ver catálogo de tratamientos y planes"),
            ("TRATAMIENTOS", "CREATE", "TRATAMIENTOS_CREATE", "Crear planes y presupuestos secuenciales"),
            ("TRATAMIENTOS", "UPDATE", "TRATAMIENTOS_UPDATE", "Editar pasos o costos acordados"),

            # Módulo Historia Clínica Diaria
            ("HISTORIA_CLINICA", "READ", "HISTORIA_CLINICA_READ", "Consultar evoluciones médicas pasadas"),
            ("HISTORIA_CLINICA", "CREATE", "HISTORIA_CLINICA_CREATE", "Registrar atención médica de hoy y recetas"),
            ("HISTORIA_CLINICA", "UPDATE", "HISTORIA_CLINICA_UPDATE", "Modificar notas de evolución"),
            ("HISTORIA_CLINICA", "CREATE", "HISTORIA_CLINICA_OBSERVAR", "Agregar observaciones a una evolución clínica"),

            # Módulo Radiografías e Imágenes
            ("RADIOGRAFIAS", "READ", "RADIOGRAFIAS_READ", "Visualizar radiografías e imágenes clínicas"),
            ("RADIOGRAFIAS", "CREATE", "RADIOGRAFIAS_CREATE", "Subir radiografías y redactar informe diagnóstico"),
            ("RADIOGRAFIAS", "DELETE", "RADIOGRAFIAS_DELETE", "Eliminar imágenes del expediente"),

            # Módulo Laboratorio y Prótesis
            ("PROTESIS", "READ", "PROTESIS_READ", "Consultar órdenes de laboratorio dental"),
            ("PROTESIS", "CREATE", "PROTESIS_CREATE", "Enviar órdenes de prótesis con color Vita"),
            ("PROTESIS", "UPDATE", "PROTESIS_UPDATE", "Marcar prótesis recibida o probada en boca"),

            # Módulo Caja y Finanzas
            ("CAJA", "READ", "CAJA_READ", "Ver estado de caja y efectivo en gaveta"),
            ("CAJA", "CREATE", "CAJA_APERTURA", "Abrir turno de caja con fondo inicial"),
            ("CAJA", "UPDATE", "CAJA_CIERRE", "Cerrar caja y registrar arqueo con descuadre"),
            ("CAJA", "CREATE", "CAJA_PAGOS", "Cobrar a pacientes (efectivo, tarjeta, transferencia)"),
            ("CAJA", "CREATE", "CAJA_EGRESOS", "Registrar salidas de dinero físico de la gaveta"),
            ("CAJA", "UPDATE", "CAJA_ANULAR_PAGOS", "Anular pagos de pacientes indicando el motivo"),

            # Módulo Personal y Nómina
            ("PERSONAL", "CREATE", "ASISTENCIA_FICHAR", "Fichar entradas, salidas y descansos"),
            ("PERSONAL", "READ", "ASISTENCIA_READ_ALL", "Auditar fichajes de todo el personal"),
            ("PERSONAL", "READ", "EMPLEADOS_READ", "Consultar contratos salariales y comisiones"),
            ("PERSONAL", "CREATE", "EMPLEADOS_PAGOS", "Liquidar sueldos y pagar comisiones"),

            # Módulo Seguridad y Auditoría
            ("AUDITORIA", "READ", "AUDITORIA_READ", "Consultar bitácora de cambios y accesos VIEW"),
            ("REPORTES", "READ", "REPORTES_READ", "Consultar reportes de productividad y finanzas"),
            ("USUARIOS", "MANAGE", "USUARIOS_MANAGE", "Crear y desactivar cuentas de usuarios"),
            ("ROLES", "MANAGE", "ROLES_MANAGE", "Crear roles y asignar permisos granulares"),
        ]

        permisos_dict = {}
        for modulo, accion, codigo, desc in catalogo_permisos:
            p = db.query(Permiso).filter(Permiso.codigo_permiso == codigo).first()
            if not p:
                p = Permiso(modulo=modulo, accion=accion, codigo_permiso=codigo, descripcion=desc)
                db.add(p)
                db.commit()
                db.refresh(p)
            permisos_dict[codigo] = p

        print(f"-> Catálogo de permisos sincronizado: {len(permisos_dict)} permisos disponibles.")

        # 2. Roles del Sistema
        roles_data = [
            (RolCodigoEnum.ADMIN, "Administrador de Clínica", "Acceso total administrativo y clínico"),
            (RolCodigoEnum.DOCTOR, "Odontólogo / Especialista", "Gestión de historias clínicas, tratamientos, odontograma y citas"),
            (RolCodigoEnum.ASISTENTE, "Asistente Dental", "Apoyo en gabinete, visualización de fichas y asistencia"),
            (RolCodigoEnum.RECEPCION, "Recepción / Secretaría", "Gestión de agenda, citas, pagos de pacientes y caja"),
        ]

        roles_dict = {}
        for codigo, nombre, desc in roles_data:
            rol = db.query(Rol).filter(Rol.codigo == codigo).first()
            if not rol:
                rol = Rol(codigo=codigo, nombre=nombre, descripcion=desc, es_sistema=True)
                db.add(rol)
                db.commit()
                db.refresh(rol)
            roles_dict[codigo] = rol

        # 3. Asignación Predeterminada de Permisos a Roles
        # DOCTOR: Todo lo clínico, citas, radiografías, prótesis y fichaje
        permisos_doctor = [
            "PACIENTES_READ", "PACIENTES_CREATE", "PACIENTES_UPDATE", "ANTECEDENTES_UPDATE",
            "CITAS_READ", "CITAS_CREATE", "CITAS_UPDATE", "CITAS_SILLON",
            "ODONTOGRAMA_READ", "ODONTOGRAMA_CREATE", "ODONTOGRAMA_UPDATE", "ODONTOGRAMA_DELETE",
            "TRATAMIENTOS_READ", "TRATAMIENTOS_CREATE", "TRATAMIENTOS_UPDATE",
            "HISTORIA_CLINICA_READ", "HISTORIA_CLINICA_CREATE", "HISTORIA_CLINICA_UPDATE", "HISTORIA_CLINICA_OBSERVAR",
            "RADIOGRAFIAS_READ", "RADIOGRAFIAS_CREATE",
            "PROTESIS_READ", "PROTESIS_CREATE", "PROTESIS_UPDATE",
            "ASISTENCIA_FICHAR"
        ]

        # ASISTENTE: Consulta de pacientes, apoyo en sillón, ver odontograma/radiografías y fichaje
        permisos_asistente = [
            "PACIENTES_READ", "CITAS_READ", "CITAS_UPDATE", "CITAS_SILLON", "ODONTOGRAMA_READ", "TRATAMIENTOS_READ",
            "HISTORIA_CLINICA_READ", "HISTORIA_CLINICA_OBSERVAR",
            "RADIOGRAFIAS_READ", "RADIOGRAFIAS_CREATE", "PROTESIS_READ", "ASISTENCIA_FICHAR"
        ]

        # RECEPCION: Pacientes, citas, cobros, caja, prótesis (recepción) y fichaje
        permisos_recepcion = [
            "PACIENTES_READ", "PACIENTES_CREATE", "PACIENTES_UPDATE",
            "CITAS_READ", "CITAS_CREATE", "CITAS_UPDATE", "CITAS_SILLON",
            "TRATAMIENTOS_READ", "PROTESIS_READ", "PROTESIS_UPDATE",
            "CAJA_READ", "CAJA_APERTURA", "CAJA_CIERRE", "CAJA_PAGOS", "CAJA_EGRESOS",
            "ASISTENCIA_FICHAR"
        ]

        def asignar_permisos(rol_obj, codigos):
            for c in codigos:
                if c in permisos_dict:
                    pid = permisos_dict[c].id
                    rel = db.query(RolPermiso).filter(RolPermiso.rol_id == rol_obj.id, RolPermiso.permiso_id == pid).first()
                    if not rel:
                        db.add(RolPermiso(rol_id=rol_obj.id, permiso_id=pid))
            db.commit()

        asignar_permisos(roles_dict[RolCodigoEnum.DOCTOR], permisos_doctor)
        asignar_permisos(roles_dict[RolCodigoEnum.ASISTENTE], permisos_asistente)
        asignar_permisos(roles_dict[RolCodigoEnum.RECEPCION], permisos_recepcion)

        # ADMIN tiene todos los permisos
        asignar_permisos(roles_dict[RolCodigoEnum.ADMIN], list(permisos_dict.keys()))

        print("-> Permisos asignados a cada rol con éxito.")

        # 4. Crear Usuario Administrador por Defecto
        admin_user = db.query(Usuario).filter(Usuario.username == "admin").first()
        if not admin_user:
            admin_user = Usuario(
                rol_id=roles_dict[RolCodigoEnum.ADMIN].id,
                username="admin",
                password_hash=hash_password("admin123"),
                nombre="Administrador",
                apellido="Principal",
                email="admin@clinicadental.com",
                telefono="000000000",
                activo=True
            )
            db.add(admin_user)
            db.commit()
            print("-> Usuario Administrador creado: admin / admin123")
        else:
            print("-> Usuario Administrador ya existe.")

        # Asegurar perfil de Doctor para el Administrador (Perfil Clínico Dual)
        admin_doc = db.query(Doctor).filter(Doctor.usuario_id == admin_user.id).first()
        if not admin_doc:
            admin_doc = Doctor(
                usuario_id=admin_user.id,
                especialidad="Odontología General / Dirección Médica",
                numero_colegiatura="COL-ADMIN-001",
                color_agenda="#3B82F6"
            )
            db.add(admin_doc)
            db.commit()
            print("-> Perfil Clínico Dual asignado al Administrador (Doctor ID generado).")
        else:
            print("-> Administrador ya cuenta con perfil de Doctor.")

        # 5. Sillones iniciales de la agenda
        if not db.query(Sillon.id).first():
            db.add_all([
                Sillon(numero=1, nombre="Box 1", especialidad="General"),
                Sillon(numero=2, nombre="Box 2", especialidad="Cirugía"),
                Sillon(numero=3, nombre="Box 3", especialidad="Ortodoncia"),
            ])
            db.commit()

        print("¡Seed de Roles y Permisos completado con total éxito!")
    except Exception as e:
        db.rollback()
        print(f"Error en el seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
