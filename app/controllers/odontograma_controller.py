from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Odontograma, PiezaDental, HallazgoSuperficie, Usuario, AuditoriaLog,
    AuditoriaAccionEnum, TipoDenticionEnum, Doctor, EstadoClinicoHallazgoEnum,
    TipoOdontogramaEnum
)
from app.core.dependencies import get_current_user
from app.services.tratamiento_clinico import clonar_odontograma_como_evolucion
from app.schemas.odontograma import (
    OdontogramaCreate, OdontogramaUpdate, OdontogramaResponse,
    PiezaDentalCreate, PiezaDentalUpdate, PiezaDentalResponse,
    HallazgoSuperficieCreate, HallazgoSuperficieUpdate, HallazgoSuperficieResponse
)

router = APIRouter(prefix="/odontogramas", tags=["Odontograma y Tooth Chart Interactivo"])

@router.get("/", response_model=List[OdontogramaResponse])
def listar_odontogramas_paciente(
    paciente_id: UUID,
    tipo_registro: Optional[TipoOdontogramaEnum] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Odontograma).filter(Odontograma.paciente_id == paciente_id)
    if tipo_registro:
        query = query.filter(Odontograma.tipo_registro == tipo_registro)
    return query.order_by(Odontograma.fecha_registro.desc()).all()

