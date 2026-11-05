# Historias de Usuario - Sistema de Gestión Clínica Dental Gustavo
**Versión:** 2.0.0  
**Fecha de Actualización:** 2026-10-23  
**Estado:** Especificación Completa para Desarrollo y QA  
**Stack Backend:** FastAPI + SQLAlchemy ORM (PostgreSQL 14+)

---

## Índice General de Historias de Usuario

| Código | Módulo / Épica | Título | Estimación |
| :---: | :--- | :--- | :---: |
| **[HU-01](#hu-01-gestión-de-roles-y-asignación-de-permisos-granulares)** | Seguridad & RBAC | Gestión de Roles y Asignación de Permisos Granulares | 5 SP |
| **[HU-02](#hu-02-creación-de-nuevos-usuarios-y-asignación-de-roles-y-perfiles)** | Personal & Cuentas | Creación de Nuevos Usuarios y Asignación de Roles y Perfiles | 5 SP |
| **[HU-03](#hu-03-registro-y-ficha-médica-integral-de-pacientes)** | Pacientes & Clínica | Registro y Ficha Médica Integral de Pacientes | 3 SP |
| **[HU-04](#hu-04-odontograma-interactivo-y-creación-de-planes-de-tratamiento-secuenciales)** | Odontología | Odontograma Interactivo FDI y Planes Secuenciales | 8 SP |
| **[HU-05](#hu-05-agendamiento-de-citas-y-control-de-flujo-de-atención-en-sillón)** | Agenda & Boxes | Agendamiento de Citas y Control de Flujo en Sillón | 5 SP |
| **[HU-06](#hu-06-control-de-asistencia-y-fichaje-laboral-del-personal)** | Recursos Humanos | Control de Asistencia y Fichaje Laboral del Personal | 3 SP |
| **[HU-07](#hu-07-evolución-clínica-diaria-procedimientos-y-recetas-médicas)** | Historia Clínica | Evolución Clínica Diaria, Procedimientos y Recetas Médicas | 5 SP |
| **[HU-08](#hu-08-gestión-y-visor-de-radiografías-e-imágenes-intraorales)** | Imagenología Dental | Gestión y Visor de Radiografías e Imágenes Intraorales | 5 SP |
| **[HU-09](#hu-09-control-de-trabajos-de-laboratorio-protésico-y-prótesis)** | Laboratorio Dental | Control de Trabajos Protésicos y Órdenes de Laboratorio | 5 SP |
| **[HU-10](#hu-10-apertura-cierre-y-arqueo-de-caja-en-tiempo-real)** | Finanzas & Caja | Apertura, Cierre y Arqueo de Caja Operativa en Tiempo Real | 5 SP |
| **[HU-11](#hu-11-cobranzas-a-pacientes-recibos-y-aplicación-de-pagos)** | Facturación & Cobros | Cobranzas a Pacientes, Recibos y Aplicación de Pagos | 5 SP |
| **[HU-12](#hu-12-nómina-liquidación-de-sueldos-y-comisiones-médicas)** | Nómina & Comisiones | Liquidación de Nómina y Cálculo de Comisiones Médicas | 5 SP |
| **[HU-13](#hu-13-panel-de-auditoría-forense-y-trazabilidad-de-accesos)** | Seguridad & Compliance | Panel de Auditoría Forense y Trazabilidad de Accesos (`VIEW`) | 3 SP |
| **[HU-14](#hu-14-reportes-de-productividad-médica-rentabilidad-y-estadísticas)** | Business Intelligence | Reportes de Productividad Médica, Rentabilidad y KPIs | 5 SP |

---

### HU-01: Gestión de Roles y Asignación de Permisos Granulares

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-01` |
| **Épica** | Seguridad, Accesos y Control RBAC |
| **Prioridad** | Alta (Crítica) |
| **Estimación** | 5 Story Points |
| **Rol Principal** | Administrador de Clínica (`ADMIN`) |

#### Narrativa:
> **Como** Administrador de la Clínica  
> **Quiero** poder crear nuevos roles en el sistema y asignarles o modificar su lista de permisos por módulo  
> **Para** garantizar que cada perfil (doctor, asistente, recepcionista) solo tenga acceso a la información y acciones estrictamente necesarias para su labor.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Listar roles y permisos del sistema
  Dado que un usuario con rol "ADMIN" está autenticado con token JWT
  Cuando realiza una petición GET a "/api/v1/usuarios/permisos" y "/api/v1/usuarios/roles"
  Entonces el sistema responde con código HTTP 200 y el listado completo de módulos y acciones disponibles.

Escenario: Creación de un rol personalizado
  Dado que el Administrador ingresa un código de rol único (ej: "COORDINADOR_CLINICO"), nombre y descripción
  Cuando realiza un POST a "/api/v1/usuarios/roles"
  Entonces el rol queda persistido en la tabla "roles" con código HTTP 201 Created.

Escenario: Asignar permisos granulares a un rol
  Dado un rol existente identificado por "rol_id"
  Cuando el Administrador envía un listado de UUIDs de permisos a "POST /api/v1/usuarios/roles/{rol_id}/permisos"
  Entonces se actualiza la tabla relacional "roles_permisos" y los usuarios con ese rol heredan los permisos inmediatamente.

Escenario: Intento de modificación sin privilegios de administrador
  Dado que un usuario con rol "DOCTOR" o "RECEPCION" intenta crear o modificar permisos
  Cuando realiza la petición a los endpoints administrativos de roles
  Entonces el sistema rechaza la solicitud con código HTTP 403 Forbidden.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Rol`, `Permiso`, `RolPermiso`
- **Controlador:** `app/controllers/usuarios_controller.py`
- **Endpoints:**
  - `GET /api/v1/usuarios/roles`
  - `POST /api/v1/usuarios/roles`
  - `GET /api/v1/usuarios/permisos`
  - `GET /api/v1/usuarios/roles/{rol_id}/permisos`
  - `POST /api/v1/usuarios/roles/{rol_id}/permisos`

---

### HU-02: Creación de Nuevos Usuarios y Asignación de Roles y Perfiles

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-02` |
| **Épica** | Administración de Personal y Cuentas |
| **Prioridad** | Alta |
| **Estimación** | 5 Story Points |
| **Rol Principal** | Administrador de Clínica (`ADMIN`) |

#### Narrativa:
> **Como** Administrador de la Clínica  
> **Quiero** dar de alta a nuevos empleados (doctores, asistentes o recepcionistas), asignándoles credenciales de acceso, su rol y su perfil correspondiente  
> **Para** que cada miembro del equipo pueda acceder con su propio usuario, registrar su asistencia y tener trazabilidad de sus acciones.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Registro exitoso de nuevo usuario con contraseña cifrada
  Dado que el Administrador ingresa username, email, nombre, apellido, teléfono, password y selecciona un rol_id válido
  Cuando envía los datos a "POST /api/v1/usuarios/"
  Entonces el sistema almacena la contraseña hasheada mediante bcrypt (nunca en texto plano)
  Y el usuario se crea con estado "activo: true" y código HTTP 201 Created.

Escenario: Rechazo de duplicados
  Dado que ya existe un usuario registrado con username "jgomez" o email "jgomez@clinica.com"
  Cuando se intenta registrar otro usuario con el mismo username o email
  Entonces el sistema responde con HTTP 400 Bad Request indicando la duplicidad.

Escenario: Creación de perfil profesional de doctor
  Dado un usuario recién creado con rol "DOCTOR"
  Cuando se envía su especialidad, número de colegiatura y color de agenda a "POST /api/v1/usuarios/doctores/perfil"
  Entonces se genera su registro en la tabla "doctores" vinculado con clave foránea 1-a-1 al usuario.

Escenario: Desactivación preventiva de usuario
  Dado un empleado que finalizó su relación con la clínica
  Cuando el Administrador actualiza su cuenta con "activo: false" vía "PUT /api/v1/usuarios/{id}"
  Entonces el usuario queda inhabilitado para generar nuevos tokens de acceso o iniciar sesión.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Usuario`, `Doctor`, `Asistente`, `Rol`
- **Controlador:** `app/controllers/usuarios_controller.py`
- **Endpoints:**
  - `GET /api/v1/usuarios/`
  - `POST /api/v1/usuarios/`
  - `GET /api/v1/usuarios/{id}`
  - `PUT /api/v1/usuarios/{id}`
  - `POST /api/v1/usuarios/doctores/perfil`
  - `POST /api/v1/usuarios/asistentes/perfil`

---

### HU-03: Registro y Ficha Médica Integral de Pacientes

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-03` |
| **Épica** | Gestión Clínica y Pacientes |
| **Prioridad** | Alta |
| **Estimación** | 3 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR`, `RECEPCION` |

#### Narrativa:
> **Como** Recepcionista o Doctor  
> **Quiero** registrar a nuevos pacientes ingresando sus datos personales, de contacto y su anamnesis o antecedentes médicos  
> **Para** contar con un expediente clínico seguro, accesible y auditable desde el primer día que asiste a la clínica.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Registro de paciente con anamnesis inicial en una sola transacción
  Dado que se completan los datos filiatorios (nombres, apellidos, documento, fecha de nacimiento, teléfono)
  Y se especifican antecedentes médicos (alergias a medicamentos, enfermedades sistémicas)
  Cuando se envía la petición a "POST /api/v1/pacientes/"
  Entonces se crea el registro en "pacientes" y automáticamente su ficha en "antecedentes_medicos"
  Y se emite un log de auditoría tipo "INSERT" en "auditoria_logs".

Escenario: Auditoría de visualización (Acción VIEW)
  Dado que un doctor o recepcionista abre el expediente de un paciente
  Cuando se ejecuta "GET /api/v1/pacientes/{id}"
  Entonces el sistema responde con la información del paciente
  Y en segundo plano registra en "auditoria_logs" una fila con accion="VIEW", usuario_id, paciente_id, fecha_hora e IP.

Escenario: Búsqueda ágil de pacientes
  Dado que recepción necesita localizar rápidamente un paciente
  Cuando consulta "GET /api/v1/pacientes/?q=mendoza"
  Entonces el sistema busca por coincidencia insensible a mayúsculas en nombres, apellidos y número de documento.

Escenario: Consulta del saldo y estado de cuenta financiero
  Dado un paciente con planes aprobados y pagos realizados
  Cuando se consulta "GET /api/v1/pacientes/{id}/saldo"
  Entonces el sistema calcula en vivo: total_presupuestado, total_pagado, saldo_pendiente y estado_saldo ("AL_DIA", "DEUDOR" o "A_FAVOR").
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Paciente`, `AntecedenteMedico`, `AuditoriaLog`, `PlanTratamiento`, `Pago`
- **Controlador:** `app/controllers/pacientes_controller.py`
- **Endpoints:**
  - `GET /api/v1/pacientes/?q={texto}`
  - `POST /api/v1/pacientes/`
  - `GET /api/v1/pacientes/{id}`
  - `PUT /api/v1/pacientes/{id}`
  - `GET /api/v1/pacientes/{id}/saldo`
  - `PUT /api/v1/pacientes/{id}/antecedentes`

---

### HU-04: Odontograma Interactivo y Creación de Planes de Tratamiento Secuenciales

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-04` |
| **Épica** | Diagnóstico Clínico y Odontología |
| **Prioridad** | Alta |
| **Estimación** | 8 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR` |

#### Narrativa:
> **Como** Doctor / Odontólogo  
> **Quiero** interactuar con un tooth chart gráfico marcando patologías en las caras de los dientes y convertir esos hallazgos en un plan de tratamiento ordenado cronológicamente  
> **Para** explicarle visualmente el diagnóstico al paciente, presupuestar el tratamiento y definir con exactitud qué procedimiento toca en la siguiente visita.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Inicialización automática de piezas dentales FDI
  Dado un paciente que asiste a su primera evaluación clínica
  Cuando el doctor crea un odontograma con tipo_denticion="ADULTA_PERMANENTE"
  Entonces el sistema autogenera las 32 piezas dentales (FDI 11 al 48) vinculadas al odontograma.
  Si el tipo_denticion es "INFANTIL_DECIDUA", autogenera las 20 piezas temporales (FDI 51 al 85).

Escenario: Marcaje de patología en superficie con código de color
  Dado un diente seleccionado (ej: pieza 16)
  Cuando el doctor marca una caries en superficie "OCLUSAL_INCISAL" con estado_clinico="REQUERIDO_PATOLOGIA"
  Entonces se guarda en "hallazgos_superficie" con color_hex="#FF0000" (rojo) para representación visual.

Escenario: Creación de Plan de Tratamiento secuenciado
  Dado un odontograma con hallazgos requeridos
  Cuando el doctor formula un plan de tratamiento asociando procedimientos del catálogo
  Entonces cada ítem guarda su "orden_secuencia" (1º Limpieza, 2º Endodoncia, 3º Corona) y el costo acordado
  Y el sistema calcula el "costo_total" del plan automáticamente.

Escenario: Marcado de procedimiento para la siguiente sesión
  Dado un plan de tratamiento con múltiples procedimientos pendientes
  Cuando el doctor indica el procedimiento a realizar en la próxima cita
  Entonces ese ítem específico cambia su estado a "PROXIMA_SESION" para que recepción y asistentes preparen la atención.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Odontograma`, `PiezaDental`, `HallazgoSuperficie`, `CatalogoTratamiento`, `PlanTratamiento`, `ItemPlanTratamiento`
- **Controladores:** 
  - `app/controllers/odontograma_controller.py`
  - `app/controllers/tratamientos_controller.py`
- **Endpoints:**
  - `POST /api/v1/odontogramas/`
  - `GET /api/v1/odontogramas/{id}`
  - `PUT /api/v1/odontogramas/piezas/{id}`
  - `POST /api/v1/odontogramas/hallazgos`
  - `GET /api/v1/tratamientos/catalogo`
  - `POST /api/v1/tratamientos/planes`
  - `POST /api/v1/tratamientos/items`
  - `PUT /api/v1/tratamientos/items/{id}`

---

### HU-05: Agendamiento de Citas y Control de Flujo de Atención en Sillón

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-05` |
| **Épica** | Agenda Médica y Productividad |
| **Prioridad** | Media-Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR`, `RECEPCION` |

#### Narrativa:
> **Como** Recepcionista y Doctor  
> **Quiero** agendar citas vinculadas al tratamiento que le corresponde al paciente y registrar los momentos en que ingresa y sale del sillón dental  
> **Para** organizar el calendario de los boxes, evitar tiempos muertos y medir con precisión la duración real de cada intervención.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Agendamiento con enlace a procedimiento planificado
  Dado un paciente con un ítem de tratamiento en estado "PROXIMA_SESION"
  Cuando recepción agenda una cita con fecha_inicio, fecha_fin, doctor_id e item_plan_id
  Entonces la cita queda en estado "PROGRAMADA" vinculada al procedimiento correspondiente.

Escenario: Recepción del paciente en sala de espera
  Dado un paciente que se presenta físicamente en la clínica
  Cuando recepción actualiza la cita registrando "hora_llegada_recepcion"
  Entonces el estado de la cita cambia a "EN_ESPERA".

Escenario: Entrada del paciente al box (Inicio en sillón)
  Dado un paciente en espera que pasa al gabinete con el doctor
  Cuando se actualiza la cita con "hora_inicio_sillon"
  Entonces el estado de la cita cambia a "EN_SILLON".

Escenario: Finalización de la atención y cálculo automático del tiempo
  Dado un paciente que termina su procedimiento dental y se levanta del sillón
  Cuando el doctor actualiza la cita con "hora_fin_sillon" y estado="FINALIZADA"
  Entonces el trigger automático de PostgreSQL calcula:
    duracion_sillon_minutos = ROUND((hora_fin_sillon - hora_inicio_sillon) / 60)
  Y queda almacenado el tiempo neto exacto de ocupación del box.

Escenario: Registro de inasistencia o cancelación
  Dado un paciente que avisa que no podrá acudir o cuya hora límite de espera expiró
  Cuando recepción actualiza el estado a "CANCELADA" o "NO_ASISTIO"
  Entonces la cita se libera del calendario y suma a las estadísticas de ausentismo.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Cita`, `Doctor`, `Paciente`, `ItemPlanTratamiento`
- **Controlador:** `app/controllers/citas_controller.py`
- **Trigger PostgreSQL:** `trg_calcular_duracion_sillon`
- **Endpoints:**
  - `GET /api/v1/citas/?doctor_id=...&fecha_desde=...`
  - `POST /api/v1/citas/`
  - `PUT /api/v1/citas/{id}`
  - `PATCH /api/v1/citas/{id}/sillon`

---

### HU-06: Control de Asistencia y Fichaje Laboral del Personal

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-06` |
| **Épica** | Recursos Humanos y Jornada Laboral |
| **Prioridad** | Media |
| **Estimación** | 3 Story Points |
| **Roles Autorizados** | Todos los usuarios autenticados |

#### Narrativa:
> **Como** Doctor, Asistente o Empleado de la Clínica  
> **Quiero** registrar con un botón mi hora de entrada, salida e inicio/fin de descanso, capturando la IP y la marca de tiempo exacta  
> **Para** certificar mis horas de trabajo, justificar descansos y permitir al Administrador controlar el cumplimiento horario.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Fichaje de entrada o descanso
  Dado que un empleado inicia sesión en su terminal
  Cuando selecciona el tipo de evento ("ENTRADA", "INICIO_DESCANSO", "FIN_DESCANSO", "SALIDA") y presiona "Fichar"
  Entonces el sistema registra una fila en "registro_asistencia" con usuario_id, tipo_evento, fecha_hora (servidor) y la IP pública/local del cliente.

Escenario: Visualización restringida de fichajes
  Dado que un asistente o doctor consulta el historial de asistencias
  Cuando solicita "GET /api/v1/personal/asistencia"
  Entonces el sistema le retorna exclusivamente sus propios fichajes.
  Si el usuario tiene rol "ADMIN", puede filtrar por cualquier "usuario_id" y rango de fechas.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `RegistroAsistencia`, `Usuario`
- **Controlador:** `app/controllers/auth_controller.py` y `app/controllers/asistencia_controller.py`
- **Endpoints:**
  - `POST /api/v1/auth/fichar`
  - `GET /api/v1/personal/asistencia`

---

### HU-07: Evolución Clínica Diaria, Procedimientos y Recetas Médicas

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-07` |
| **Épica** | Historia Clínica Diaria |
| **Prioridad** | Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR` |

#### Narrativa:
> **Como** Odontólogo / Especialista  
> **Quiero** documentar la atención médica realizada en el sillón (diagnóstico, técnica, anestesia, materiales), emitir la receta farmacológica y vincular al asistente de gabinete  
> **Para** dejar constancia legal inalterable de la evolución médica, marcar como completado el paso del tratamiento y preparar la próxima sesión.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Registro de evolución diaria y avance de estados
  Dado un paciente sentado en el sillón dental
  Cuando el doctor completa: motivo_visita, diagnostico, procedimiento_realizado, receta_medicamentos, asistente_id y cita_id
  Y selecciona el "item_plan_id" realizado hoy y el "proximo_item_plan_id" para la siguiente cita
  Entonces se guarda el registro en "visitas_evolucion"
  Y el ítem ejecutado hoy cambia automáticamente a estado "COMPLETADO"
  Y el ítem de la siguiente cita pasa a estado "PROXIMA_SESION".

Escenario: Auditoría de lectura de evolución clínica
  Dado que cualquier usuario autorizado consulta una visita médica anterior vía "GET /api/v1/visitas/{id}"
  Cuando el sistema responde con la nota clínica y la receta
  Entonces se graba una auditoría tipo "VIEW" con seccion_consultada="HISTORIA_CLINICA_SESION".
```

#### Mapeo Técnico (API):
- **Modelos BD:** `VisitaEvolucion`, `ItemPlanTratamiento`, `Doctor`, `Asistente`, `Cita`, `AuditoriaLog`
- **Controlador:** `app/controllers/visitas_controller.py`
- **Endpoints:**
  - `POST /api/v1/visitas/`
  - `GET /api/v1/visitas/?paciente_id=...`
  - `GET /api/v1/visitas/{id}`
  - `PUT /api/v1/visitas/{id}`

---

### HU-08: Gestión y Visor de Radiografías e Imágenes Intraorales

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-08` |
| **Épica** | Diagnóstico por Imágenes |
| **Prioridad** | Media-Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR`, `ASISTENTE` |

#### Narrativa:
> **Como** Doctor u Odontólogo  
> **Quiero** subir y catalogar estudios radiológicos (panorámicas, periapicales, CBCT 3D, fotos clínicas) asignados al paciente o a una pieza dental específica con un informe diagnóstico  
> **Para** respaldar cirugías, endodoncias y tratamientos estéticos con evidencia visual antes, durante y después del tratamiento.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Subida de radiografía con metadatos clínicos
  Dado un paciente con indicación de estudio de imagen
  Cuando se registra la URL segura del archivo, tipo_estudio ("PANORAMICA", "PERIAPICAL", "CONE_BEAM_CBCT"), pieza_fdi opcional y el informe diagnóstico del doctor
  Entonces queda almacenado en "radiografias_estudios" con fecha de toma y usuario_subido.

Escenario: Consulta en el visor radiológico y auditoría
  Dado que un doctor abre una radiografía para inspección
  Cuando el endpoint "GET /api/v1/radiografias/{id}" es invocado
  Entonces se emite un log de auditoría "VIEW" en "auditoria_logs" protegiendo la confidencialidad de la imagen médica.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `RadiografiaEstudio`, `Paciente`, `VisitaEvolucion`, `AuditoriaLog`
- **Controlador:** `app/controllers/radiografias_controller.py`
- **Endpoints:**
  - `GET /api/v1/radiografias/?paciente_id=...`
  - `POST /api/v1/radiografias/`
  - `GET /api/v1/radiografias/{id}`
  - `PUT /api/v1/radiografias/{id}`
  - `DELETE /api/v1/radiografias/{id}`

---

### HU-09: Control de Trabajos de Laboratorio Protésico y Prótesis

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-09` |
| **Épica** | Laboratorio Dental y Prótesis |
| **Prioridad** | Media-Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `DOCTOR`, `RECEPCION` |

#### Narrativa:
> **Como** Doctor y Recepcionista  
> **Quiero** registrar las órdenes de prótesis enviadas a laboratorios externos (coronas de zirconio, prótesis removibles, carillas, placas de bruxismo) indicando color de guía Vita, costo del laboratorio y fechas de entrega  
> **Para** verificar que la pieza dental esté físicamente en la clínica antes de que el paciente acuda a su cita y controlar los gastos por protésico.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Envío de orden a laboratorio dental
  Dado un paciente que requiere una corona o prótesis
  Cuando el doctor registra: laboratorio_nombre, tipo_trabajo, piezas_dentales, color_guia_vita (ej: "A2"), costo_laboratorio y fecha_entrega_esperada
  Entonces la orden queda en estado "ENVIADO" o "EN_LABORATORIO".

Escenario: Recepción del trabajo en recepción
  Dado que el mensajero del laboratorio entrega el trabajo en la clínica
  Cuando recepción actualiza la orden a estado "RECIBIDO_EN_CLINICA" y marca fecha_recepcion_real
  Entonces la agenda de citas muestra un indicador verde señalando que la prótesis está lista para instalar.

Escenario: Pago al laboratorio desde la gaveta de caja
  Dado que el laboratorio cobra sus honorarios en la recepción en efectivo
  Cuando se registra el egreso en caja vinculado a la orden
  Entonces el dinero se descuenta de la sesión de caja activa y queda asociado en "ordenes_laboratorio_protesis.egreso_caja_id".
```

#### Mapeo Técnico (API):
- **Modelos BD:** `OrdenLaboratorioProtesis`, `Paciente`, `Doctor`, `EgresoCaja`, `CajaSesion`
- **Controlador:** `app/controllers/protesis_controller.py`
- **Endpoints:**
  - `GET /api/v1/protesis/?paciente_id=...&estado=...`
  - `POST /api/v1/protesis/`
  - `PUT /api/v1/protesis/{id}`

---

### HU-10: Apertura, Cierre y Arqueo de Caja Operativa en Tiempo Real

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-10` |
| **Épica** | Finanzas y Control de Caja |
| **Prioridad** | Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `RECEPCION` |

#### Narrativa:
> **Como** Recepcionista y Administrador  
> **Quiero** abrir el turno de caja con un fondo de cambio, registrar cobros, salidas menores y realizar el arqueo final comparando lo contado físicamente contra lo esperado por el sistema  
> **Para** evitar pérdidas de dinero físico, controlar la gaveta en tiempo real y detectar faltantes o sobrantes al cierre del turno.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Apertura de turno con fondo inicial
  Dado que no existe ninguna caja abierta en el sistema
  Cuando recepción ingresa un monto_inicial_fondo (ej: $100.00) y presiona "Abrir Caja"
  Entonces se crea una "cajas_sesiones" en estado "ABIERTA" con saldo_efectivo_esperado = $100.00.

Escenario: Monitoreo en tiempo real del dinero en gaveta
  Dado una caja abierta con ingresos en efectivo de $500 y egresos en efectivo de $80
  Cuando se consulta "GET /api/v1/caja/estado"
  Entonces el sistema responde:
    efectivo_actual_en_gaveta = monto_inicial ($100) + cobros ($500) - salidas ($80) = $520.00.

Escenario: Cierre de caja y cálculo de descuadre
  Dado que finaliza la jornada laboral
  Cuando recepción cuenta el dinero físico (ej: cuenta $515.00) e invoca "POST /api/v1/caja/cerrar"
  Entonces el sistema calcula:
    diferencia_descuadre = total_efectivo_contado ($515.00) - saldo_esperado ($520.00) = -$5.00 (Faltante)
  Y la caja pasa a estado "CERRADA" registrando el usuario_cierre_id y fecha_cierre.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `CajaSesion`, `Pago`, `EgresoCaja`, `Usuario`
- **Controlador:** `app/controllers/caja_controller.py`
- **Endpoints:**
  - `GET /api/v1/caja/estado`
  - `POST /api/v1/caja/abrir`
  - `POST /api/v1/caja/cerrar`
  - `POST /api/v1/caja/egresos`

---

### HU-11: Cobranzas a Pacientes, Recibos y Aplicación de Pagos

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-11` |
| **Épica** | Facturación y Pagos de Pacientes |
| **Prioridad** | Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN`, `RECEPCION` |

#### Narrativa:
> **Como** Recepcionista  
> **Quiero** registrar los pagos de los pacientes en efectivo, tarjetas o transferencias, vinculándolos al plan de tratamiento o visita y asignando la comisión al doctor  
> **Para** actualizar el saldo deudor del paciente en tiempo real y certificar los ingresos de la clínica.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Registro de cobro en efectivo y actualización de caja
  Dado un paciente con saldo deudor en un plan de tratamiento
  Cuando recepción registra un pago en efectivo por $150.00 con "metodo_pago=EFECTIVO"
  Entonces se inserta la fila en "pagos" vinculada a la sesión de caja activa
  Y el "total_ingresos_efectivo" de la caja aumenta en $150.00 automáticamente.

Escenario: Registro de cobro bancario (Tarjeta o Transferencia)
  Dado un paciente que paga con tarjeta de débito o transferencia bancaria
  Cuando se registra el pago con su número de referencia de comprobante
  Entonces se descuenta del saldo del paciente, pero NO altera el efectivo físico de la gaveta de caja.

Escenario: Actualización instantánea del saldo deudor del paciente
  Dado un paciente con presupuesto de $800 y pagos acumulados de $300
  Cuando se registra un nuevo abono de $200
  Entonces "GET /api/v1/pacientes/{id}/saldo" refleja saldo_pendiente = $300.00 de inmediato.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Pago`, `Paciente`, `PlanTratamiento`, `VisitaEvolucion`, `CajaSesion`, `Doctor`
- **Controlador:** `app/controllers/caja_controller.py`
- **Endpoints:**
  - `POST /api/v1/caja/pagos`
  - `GET /api/v1/pacientes/{id}/saldo`

---

### HU-12: Nómina, Liquidación de Sueldos y Comisiones Médicas

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-12` |
| **Épica** | Nómina y Honorarios Médicos |
| **Prioridad** | Media-Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN` |

#### Narrativa:
> **Como** Administrador de Clínica  
> **Quiero** calcular automáticamente las comisiones acumuladas de los doctores en base a sus tratamientos cobrados y emitir recibos de pago salarial o adelantos  
> **Para** liquidar con exactitud los honorarios profesionales, deducir anticipos entregados en efectivo y mantener la transparencia salarial.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Cálculo automatizado de comisiones por doctor
  Dado un doctor con un contrato del 40.00% sobre tratamientos realizados
  Y cobros acumulados por sus tratamientos de $3,000.00 en el mes
  Cuando el Administrador consulta "GET /api/v1/empleados/comisiones-doctor/{doctor_id}"
  Entonces el sistema calcula:
    comision_bruta_generada = $3,000.00 * 40% = $1,200.00
    saldo_comision_por_pagar = $1,200.00 - comisiones_ya_liquidadas.

Escenario: Pago de anticipo en efectivo desde la caja diaria
  Dado un empleado que solicita un adelanto de $100.00 en efectivo
  Cuando el Administrador registra el pago con "metodo_pago=EFECTIVO_CAJA"
  Entonces se guarda en "pagos_empleados"
  Y simultáneamente se genera una fila en "egresos_caja" descontando los $100.00 de la gaveta activa.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `ContratoRemuneracion`, `PagoEmpleado`, `EgresoCaja`, `CajaSesion`, `Doctor`, `Usuario`
- **Controlador:** `app/controllers/empleados_controller.py`
- **Endpoints:**
  - `GET /api/v1/empleados/pagos`
  - `POST /api/v1/empleados/pagos`
  - `GET /api/v1/empleados/comisiones-doctor/{doctor_id}`

---

### HU-13: Panel de Auditoría Forense y Trazabilidad de Accesos

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-13` |
| **Épica** | Seguridad, Auditoría y Compliance |
| **Prioridad** | Media |
| **Estimación** | 3 Story Points |
| **Roles Autorizados** | `ADMIN` |

#### Narrativa:
> **Como** Administrador o Auditor de la Clínica  
> **Quiero** inspeccionar el registro cronológico inmutable de todas las inserciones, modificaciones, eliminaciones y consultas de lectura (`VIEW`) a datos sensibles  
> **Para** cumplir con normativas de protección de datos médicos, detectar posibles fugas de información y saber con exactitud quién consultó qué ficha médica.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Trazabilidad de consultas de lectura médica
  Dado que un usuario abre un odontograma o historial médico
  Cuando se genera el evento "VIEW" en "auditoria_logs"
  Entonces el Administrador puede buscar en "GET /api/v1/auditoria/?accion=VIEW" y observar:
    usuario_id, nombre del empleado, tabla_afectada, registro_id, fecha_hora exacta, dirección IP y navegador (User-Agent).

Escenario: Auditoría de cambios críticos (Datos Previos vs Nuevos)
  Dado que un usuario modifica el costo de un tratamiento o los datos de un paciente
  Cuando se ejecuta la actualización
  Entonces el log guarda en campos JSONB "datos_previos" y "datos_nuevos", permitiendo comparar el antes y después.
```

#### Mapeo Técnico (API):
- **Modelos BD:** `AuditoriaLog`, `Usuario`
- **Controlador:** `app/controllers/auditoria_controller.py`
- **Endpoints:**
  - `GET /api/v1/auditoria/?usuario_id=...&tabla_afectada=...&accion=...`

---

### HU-14: Reportes de Productividad Médica, Rentabilidad y Estadísticas

| Atributo | Detalle |
| :--- | :--- |
| **Código** | `HU-14` |
| **Épica** | Analítica de Negocio (Business Intelligence) |
| **Prioridad** | Media-Alta |
| **Estimación** | 5 Story Points |
| **Roles Autorizados** | `ADMIN` |

#### Narrativa:
> **Como** Director o Dueño de la Clínica  
> **Quiero** visualizar paneles con métricas de los tratamientos más realizados, tiempos efectivos en sillón por odontólogo y tasas de inasistencia  
> **Para** optimizar la compra de insumos, ajustar tarifas, medir la eficiencia de los boxes y proyectar el crecimiento de la clínica.

#### Criterios de Aceptación (Gherkin):
```gherkin
Escenario: Reporte de tratamientos con mayor demanda
  Dado un rango de fechas seleccionado (ej: mes actual)
  Cuando el Administrador solicita la analítica de procedimientos
  Entonces el sistema agrupa los ítems completados en "items_plan_tratamiento" y "visitas_evolucion"
  Y devuelve el ranking ordenado por cantidad realizada y facturación total generada.

Escenario: Métrica de ocupación y tiempo en sillón dental
  Dado el registro de citas finalizadas en el período
  Cuando se calcula la productividad médica
  Entonces el sistema suma "duracion_sillon_minutos" por doctor y calcula el promedio de atención por cita y la tasa de pacientes ausentes ("NO_ASISTIO").
```

#### Mapeo Técnico (API):
- **Modelos BD:** `Cita`, `VisitaEvolucion`, `CatalogoTratamiento`, `ItemPlanTratamiento`, `Pago`
- **Consultas SQL Optimizadas:** Indexadas por `(doctor_id, fecha_inicio_programada)` y `(fecha_hora, metodo_pago)`.
