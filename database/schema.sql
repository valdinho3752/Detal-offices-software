-- ==============================================================================
-- SISTEMA DE GESTIÓN CLÍNICA DENTAL - ESQUEMA DE BASE DE DATOS RELACIONAL
-- Motor: PostgreSQL 14+
-- Descripción: Módulos de Pacientes, Citas, Odontograma, Radiografías,
--              Laboratorio/Prótesis, Finanzas, Caja en Vivo, Asistencia y Auditoría.
-- ==============================================================================

-- Extensión para generación de identificadores UUID v4
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 1. TIPOS ENUMERADOS (ENUMS)
-- ==============================================================================

-- Eventos de asistencia de personal
CREATE TYPE asistencia_tipo_enum AS ENUM (
    'ENTRADA',
    'SALIDA',
    'INICIO_DESCANSO',
    'FIN_DESCANSO'
);

-- Acciones de auditoría (incluye VIEW para accesos a datos médicos)
CREATE TYPE auditoria_accion_enum AS ENUM (
    'VIEW',
    'INSERT',
    'UPDATE',
    'DELETE',
    'EXPORT'
);

-- Género del paciente
CREATE TYPE genero_enum AS ENUM (
    'MASCULINO',
    'FEMENINO',
    'OTRO'
);

-- Estado del paciente
CREATE TYPE estado_registro_enum AS ENUM (
    'ACTIVO',
    'INACTIVO'
);

-- Dentición del odontograma
CREATE TYPE tipo_denticion_enum AS ENUM (
    'ADULTA_PERMANENTE',
    'INFANTIL_DECIDUA',
    'MIXTA'
);

-- Tipo de odontograma
CREATE TYPE tipo_odontograma_enum AS ENUM (
    'INICIAL_INGRESO',
    'EVOLUCION_ACTUAL'
);

-- Estado de una pieza dental completa
CREATE TYPE estado_diente_enum AS ENUM (
    'PRESENTE',
    'AUSENTE_CONGENITO',
    'EXTRAIDO',
    'POR_EXTRAER',
    'NO_ERUPCIONADO',
    'IMPLANTE',
    'CORONA_PROTESICA'
);

-- Superficies del diente
CREATE TYPE superficie_dental_enum AS ENUM (
    'GENERAL',
    'VESTIBULAR',
    'LINGUAL_PALATINO',
    'MESIAL',
    'DISTAL',
    'OCLUSAL_INCISAL',
    'RAIZ'
);

-- Condición / Hallazgo en superficie
CREATE TYPE condicion_dental_enum AS ENUM (
    'SANO',
    'CARIES',
    'OBTURACION_RESINA',
    'OBTURACION_AMALGAMA',
    'SELLANTE',
    'FRACTURA',
    'CORONA',
    'INCRUSTACION',
    'DESGASTE_EROSION',
    'ENDODONCIA'
);

-- Estado clínico de la patología / restauración
CREATE TYPE estado_clinico_hallazgo_enum AS ENUM (
    'EXISTENTE_PREVIO',     -- Vino de otra clínica (azul)
    'REQUERIDO_PATOLOGIA',  -- Caries o tratamiento pendiente (rojo)
    'REALIZADO_EN_CLINICA'  -- Realizado en esta clínica (azul/verde)
);

-- Categorías de catálogo de tratamientos
CREATE TYPE categoria_tratamiento_enum AS ENUM (
    'PREVENCION',
    'RESTAURADORA',
    'ENDODONCIA',
    'CIRUGIA_PERIODONCIA',
    'REHABILITACION_PROTESIS',
    'ORTODONCIA',
    'ESTETICA_DENTAL',
    'IMPLANTOLOGIA'
);

-- Estado del plan de tratamiento
CREATE TYPE estado_plan_enum AS ENUM (
    'PROPUESTO',
    'APROBADO',
    'EN_CURSO',
    'COMPLETADO',
    'CANCELADO'
);

-- Estado de un ítem individual del plan
CREATE TYPE estado_item_plan_enum AS ENUM (
    'PENDIENTE',
    'EN_CURSO',
    'PROXIMA_SESION',
    'COMPLETADO',
    'CANCELADO'
);