@router.post("/", response_model=OdontogramaResponse, status_code=status.HTTP_201_CREATED)
def crear_odontograma(
    datos: OdontogramaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo odontograma y autogenera las piezas dentales correspondientes según la dentición:
    - Adulto: 32 piezas (11-48 FDI)
    - Pediátrico: 20 piezas (51-85 FDI)
    """
    odontograma_data = datos.model_dump()
    doctor = None
    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"

    if es_admin:
        # Administrador: puede asignar el odontograma a cualquier doctor
        if datos.doctor_id:
            doctor = db.query(Doctor).filter((Doctor.id == datos.doctor_id) | (Doctor.usuario_id == datos.doctor_id)).first()
        if not doctor and current_user.doctor_perfil:
            doctor = current_user.doctor_perfil
        if not doctor:
            doctor = db.query(Doctor).first()
        if not doctor:
            doctor = Doctor(usuario_id=current_user.id, especialidad="Odontología General / Dirección Médica")
            db.add(doctor)
            db.flush()
    else:
        # No es Admin: Solo un DOCTOR puede registrar odontograma y queda estrictamente bajo su autoría
        if not current_user.doctor_perfil:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo personal médico o administradores pueden crear odontogramas"
            )
        if datos.doctor_id:
            target_doc = db.query(Doctor).filter((Doctor.id == datos.doctor_id) | (Doctor.usuario_id == datos.doctor_id)).first()
            if target_doc and target_doc.id != current_user.doctor_perfil.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para registrar odontogramas a nombre de otros doctores"
                )
        doctor = current_user.doctor_perfil

    odontograma_data["doctor_id"] = doctor.id
    odontograma = Odontograma(**odontograma_data)
    db.add(odontograma)
    db.flush()

    piezas_a_crear = []
    if datos.tipo_denticion == TipoDenticionEnum.INFANTIL_DECIDUA:
        # Dientes de leche (temporales): 51 a 55, 61 a 65, 71 a 75, 81 a 85
        cuadrantes = [(51, 55), (61, 65), (71, 75), (81, 85)]
        for inicio, fin in cuadrantes:
            for num in range(inicio, fin + 1):
                piezas_a_crear.append(PiezaDental(odontograma_id=odontograma.id, numero_fdi=num))
    else:
        # Dientes permanentes (adultos): 11 a 18, 21 a 28, 31 a 38, 41 a 48
        cuadrantes = [(11, 18), (21, 28), (31, 38), (41, 48)]
        for inicio, fin in cuadrantes:
            for num in range(inicio, fin + 1):
                piezas_a_crear.append(PiezaDental(odontograma_id=odontograma.id, numero_fdi=num))

    db.add_all(piezas_a_crear)

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="odontogramas",
        registro_id=odontograma.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="CREAR_ODONTOGRAMA"
    )
    db.add(log)
    db.commit()
    db.refresh(odontograma)
    return odontograma

@router.get("/{id}", response_model=OdontogramaResponse)
def obtener_odontograma(
    id: UUID,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    odontograma = db.query(Odontograma).filter(Odontograma.id == id).first()
    if not odontograma:
        raise HTTPException(status_code=404, detail="Odontograma no encontrado")

    # Auditoría de visualización (VIEW)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="odontogramas",
        registro_id=odontograma.id,
        accion=AuditoriaAccionEnum.VIEW,
        seccion_consultada="ODONTOGRAMA_INTERACTIVO",
        ip_origen=client_ip,
        user_agent=user_agent
    )
    db.add(log)
    db.commit()

    return odontograma

@router.put("/{id}", response_model=OdontogramaResponse)
def actualizar_odontograma(
    id: UUID,
    datos: OdontogramaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    odontograma = db.query(Odontograma).filter(Odontograma.id == id).first()
    if not odontograma:
        raise HTTPException(status_code=404, detail="Odontograma no encontrado")
        
    update_data = datos.model_dump(exclude_unset=True)
    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"
    
    if "doctor_id" in update_data and update_data["doctor_id"]:
        if not es_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden reasignar el doctor del odontograma"
            )
        doc = db.query(Doctor).filter((Doctor.id == update_data["doctor_id"]) | (Doctor.usuario_id == update_data["doctor_id"])).first()
        if doc:
            update_data["doctor_id"] = doc.id
            
    for field, value in update_data.items():
        setattr(odontograma, field, value)
    db.commit()
    db.refresh(odontograma)
    return odontograma

@router.post("/{id}/clonar-como-evolucion", response_model=OdontogramaResponse, status_code=status.HTTP_201_CREATED)
def clonar_como_evolucion(
    id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    origen = db.query(Odontograma).filter(Odontograma.id == id).first()
    if not origen:
        raise HTTPException(status_code=404, detail="Odontograma de origen no encontrado")

    doctor_id = origen.doctor_id
    if current_user.doctor_perfil:
        doctor_id = current_user.doctor_perfil.id

    nuevo_odonto = clonar_odontograma_como_evolucion(origen, doctor_id, db)

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="odontogramas",
        registro_id=nuevo_odonto.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="CLONAR_COMO_EVOLUCION"
    )
    db.add(log)
    db.commit()
    db.refresh(nuevo_odonto)
    return nuevo_odonto

# ==================== PIEZAS DENTALES ====================

@router.put("/piezas/{id}", response_model=PiezaDentalResponse)
def actualizar_pieza_dental(
    id: UUID,
    datos: PiezaDentalUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pieza = db.query(PiezaDental).filter(PiezaDental.id == id).first()
    if not pieza:
        raise HTTPException(status_code=404, detail="Pieza dental no encontrada")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(pieza, field, value)
    db.commit()
    db.refresh(pieza)
    return pieza

# ==================== HALLAZGOS Y CARAS DENTALES ====================

@router.post("/hallazgos", response_model=HallazgoSuperficieResponse, status_code=status.HTTP_201_CREATED)
def registrar_hallazgo_superficie(
    datos: HallazgoSuperficieCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pieza_id = datos.pieza_dental_id
    if not pieza_id and datos.odontograma_id and datos.pieza_fdi:
        pieza = db.query(PiezaDental).filter(
            PiezaDental.odontograma_id == datos.odontograma_id,
            PiezaDental.numero_fdi == datos.pieza_fdi
        ).first()
        if not pieza:
            pieza = PiezaDental(odontograma_id=datos.odontograma_id, numero_fdi=datos.pieza_fdi)
            db.add(pieza)
            db.flush()
        pieza_id = pieza.id

    if not pieza_id:
        raise HTTPException(status_code=400, detail="Debe proporcionar pieza_dental_id o (odontograma_id y pieza_fdi)")

    existentes = db.query(HallazgoSuperficie).filter(
        HallazgoSuperficie.pieza_dental_id == pieza_id,
        HallazgoSuperficie.superficie == datos.superficie
    ).all()
    if existentes:
        existente = existentes[0]
        existente.condicion = datos.condicion
        existente.estado_clinico = datos.estado_clinico or EstadoClinicoHallazgoEnum.REQUERIDO_PATOLOGIA
        existente.color_hex = datos.color_hex or "#EF4444"
        if datos.detalle is not None:
            existente.detalle = datos.detalle
        for dup in existentes[1:]:
            db.delete(dup)
        db.commit()
        db.refresh(existente)
        return existente

    hallazgo = HallazgoSuperficie(
        pieza_dental_id=pieza_id,
        superficie=datos.superficie,
        condicion=datos.condicion,
        estado_clinico=datos.estado_clinico or EstadoClinicoHallazgoEnum.REQUERIDO_PATOLOGIA,
        color_hex=datos.color_hex or "#EF4444",
        detalle=datos.detalle
    )
    db.add(hallazgo)
    db.commit()
    db.refresh(hallazgo)
    return hallazgo

@router.put("/hallazgos/{id}", response_model=HallazgoSuperficieResponse)
def actualizar_hallazgo_superficie(
    id: UUID,
    datos: HallazgoSuperficieUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hallazgo = db.query(HallazgoSuperficie).filter(HallazgoSuperficie.id == id).first()
    if not hallazgo:
        raise HTTPException(status_code=404, detail="Hallazgo de superficie no encontrado")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(hallazgo, field, value)
    db.commit()
    db.refresh(hallazgo)
    return hallazgo

@router.delete("/hallazgos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_hallazgo_superficie(
    id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hallazgo = db.query(HallazgoSuperficie).filter(HallazgoSuperficie.id == id).first()
    if not hallazgo:
        raise HTTPException(status_code=404, detail="Hallazgo de superficie no encontrado")
    db.delete(hallazgo)
    db.commit()
    return None