-- Estados de la cita
CREATE TYPE estado_cita_enum AS ENUM (
    'PROGRAMADA',
    'CONFIRMADA',
    'EN_ESPERA',
    'EN_SILLON',
    'FINALIZADA',
    'CANCELADA',
    'NO_ASISTIO'
);

-- Tipos de estudios radiológicos e imágenes
CREATE TYPE tipo_estudio_imagen_enum AS ENUM (
    'PANORAMICA',
    'PERIAPICAL',
    'ALETA_MORDIDA',
    'CEFALOMETRICA',
    'CONE_BEAM_CBCT',
    'OCLUSAL',
    'FOTOGRAFIA_CLINICA'
);

-- Tipos de prótesis o trabajos de laboratorio
CREATE TYPE tipo_trabajo_protesis_enum AS ENUM (
    'CORONA_ZIRCONIO',
    'CORONA_METAL_PORCELANA',
    'PROTESIS_TOTAL',
    'PROTESIS_REMOVIBLE_ESQUELETICO',
    'INCRUSTACION_EMAX',
    'CARILLA_ESTETICA',
    'PLACA_MIORRELAJANTE_BRUXISMO',
    'RETENEDOR_ORTODONCIA',
    'PERNO_COLADO',
    'OTRO'
);

-- Estados de órdenes de laboratorio
CREATE TYPE estado_orden_protesis_enum AS ENUM (
    'ENVIADO',
    'EN_LABORATORIO',
    'RECIBIDO_EN_CLINICA',
    'PRUEBA_EN_BOCA',
    'AJUSTE_REPETICION',
    'INSTALADO_FINALIZADO',
    'CANCELADO'
);

-- Métodos de pago
CREATE TYPE metodo_pago_enum AS ENUM (
    'EFECTIVO',
    'TARJETA_DEBITO',
    'TARJETA_CREDITO',
    'TRANSFERENCIA',
    'OTRO'
);

-- Esquemas salariales de empleados
CREATE TYPE tipo_remuneracion_enum AS ENUM (
    'SUELDO_FIJO_MENSUAL',
    'SUELDO_FIJO_QUINCENAL',
    'POR_HORA',
    'PORCENTAJE_COMISION',
    'MIXTO_BASE_MAS_COMISION'
);

-- Tipos de egreso de caja física
CREATE TYPE categoria_egreso_caja_enum AS ENUM (
    'PAGO_SUELDO',
    'ADELANTO_SUELDO',
    'COMISION_DOCTOR',
    'PAGO_LABORATORIO_PROTESIS',
    'COMPRA_INSUMOS',
    'GASTO_OPERATIVO',
    'OTRO'
);

-- Tipos de pago a empleados
CREATE TYPE tipo_pago_empleado_enum AS ENUM (
    'SUELDO_MENSUAL',
    'QUINCENA',
    'ADELANTO',
    'COMISION_TRATAMIENTOS',
    'BONO'
);

-- Estado de sesión de caja
CREATE TYPE estado_caja_enum AS ENUM (
    'ABIERTA',
    'CERRADA'
);

-- Estado de la cuenta de cobro de una cita
CREATE TYPE estado_cobro_cita_enum AS ENUM (
    'PENDIENTE',
    'PAGADO',
    'ANULADO'
);


-- ==============================================================================
-- 2. CONTROL DE ACCESO (RBAC) Y USUARIOS
-- ==============================================================================

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo VARCHAR(50) UNIQUE NOT NULL, -- Ej: ADMIN, DOCTOR, ASISTENTE, RECEPCION o roles personalizados
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    es_sistema BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permisos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    modulo VARCHAR(100) NOT NULL,
    accion VARCHAR(50) NOT NULL,
    codigo_permiso VARCHAR(150) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles_permisos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rol_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permiso_id UUID NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    CONSTRAINT uq_rol_permiso UNIQUE (rol_id, permiso_id)
);

CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rol_id UUID NOT NULL REFERENCES roles(id),
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    version_sesion INTEGER NOT NULL DEFAULT 0, -- Al aumentar, las sesiones anteriores dejan de servir
    debe_cambiar_contrasena BOOLEAN NOT NULL DEFAULT false,
    minutos_inactividad INTEGER NOT NULL DEFAULT 5, -- Cierre de sesión sin actividad; cada usuario lo elige
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(30),
    activo BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuarios_permisos_especiales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permiso_id UUID NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    concedido BOOLEAN NOT NULL DEFAULT true, -- true: otorga, false: revoca excepción
    CONSTRAINT uq_usuario_permiso UNIQUE (usuario_id, permiso_id)
);

CREATE TABLE doctores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    especialidad VARCHAR(120) NOT NULL DEFAULT 'Odontología General',
    numero_colegiatura VARCHAR(60),
    color_agenda VARCHAR(10) DEFAULT '#3B82F6', -- Color hexadecimal para el calendario
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE asistentes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 3. ASISTENCIA LABORAL Y CONTRATOS SALARIALES
-- ==============================================================================

CREATE TABLE contratos_remuneracion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_remuneracion tipo_remuneracion_enum NOT NULL DEFAULT 'SUELDO_FIJO_MENSUAL',
    salario_base NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    porcentaje_comision NUMERIC(5, 2) NOT NULL DEFAULT 0.00, -- Ej: 40.00%
    valor_hora NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    fecha_inicio_contrato DATE NOT NULL DEFAULT CURRENT_DATE,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE registro_asistencia (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_evento asistencia_tipo_enum NOT NULL,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones TEXT,
    ip_registro VARCHAR(45),
    es_correccion BOOLEAN NOT NULL DEFAULT false, -- Agregado por el administrador
    motivo_correccion TEXT,
    corregido_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    anulado BOOLEAN NOT NULL DEFAULT false, -- Deja de contar, pero sigue visible
    motivo_anulacion TEXT,
    anulado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL
);


-- ==============================================================================
-- 4. AUDITORÍA EXHAUSTIVA (LOGS DE ACCIONES Y VISTAS)
-- ==============================================================================

CREATE TABLE auditoria_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    tabla_afectada VARCHAR(100) NOT NULL,
    registro_id UUID,
    accion auditoria_accion_enum NOT NULL,
    seccion_consultada VARCHAR(100), -- Ej: HISTORIA_CLINICA, ODONTOGRAMA, CAJA
    datos_previos JSONB,             -- Null en consultas de lectura (VIEW)
    datos_nuevos JSONB,
    ip_origen VARCHAR(45),
    user_agent TEXT,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);


-- ==============================================================================
-- 5. PACIENTES Y ANTECEDENTES MÉDICOS (ANAMNESIS)
-- ==============================================================================

CREATE TABLE pacientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombres VARCHAR(120) NOT NULL,
    apellidos VARCHAR(120) NOT NULL,
    tipo_documento VARCHAR(20) DEFAULT 'DNI',
    numero_documento VARCHAR(50) UNIQUE NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    genero genero_enum DEFAULT 'OTRO',
    telefono VARCHAR(30) NOT NULL,
    email VARCHAR(150),
    direccion TEXT,
    ocupacion VARCHAR(100),
    contacto_emergencia_nombre VARCHAR(150),
    contacto_emergencia_telefono VARCHAR(30),
    estado estado_registro_enum DEFAULT 'ACTIVO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE antecedentes_medicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID UNIQUE NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    enfermedades_sistemicas TEXT, -- Diabetes, Hipertensión, Cardiopatías, etc.
    alergias TEXT,                -- Penicilina, Látex, Anestésicos, etc.
    medicamentos_actuales TEXT,   -- Anticoagulantes, Bifosfonatos, etc.
    cirugias_previas TEXT,
    fuma BOOLEAN DEFAULT false,
    embarazada BOOLEAN DEFAULT false,
    observaciones TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 6. ODONTOGRAMA INTERACTIVO (TOOTH CHART)
-- ==============================================================================

CREATE TABLE odontogramas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    tipo_denticion tipo_denticion_enum DEFAULT 'ADULTA_PERMANENTE' NOT NULL,
    tipo_registro tipo_odontograma_enum DEFAULT 'INICIAL_INGRESO' NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones_generales TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE piezas_dentales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    odontograma_id UUID NOT NULL REFERENCES odontogramas(id) ON DELETE CASCADE,
    numero_fdi INTEGER NOT NULL, -- 11-48 permanentes / 51-85 deciduos
    estado_general estado_diente_enum DEFAULT 'PRESENTE' NOT NULL,
    tiene_endodoncia BOOLEAN DEFAULT false NOT NULL,
    tiene_perno_poste BOOLEAN DEFAULT false NOT NULL,
    notas_pieza TEXT,
    CONSTRAINT uq_odontograma_pieza UNIQUE (odontograma_id, numero_fdi)
);

CREATE TABLE hallazgos_superficie (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pieza_dental_id UUID NOT NULL REFERENCES piezas_dentales(id) ON DELETE CASCADE,
    superficie superficie_dental_enum NOT NULL,
    condicion condicion_dental_enum NOT NULL,
    estado_clinico estado_clinico_hallazgo_enum NOT NULL,
    color_hex VARCHAR(10) DEFAULT '#FF0000', -- #FF0000 (Rojo/Requerido), #0000FF (Azul/Existente)
    detalle TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 7. CATÁLOGO DE TRATAMIENTOS Y PLANES (SECUENCIA)
-- ==============================================================================

CREATE TABLE catalogo_tratamientos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo VARCHAR(30) UNIQUE NOT NULL,
    categoria categoria_tratamiento_enum NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    costo_base NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    duracion_estimada_min INTEGER DEFAULT 30 NOT NULL,
    activo BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE planes_tratamiento (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    titulo VARCHAR(200) NOT NULL,
    estado estado_plan_enum DEFAULT 'PROPUESTO' NOT NULL,
    costo_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    fecha_creacion DATE DEFAULT CURRENT_DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_clinica (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1), -- Siempre una sola fila
    moneda_simbolo VARCHAR(8) NOT NULL DEFAULT '$',
    nombre_clinica VARCHAR(120) NOT NULL DEFAULT 'Clínica Dental Gustavo',
    logo BYTEA,
    logo_tipo VARCHAR(20),
    tema_por_defecto VARCHAR(10) NOT NULL DEFAULT 'oscuro',
    CONSTRAINT configuracion_tema_valido CHECK (tema_por_defecto IN ('claro', 'oscuro')),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
INSERT INTO configuracion_clinica (id) VALUES (1);

-- Lo escribe el servicio de copias automáticas
CREATE TABLE estado_copias (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1), -- Siempre una sola fila
    ultima_exitosa TIMESTAMP WITH TIME ZONE,
    ultimo_error_en TIMESTAMP WITH TIME ZONE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
INSERT INTO estado_copias (id) VALUES (1);

CREATE TABLE items_plan_tratamiento (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES planes_tratamiento(id) ON DELETE CASCADE,
    tratamiento_id UUID NOT NULL REFERENCES catalogo_tratamientos(id),
    hallazgo_superficie_id UUID REFERENCES hallazgos_superficie(id) ON DELETE SET NULL,
    pieza_fdi INTEGER,
    orden_secuencia INTEGER DEFAULT 1 NOT NULL, -- 1, 2, 3... paso a paso cronológico
    fecha_programada DATE,
    estado estado_item_plan_enum DEFAULT 'PENDIENTE' NOT NULL,
    costo_acordado NUMERIC(12, 2) NOT NULL,
    observaciones TEXT,
    fecha_realizacion TIMESTAMP WITH TIME ZONE, -- Solo en estado COMPLETADO
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 8. CITAS Y DURACIÓN EFECTIVA EN SILLÓN
-- ==============================================================================

CREATE TABLE sillones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero INTEGER UNIQUE NOT NULL, -- Identifica al sillón en las citas; no cambia
    nombre VARCHAR(100) NOT NULL,
    especialidad VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE citas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    tratamiento_id UUID REFERENCES catalogo_tratamientos(id) ON DELETE SET NULL,
    fecha_inicio_programada TIMESTAMP WITH TIME ZONE NOT NULL,
    fecha_fin_programada TIMESTAMP WITH TIME ZONE NOT NULL,
    hora_llegada_recepcion TIMESTAMP WITH TIME ZONE,
    hora_inicio_sillon TIMESTAMP WITH TIME ZONE, -- Momento en que se sienta en sillón
    hora_fin_sillon TIMESTAMP WITH TIME ZONE,    -- Momento en que concluye la atención
    duracion_sillon_minutos INTEGER,            -- Minutos reales efectivos de atención
    estado estado_cita_enum DEFAULT 'PROGRAMADA' NOT NULL,
    motivo_consulta VARCHAR(255) NOT NULL,
    notas_adicionales TEXT,
    created_by_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 9. HISTORIA CLÍNICA (EVOLUCIONES / ATENCIONES DIARIAS)
-- ==============================================================================

CREATE TABLE visitas_evolucion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    asistente_id UUID REFERENCES asistentes(id) ON DELETE SET NULL,
    cita_id UUID UNIQUE REFERENCES citas(id) ON DELETE SET NULL,
    item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    proximo_item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    motivo_visita TEXT NOT NULL,
    diagnostico TEXT NOT NULL,
    procedimiento_realizado TEXT NOT NULL,
    receta_medicamentos TEXT,
    recomendaciones TEXT,
    fecha_proximo_control DATE,
    indicaciones_proxima_visita TEXT, -- Instrucciones para la siguiente cita
    generada_automaticamente BOOLEAN NOT NULL DEFAULT false, -- Creada al finalizar la cita: solo admite observaciones
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Observaciones de doctores y asistentes: solo se agregan, nunca se editan ni eliminan
CREATE TABLE observaciones_evolucion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visita_id UUID NOT NULL REFERENCES visitas_evolucion(id) ON DELETE CASCADE,
    autor_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    rol_autor VARCHAR(50) NOT NULL,
    texto TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);


-- ==============================================================================
-- 10. ESTUDIOS RADIOLÓGICOS E IMÁGENES DENTALES
-- ==============================================================================

CREATE TABLE radiografias_estudios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    subido_por_usuario_id UUID NOT NULL REFERENCES usuarios(id),
    visita_id UUID REFERENCES visitas_evolucion(id) ON DELETE SET NULL,
    pieza_fdi INTEGER,
    tipo_estudio tipo_estudio_imagen_enum NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    archivo_url VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'image/jpeg',
    tamano_bytes BIGINT,
    informe_diagnostico TEXT,
    fecha_toma DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 11. CAJA OPERATIVA, INGRESOS Y EGRESOS EN TIEMPO REAL
-- ==============================================================================

CREATE TABLE cajas_sesiones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_apertura_id UUID NOT NULL REFERENCES usuarios(id),
    usuario_cierre_id UUID REFERENCES usuarios(id),
    fecha_apertura TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    monto_inicial_fondo NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_ingresos_efectivo NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_egresos_efectivo NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    saldo_efectivo_esperado NUMERIC(12, 2) NOT NULL DEFAULT 0.00, -- Inicial + Ingresos - Egresos
    total_efectivo_contado NUMERIC(12, 2),
    diferencia_descuadre NUMERIC(12, 2),
    estado estado_caja_enum DEFAULT 'ABIERTA' NOT NULL,
    observaciones TEXT
);

-- Cuenta que se crea al finalizar una cita y se puede editar hasta confirmar el pago
CREATE TABLE cobros_cita (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cita_id UUID UNIQUE REFERENCES citas(id) ON DELETE SET NULL,
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    estado estado_cobro_cita_enum NOT NULL DEFAULT 'PENDIENTE',
    motivo_cierre TEXT,
    cerrado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE cobros_cita_lineas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cobro_id UUID NOT NULL REFERENCES cobros_cita(id) ON DELETE CASCADE,
    item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    concepto VARCHAR(255) NOT NULL,
    monto NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    costo_referencia NUMERIC(12, 2)
);

CREATE TABLE pagos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES planes_tratamiento(id) ON DELETE SET NULL,
    visita_id UUID REFERENCES visitas_evolucion(id) ON DELETE SET NULL,
    caja_sesion_id UUID REFERENCES cajas_sesiones(id) ON DELETE SET NULL,
    doctor_comision_id UUID REFERENCES doctores(id) ON DELETE SET NULL, -- Para comisiones
    porcentaje_comision NUMERIC(5, 2) DEFAULT 0 NOT NULL, -- Vigente al registrar el cobro
    registrado_por_usuario_id UUID NOT NULL REFERENCES usuarios(id),
    monto NUMERIC(12, 2) NOT NULL,
    metodo_pago metodo_pago_enum NOT NULL DEFAULT 'EFECTIVO',
    referencia_comprobante VARCHAR(150),
    es_cobro_directo BOOLEAN NOT NULL DEFAULT false, -- Consulta cobrada sin plan: no afecta el saldo de los planes
    cobro_cita_id UUID REFERENCES cobros_cita(id) ON DELETE SET NULL,
    anulado BOOLEAN NOT NULL DEFAULT false, -- Un pago anulado se conserva, pero deja de contar
    motivo_anulacion TEXT,
    fecha_anulacion TIMESTAMP WITH TIME ZONE,
    anulado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones TEXT
);

CREATE TABLE pagos_empleados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_empleado_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    caja_sesion_id UUID REFERENCES cajas_sesiones(id) ON DELETE SET NULL, -- Si salió de caja
    usuario_autoriza_id UUID NOT NULL REFERENCES usuarios(id),
    tipo_pago tipo_pago_empleado_enum NOT NULL,
    monto_base NUMERIC(12, 2) DEFAULT 0.00,
    monto_comisiones NUMERIC(12, 2) DEFAULT 0.00,
    deducciones_descuentos NUMERIC(12, 2) DEFAULT 0.00,
    monto_neto_pagado NUMERIC(12, 2) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL DEFAULT 'EFECTIVO_CAJA',
    referencia_pago VARCHAR(150),
    fecha_hora_pago TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones TEXT
);

CREATE TABLE egresos_caja (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    caja_sesion_id UUID NOT NULL REFERENCES cajas_sesiones(id) ON DELETE CASCADE,
    usuario_autoriza_id UUID NOT NULL REFERENCES usuarios(id),
    usuario_beneficiario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    pago_empleado_id UUID REFERENCES pagos_empleados(id) ON DELETE SET NULL,
    pago_anulado_id UUID REFERENCES pagos(id) ON DELETE SET NULL, -- Devolución en efectivo: no es un gasto
    categoria categoria_egreso_caja_enum NOT NULL,
    monto NUMERIC(12, 2) NOT NULL,
    concepto_motivo VARCHAR(255) NOT NULL,
    numero_recibo_comprobante VARCHAR(100),
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);


-- ==============================================================================
-- 12. ÓRDENES DE LABORATORIO Y PRÓTESIS DENTALES
-- ==============================================================================

CREATE TABLE ordenes_laboratorio_protesis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    egreso_caja_id UUID REFERENCES egresos_caja(id) ON DELETE SET NULL, -- Si se pagó desde caja
    laboratorio_nombre VARCHAR(150) NOT NULL,
    tipo_trabajo tipo_trabajo_protesis_enum NOT NULL,
    piezas_dentales VARCHAR(100) NOT NULL, -- Ej: "Pieza 16" o "11, 12, 21"
    color_guia_vita VARCHAR(50),           -- Ej: "A2", "A3.5", "Bleach"
    instrucciones_tecnicas TEXT,
    costo_laboratorio NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    fecha_envio DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_entrega_esperada DATE NOT NULL,
    fecha_recepcion_real DATE,
    estado estado_orden_protesis_enum DEFAULT 'ENVIADO' NOT NULL,
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==============================================================================
-- 13. ÍNDICES DE RENDIMIENTO (OPTIMIZACIÓN PARA CONSULTAS Y REPORTES)
-- ==============================================================================

-- Búsqueda de pacientes
CREATE INDEX idx_pacientes_documento ON pacientes(numero_documento);
CREATE INDEX idx_pacientes_apellidos ON pacientes(apellidos, nombres);

-- Agenda de citas y tiempos en sillón
CREATE INDEX idx_citas_doctor_fecha ON citas(doctor_id, fecha_inicio_programada);
CREATE INDEX idx_citas_paciente ON citas(paciente_id);
CREATE INDEX idx_citas_estado ON citas(estado);

-- Historial médico y atenciones
CREATE INDEX idx_visitas_paciente_fecha ON visitas_evolucion(paciente_id, fecha_hora DESC);
CREATE INDEX idx_visitas_doctor ON visitas_evolucion(doctor_id);
CREATE INDEX idx_visitas_asistente ON visitas_evolucion(asistente_id);
CREATE INDEX idx_observaciones_visita ON observaciones_evolucion(visita_id, created_at);

-- Reportes financieros y caja
CREATE INDEX idx_pagos_fecha ON pagos(fecha_hora);
CREATE INDEX idx_pagos_paciente ON pagos(paciente_id);
CREATE INDEX idx_pagos_caja_sesion ON pagos(caja_sesion_id);
CREATE INDEX idx_pagos_doctor_comision ON pagos(doctor_comision_id);
CREATE INDEX idx_egresos_caja_sesion ON egresos_caja(caja_sesion_id);
CREATE INDEX idx_cobros_cita_estado ON cobros_cita(estado);
CREATE INDEX idx_cobros_cita_paciente ON cobros_cita(paciente_id);
CREATE INDEX idx_cobros_cita_lineas_cobro ON cobros_cita_lineas(cobro_id);

-- Órdenes de prótesis
CREATE INDEX idx_ordenes_protesis_paciente ON ordenes_laboratorio_protesis(paciente_id);
CREATE INDEX idx_ordenes_protesis_doctor ON ordenes_laboratorio_protesis(doctor_id);
CREATE INDEX idx_ordenes_protesis_estado ON ordenes_laboratorio_protesis(estado);

-- Auditoría
CREATE INDEX idx_auditoria_tabla_registro ON auditoria_logs(tabla_afectada, registro_id);
CREATE INDEX idx_auditoria_usuario_fecha ON auditoria_logs(usuario_id, fecha_hora DESC);
CREATE INDEX idx_auditoria_accion ON auditoria_logs(accion);

-- Asistencia laboral
CREATE INDEX idx_asistencia_usuario_fecha ON registro_asistencia(usuario_id, fecha_hora DESC);


-- ==============================================================================
-- 14. TRIGGERS Y FUNCIONES AUTOMÁTICAS
-- ==============================================================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION actualizar_timestamp_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usuarios_updated_at
BEFORE UPDATE ON usuarios
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

CREATE TRIGGER trg_pacientes_updated_at
BEFORE UPDATE ON pacientes
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

CREATE TRIGGER trg_citas_updated_at
BEFORE UPDATE ON citas
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

CREATE TRIGGER trg_planes_updated_at
BEFORE UPDATE ON planes_tratamiento
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

-- Función para calcular automáticamente la duración del sillón en minutos al finalizar la cita
CREATE OR REPLACE FUNCTION calcular_duracion_sillon()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.hora_inicio_sillon IS NOT NULL AND NEW.hora_fin_sillon IS NOT NULL THEN
        NEW.duracion_sillon_minutos = ROUND(EXTRACT(EPOCH FROM (NEW.hora_fin_sillon - NEW.hora_inicio_sillon)) / 60);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calcular_duracion_sillon
BEFORE INSERT OR UPDATE ON citas
FOR EACH ROW EXECUTE FUNCTION calcular_duracion_sillon();

-- Nunca puede haber dos cajas abiertas a la vez
CREATE UNIQUE INDEX caja_unica_abierta ON cajas_sesiones ((1)) WHERE estado = 'ABIERTA';
