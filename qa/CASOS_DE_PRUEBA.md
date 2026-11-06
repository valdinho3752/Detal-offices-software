# Casos de prueba: sistema de la clínica dental

Plan de pruebas manuales para la instalación **local de una sola sede**. Cada caso indica qué hacer y qué debe ocurrir.

## 1. Cómo usar este documento

### Columnas

| Columna | Significado |
|---|---|
| **ID** | Identificador del caso. Úsalo al reportar un defecto |
| **Tipo** | `F` funcional, `N` negativo o dato inválido, `S` seguridad y permisos, `I` integración entre módulos, `V` visual, `O` operación |
| **Caso y pasos** | Lo que se prueba y cómo |
| **Resultado esperado** | Lo que debe ocurrir para aprobarlo |
| **Prio** | `P1` bloquea la salida a producción, `P2` importante, `P3` menor |
| **Estado** | `OK`, `FALLA`, `MANUAL` (requiere otro equipo, hardware o personas), `PARCIAL` (simulado; falta confirmarlo en el equipo real) o `DECIDIR` (funcionamiento comprobado; falta una decisión de la clínica) |

Los casos marcados con **[API]** se prueban contra la API, porque la pantalla no permite esa acción. Usan `curl` o una herramienta similar, con el token de la sesión.

### Criterio de salida

- 100 % de los casos `P1` en `OK`.
- Al menos 95 % de los casos `P2` en `OK`, con los fallos restantes aceptados por escrito.
- Ningún defecto abierto que afecte dinero, datos clínicos o permisos.
- Una restauración real de copia de seguridad completada con éxito (`OPE-10` y `OPE-11`).

### Automatización

Las pruebas con Playwright están en `qa/automatizacion/` y escriben aquí la columna Estado. Requieren Docker Desktop y Microsoft Edge:

```powershell
python -m venv qa\.venv
qa\.venv\Scripts\pip install -r qa\automatizacion\requirements.txt
qa\.venv\Scripts\python qa\automatizacion\ejecutar.py
```

Levanta una instalación aparte, sin tocar tus datos, y deja el resumen en `qa/resultados/RESUMEN.md`. Tarda cerca de 40 minutos, porque incluye instalaciones completas, carga y una espera real de 15 minutos. Los motivos de cada caso `MANUAL`, `PARCIAL` y `DECIDIR` están en `qa/automatizacion/casos_no_automatizables.py` y en el resumen. Para el criterio de salida, solo cuenta `OK`.

### Registro de defectos

Para cada defecto anota: ID del caso, usuario y rol, pantalla, pasos exactos, resultado esperado, resultado obtenido, captura de pantalla y hora. Si es un error del servidor, añade la salida de `docker compose logs backend`.

## 2. Preparación del entorno

**No uses la base real.** Levanta una instalación aparte con su propio volumen, en PowerShell, desde la carpeta del proyecto:

```powershell
$env:CLINICA_PUERTO_WEB = "8081"
$env:CLINICA_RESPALDOS = "C:\qa-respaldos"
docker compose -p clinica-qa up --build -d
```

La web de QA queda en <http://localhost:8081>. Para los casos con HTTPS añade `--profile https` y define antes `CLINICA_PUERTO_HTTP` y `CLINICA_PUERTO_HTTPS`.

Esta instalación usa los archivos `.env.docker` y `.env.docker.admin` del proyecto. Si ya borraste `.env.docker.admin`, vuelve a crearlo temporalmente con una línea `ADMIN_PASSWORD=` y una contraseña de al menos 12 caracteres. Sin ese archivo, la primera instalación no arranca.

Para borrar todo al terminar o para empezar de cero:

```powershell
docker compose -p clinica-qa --profile https --profile herramientas down -v
```

### Usuarios de prueba

Créalos desde Usuarios & Roles. En su primer ingreso, cada uno cambiará su contraseña.

| Alias | Rol | Datos |
|---|---|---|
| `qa_admin2` | Administrador | Segundo administrador |
| `qa_doc1` | Doctor | Contrato de 40 % de comisión |
| `qa_doc2` | Doctor | Contrato mixto: sueldo 2.000 y 10 % de comisión |
| `qa_asi` | Asistente | Sin contrato |
| `qa_rec` | Recepción | Sueldo fijo mensual de 3.000 |
| `qa_custom` | Rol personalizado | Solo `PACIENTES_READ` y `REPORTES_READ` |

### Datos de prueba

- 5 pacientes: uno adulto con alergias, uno menor, uno con plan aprobado, uno con plan propuesto y uno sin plan.
- 5 tratamientos en el catálogo, de categorías distintas y con precio.
- 3 sillones activos, que son los iniciales.
- Caja abierta con un fondo de 1.000.

### Permisos iniciales por rol

| Módulo | Admin | Doctor | Asistente | Recepción |
|---|---|---|---|---|
| Pacientes | Todo | Ver, crear, editar, antecedentes | Ver | Ver, crear, editar |
| Citas | Todo | Ver, crear, editar, sillón (solo las propias) | Ver, editar, sillón | Ver, crear, editar, sillón |
| Odontograma | Todo | Ver, crear, editar, borrar | Ver | Sin acceso |
| Tratamientos y planes | Todo | Ver, crear, editar | Ver | Ver |
| Catálogo de tratamientos | Administra | Solo consulta por API | Solo consulta por API | Solo consulta por API |
| Evolución | Todo | Ver, crear, observar | Ver, observar | Sin acceso |
| Radiografías | Todo | Ver, crear | Ver, crear | Sin acceso |
| Prótesis | Todo | Ver, crear, actualizar | Ver | Ver, actualizar |
| Caja y cobros | Todo, incluida la anulación | Sin acceso | Sin acceso | Ver, abrir, cerrar, cobrar, egresos |
| Nómina | Todo | Solo la propia | Sin acceso | Sin acceso |
| Marcar turno | Sí | Sí | Sí | Sí |
| Auditoría y reportes | Sí | No | No | No |
| Usuarios y roles | Sí | No | No | No |
| Sillones y Configuración | Sí | No | No | No |

---

## 3. Acceso y sesión

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| ACC-01 | F | Entrar con usuario y contraseña correctos | Abre el Panel Principal con el nombre y rol correctos | P1 | OK |
| ACC-02 | N | Entrar con contraseña incorrecta | «Credenciales incorrectas»; sigue en el acceso | P1 | OK |
| ACC-03 | N | Entrar con un usuario inexistente | El mismo mensaje que con contraseña incorrecta, sin revelar si el usuario existe | P1 | OK |
| ACC-04 | N | Enviar el formulario con campos vacíos | El navegador exige completarlos y no envía nada | P2 | OK |
| ACC-05 | S | Hacer 5 intentos fallidos y un sexto | Del sexto en adelante: «Demasiados intentos fallidos» con los minutos de espera | P1 | OK |
| ACC-06 | S | Durante el bloqueo, usar la contraseña correcta | También se rechaza hasta que venza el bloqueo | P1 | OK |
| ACC-07 | S | Esperar 15 minutos tras el bloqueo y entrar | Entra con normalidad | P2 | OK |
| ACC-08 | F | Hacer 4 fallos, un acierto, salir y hacer 4 fallos más | El acierto reinició el conteo: no se bloquea | P2 | OK |
| ACC-09 | S | Bloquear el usuario A y entrar con el usuario B desde el mismo equipo | B entra con normalidad | P2 | OK |
| ACC-10 | S | Bloquear un usuario desde un equipo e intentar entrar desde otro | Desde el otro equipo sí puede entrar | P2 | OK |
| ACC-11 | S | Probar 50 usuarios falsos distintos desde un equipo | El equipo queda frenado durante la ventana de 15 minutos, también para usuarios válidos | P3 | OK |
| ACC-12 | F | Reiniciar el backend durante un bloqueo | El bloqueo desaparece, porque se guarda en memoria | P3 | OK |
| ACC-13 | N | Entrar con un usuario desactivado y contraseña correcta | «Este usuario se encuentra inactivo» | P1 | OK |
| ACC-14 | S | Revisar la pantalla de acceso y el código de la página | No hay usuarios ni contraseñas de ejemplo | P1 | OK |
| ACC-15 | F | Abrir una ruta interna sin sesión, como `/caja` | Redirige al acceso | P1 | OK |
| ACC-16 | F | Cerrar sesión y usar el botón Atrás | No muestra datos protegidos; vuelve al acceso | P1 | OK |
| ACC-17 | S | Alterar el token guardado en el navegador y recargar | Cierra la sesión y lleva al acceso | P1 | OK |
| ACC-18 | S | Esperar 8 horas con la sesión abierta y operar | La sesión vence y lleva al acceso | P2 | OK |
| ACC-19 | S | Desactivar a un usuario con la sesión abierta | Su siguiente acción se rechaza | P1 | OK |
| ACC-20 | F | Abrir la misma cuenta en dos equipos | Ambas sesiones funcionan hasta que se cambie la contraseña | P3 | OK |
| ACC-21 | F | Recargar la página con sesión activa | Sigue dentro, en la misma pantalla | P2 | OK |
| ACC-22 | F | Entrar usando el correo, en mayúsculas o minúsculas | Entra igual que con el usuario | P2 | OK |
| ACC-23 | S | Enviar `' OR 1=1 --` como usuario | Se rechaza como credenciales incorrectas | P1 | OK |
| ACC-24 | V | Revisar el acceso en modo claro, modo oscuro y celular | Se ve completo, con nombre y logo de la clínica | P3 | OK |

## 4. Contraseñas

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| PWD-01 | F | Primer ingreso de un usuario recién creado | Aparece un formulario obligatorio para cambiar la contraseña, sin botón Cancelar | P1 | OK |
| PWD-02 | N | Intentar cerrar ese formulario o usar el menú por detrás | No se puede operar hasta cambiarla | P1 | OK |
| PWD-03 | N | Contraseña nueva de menos de 8 caracteres | Se rechaza con un mensaje claro | P1 | OK |
| PWD-04 | N | Contraseña solo con letras o solo con números | «Debe combinar letras y números» | P1 | OK |
| PWD-05 | N | Contraseña común, como `Password123` o `admin123` | «Demasiado común» | P2 | OK |
| PWD-06 | N | Las dos contraseñas nuevas no coinciden | «No coinciden» | P2 | OK |
| PWD-07 | N | Contraseña actual incorrecta | «La contraseña actual no es correcta» | P1 | OK |
| PWD-08 | N | Nueva igual a la actual | «Debe ser distinta de la actual» | P2 | OK |
| PWD-09 | F | Cambio válido | Sigue en su sesión, sin el aviso; la anterior deja de servir y la nueva entra | P1 | OK |
| PWD-10 | S | Cambiarla con otra sesión abierta en otro equipo | La otra sesión se cierra en su siguiente acción | P1 | OK |
| PWD-11 | F | Cambio voluntario con el botón de la llave | Tiene Cancelar y cambia correctamente | P2 | OK |
| PWD-12 | S | El administrador restablece la contraseña de otra persona | Se cierran sus sesiones y debe cambiarla al entrar | P1 | OK |
| PWD-13 | F | Editar otros datos de un usuario, sin tocar su contraseña | Su sesión sigue activa | P2 | OK |
| PWD-14 | S | Revisar la auditoría tras un cambio | Figura `CAMBIO_CONTRASENA`, sin ninguna contraseña en el registro | P1 | OK |
| PWD-15 | N | Administrador asigna una contraseña débil al crear o editar | Se rechaza con mensaje legible, sin texto técnico | P1 | OK |
| PWD-16 | O | Ejecutar `scripts/restablecer_admin.py` con el administrador desactivado | Lo reactiva, cambia la contraseña y cierra sus sesiones | P1 | OK |
| PWD-17 | N | Ejecutar ese script con un usuario inexistente o una contraseña débil | Falla con un mensaje y no cambia nada | P2 | OK |
| PWD-18 | S | [API] Con un usuario que debe cambiar su contraseña, operar por API sin cambiarla | Responde 403 hasta cambiarla; solo permite ver sus datos y cambiarla | P1 | OK |

## 5. Usuarios, roles y permisos

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| USU-01 | F | Crear un usuario de cada rol del sistema | Aparece en la lista con su rol | P1 | OK |
| USU-02 | F | Crear un doctor con especialidad, colegiatura y color | Se crea su perfil médico y aparece en las listas de doctores | P1 | OK |
| USU-03 | F | Crear un asistente | Se crea su perfil de asistente | P2 | OK |
| USU-04 | N | Usuario con nombre repetido | «El nombre de usuario ya está en uso» | P1 | OK |
| USU-05 | N | Correo repetido | «El correo electrónico ya está registrado» | P1 | OK |
| USU-06 | N | Correo con formato inválido | Se rechaza | P2 | OK |
| USU-07 | N | Campos obligatorios vacíos | No permite guardar | P2 | OK |
| USU-08 | F | Editar nombre, teléfono y rol | Los cambios se guardan y se reflejan | P2 | OK |
| USU-09 | F | Buscar por usuario, nombre y correo | Filtra correctamente | P3 | OK |
| USU-10 | F | Desactivar y reactivar un usuario | El estado cambia y el acceso se bloquea y se restablece | P1 | OK |
| USU-11 | S | El administrador intenta desactivarse a sí mismo | «No puedes desactivar tu propia cuenta» | P1 | OK |
| USU-12 | S | El administrador intenta quitarse su rol | Se rechaza | P1 | OK |
| USU-13 | S | Con dos administradores activos, uno desactiva al otro | Se permite | P2 | OK |
| USU-14 | S | [API] Intentar dejar el sistema sin ningún administrador activo | «Debe quedar al menos un administrador activo» | P1 | OK |
| USU-15 | F | Crear un rol personalizado con permisos concretos | Se crea, y un usuario con ese rol solo ve lo permitido | P1 | OK |
| USU-16 | S | Quitar un permiso a un rol con un usuario conectado | Se aplica en su siguiente petición | P1 | OK |
| USU-17 | N | Crear un rol sin nombre | Se rechaza | P3 | OK |
| USU-18 | S | Un usuario con `USUARIOS_MANAGE` que no es administrador intenta editar a un administrador o a sí mismo | Se rechaza | P1 | OK |
| USU-19 | S | Un usuario con `USUARIOS_MANAGE` intenta crear otro administrador | Se rechaza | P1 | OK |
| USU-20 | S | Un usuario con `ROLES_MANAGE` intenta darse permisos que no tiene | Se rechaza: no hay escalada de privilegios | P1 | OK |
| USU-21 | S | Comprobar el menú de cada rol con la tabla de permisos | Solo aparecen los módulos permitidos | P1 | OK |
| USU-22 | S | Escribir en la barra de direcciones una ruta no permitida | Vuelve al Panel Principal | P1 | OK |
| USU-23 | S | [API] Llamar con el token de cada rol a una ruta que no le corresponde | Responde 403 | P1 | OK |
| USU-24 | S | [API] Llamar a cualquier ruta protegida sin token | Responde 401 | P1 | OK |
| USU-25 | S | Revisar la respuesta de usuarios | Nunca incluye la contraseña ni su hash | P1 | OK |
| USU-26 | F | Desactivar a un doctor con citas futuras | Decidir el comportamiento: sus citas siguen visibles y deben poder reasignarse | P2 | OK |

## 6. Pacientes

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| PAC-01 | F | Registrar un paciente con todos los datos | Aparece en la lista; la ficha muestra todo | P1 | OK |
| PAC-02 | F | Registrar un paciente solo con los obligatorios | Se guarda correctamente | P1 | OK |
| PAC-03 | N | Documento repetido | «Ya existe un paciente registrado con el documento…» | P1 | OK |
| PAC-04 | N | Editar y usar el documento de otro paciente | «Ya existe otro paciente con el documento…» | P1 | OK |
| PAC-05 | N | Fecha de nacimiento futura | «No puede ser futura», al crear y al editar | P1 | OK |
| PAC-06 | N | Correo inválido | Se rechaza | P2 | OK |
| PAC-07 | N | Campos obligatorios vacíos | No permite guardar | P2 | OK |
| PAC-08 | N | Nombre de 5.000 caracteres | Mensaje claro, sin error interno | P2 | OK |
| PAC-09 | N | Pegar caracteres especiales o emojis en el nombre | Se guarda y se muestra bien, o se rechaza con mensaje | P3 | OK |
| PAC-10 | S | Escribir `<script>alert(1)</script>` en nombre y dirección | Se muestra como texto; no se ejecuta nada | P1 | OK |
| PAC-11 | F | Editar los datos de un paciente | Los cambios se guardan y quedan en auditoría | P2 | OK |
| PAC-12 | F | Registrar alergias y enfermedades sistémicas | Se muestran de forma visible en la ficha | P1 | OK |
| PAC-13 | F | Editar antecedentes como doctor | Se actualizan | P1 | OK |
| PAC-14 | S | Editar antecedentes como recepción | [API] Responde 403: no tiene ese permiso | P1 | OK |
| PAC-15 | F | Buscar por nombre, apellido y documento | Encuentra coincidencias parciales, sin importar mayúsculas | P1 | OK |
| PAC-16 | F | Buscar algo que no existe | «No se encontraron pacientes» | P3 | OK |
| PAC-17 | F | Abrir la ficha y usar sus accesos: Agendar Cita, Odontograma, Evolución, Radiografías y Cobranza | Cada uno abre su módulo con ese paciente seleccionado | P2 | OK |
| PAC-18 | I | Comparar el saldo de la ficha con Cobranzas | Es exactamente el mismo | P1 | OK |
| PAC-19 | S | Abrir una ficha y revisar la auditoría | Queda un registro `VIEW` del acceso | P2 | OK |
| PAC-20 | S | Asistente intenta crear o editar | No ve esos botones; [API] responde 403 | P1 | OK |
| PAC-21 | F | Marcar un paciente como inactivo | Decidir el comportamiento: su historia se conserva y su estado se ve claramente | P2 | DECIDIR |
| PAC-22 | S | [API] Intentar eliminar un paciente | No existe esa acción: responde 405 | P1 | OK |
| PAC-23 | F | Listado con más de 100 pacientes | Se puede encontrar a cualquiera; la pantalla responde bien | P2 | OK |
| PAC-24 | V | Revisar buscador y formulario del paciente | Hablan de «documento», sin referencias a otro país; CI es la opción predeterminada | P3 | OK |
| PAC-25 | F | Registrar en pantalla, sin correo, con sexo, dirección y alergias | Se guarda, y la ficha muestra sexo, dirección y alergias | P0 | OK |
| PAC-26 | F | Editar en pantalla un paciente: cambiar alergias y dejar el correo vacío | Se guarda y la ficha se actualiza sin recargar | P1 | OK |

## 7. Odontograma

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| ODO-01 | F | Abrir el odontograma de un paciente nuevo | Se muestran los 32 dientes adultos correctamente numerados | P1 | OK |
| ODO-02 | F | Cambiar a dentición temporal | Se muestran 20 dientes (51–55, 61–65, 71–75, 81–85) | P1 | OK |
| ODO-03 | F | Marcar una cara con el estado de diagnóstico inicial | Se pinta con su color y queda en «Estado de Ingreso Inicial» | P1 | OK |
| ODO-04 | F | Marcar una cara con «Plan de tratamiento» | Se pinta de rojo | P1 | OK |
| ODO-05 | F | Marcar una cara con el estado de alta clínica | Se pinta de azul | P1 | OK |
| ODO-06 | F | Marcar una pieza como inexistente | Aparece tachada, con la etiqueta Ausente | P1 | OK |
| ODO-07 | F | Probar cada cara: vestibular, palatina o lingual, mesial, distal, oclusal o incisal, raíz y general | Se pinta justo la cara elegida | P1 | OK |
| ODO-08 | F | Comprobar las caras mesiales de los cuatro cuadrantes | Quedan orientadas hacia la línea media | P2 | OK |
| ODO-09 | F | Limpiar una cara | Solo esa cara vuelve a su estado inicial | P1 | OK |
| ODO-10 | F | Limpiar el diente completo | Se quitan los hallazgos de todas sus caras | P1 | OK |
| ODO-11 | F | Guardar el diagnóstico inicial y recargar | Los hallazgos siguen allí | P1 | OK |
| ODO-12 | F | Eliminar un registro de la tabla de ingreso | Desaparece de la tabla y del gráfico | P2 | OK |
| ODO-13 | F | Asignar un tratamiento del catálogo a una cara | Se añade al plan con pieza, cara y precio | P1 | OK |
| ODO-14 | F | Buscar tratamiento por nombre y por código | Encuentra coincidencias | P2 | OK |
| ODO-15 | F | Un tratamiento desactivado en el catálogo | Ya no se ofrece; los planes anteriores lo conservan | P2 | OK |
| ODO-16 | F | Asignar varios tratamientos y aplicar descuentos | Subtotal, descuentos y total se calculan bien | P1 | OK |
| ODO-17 | N | Descuento mayor que el precio | El total de esa línea no queda negativo | P1 | OK |
| ODO-18 | F | Eliminar un tratamiento del presupuesto | Se recalcula el total | P1 | OK |
| ODO-19 | F | Guardar como propuesta | El plan queda PROPUESTO y no genera deuda | P1 | OK |
| ODO-20 | I | Aprobar y cargar a cuenta | El plan queda APROBADO y su total aparece como deuda en Cobranzas | P1 | OK |
| ODO-21 | F | Dar de alta un tratamiento desde el plan | Queda completado y la cara se pinta de azul | P1 | OK |
| ODO-22 | I | Finalizar una cita con un tratamiento asignado | La pieza se actualiza en el odontograma de evolución | P1 | OK |
| ODO-23 | F | Realizar una extracción | La pieza queda como extraída y sin patologías pendientes | P1 | OK |
| ODO-24 | F | Realizar una endodoncia, una corona y un implante | La pieza refleja cada resultado | P2 | OK |
| ODO-25 | F | Comparar el odontograma inicial tras realizar tratamientos | El inicial no cambia; los cambios van al de evolución | P1 | OK |
| ODO-26 | F | Pulsar «Ver Ambos Espacios» | Muestra el estado de ingreso y los tratamientos a realizar | P3 | OK |
| ODO-27 | F | Cambiar de paciente | Se carga el odontograma correcto, sin mezclar datos | P1 | OK |
| ODO-28 | S | Doctor intenta registrar a nombre de otro doctor | Se rechaza | P2 | OK |
| ODO-29 | S | Asistente abre el odontograma | Solo lectura: [API] las modificaciones responden 403 | P1 | OK |
| ODO-30 | S | Recepción intenta abrirlo | No aparece en el menú y la ruta lo devuelve al Panel | P2 | OK |
| ODO-31 | V | Medir con pantallas de 1280, 1366, 1536, 1920 y 2560 px | Los 32 dientes caben y ocupan casi todo el ancho | P2 | OK |
| ODO-32 | V | Seleccionar un diente en cada ancho | No provoca desbordes | P3 | OK |
| ODO-33 | V | Abrir en celular | Se desplaza dentro de su recuadro, no la página | P3 | OK |
| ODO-34 | V | Revisar los colores en modo claro y oscuro | Los estados se distinguen en ambos | P2 | OK |
| ODO-35 | N | [API] Registrar `pieza_fdi` inexistente, como 99 | Se rechaza: solo valen las piezas de la numeración FDI | P2 | OK |
| ODO-36 | V | Revisar los botones de estado | Dicen «Diagnóstico y evaluación inicial» y «Alta clínica / Control posterior», con tildes | P3 | OK |

## 8. Planes y catálogo de tratamientos

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| TRA-01 | F | Administrador crea un tratamiento | Aparece en el catálogo y se puede asignar | P1 | OK |
| TRA-02 | N | Código repetido | «El código de tratamiento ya existe» | P1 | OK |
| TRA-03 | N | Precio negativo o duración 0 | Se rechaza | P1 | OK |
| TRA-04 | N | Nombre solo con espacios | Se rechaza | P2 | OK |
| TRA-05 | N | Precio gigante, como 100000000000000 | Mensaje claro, sin error interno | P2 | OK |
| TRA-06 | F | Editar un precio | Queda en auditoría con el valor anterior y el nuevo | P1 | OK |
| TRA-07 | I | Cambiar un precio con planes ya creados | Los planes existentes conservan su costo acordado | P1 | OK |
| TRA-08 | F | Eliminar un tratamiento sin uso | Se elimina | P2 | OK |
| TRA-09 | F | Eliminar uno usado en planes o citas | Se desactiva, y la historia conserva nombre y precio | P1 | OK |
| TRA-10 | F | Reactivar un tratamiento desactivado | Se puede volver a asignar | P2 | OK |
| TRA-11 | F | Filtrar por categoría y buscar | Muestra lo correcto | P3 | OK |
| TRA-12 | S | Otro rol, incluso con todos los permisos, intenta administrar el catálogo | No lo ve; [API] responde 403 | P1 | OK |
| TRA-13 | S | Doctor consulta tratamientos para asignarlos | Sí puede verlos | P2 | OK |
| TRA-14 | F | Crear un plan desde el odontograma como doctor | Queda a nombre de ese doctor | P1 | OK |
| TRA-15 | S | Doctor intenta reasignar un plan a otro doctor | Solo los administradores pueden hacerlo | P2 | OK |
| TRA-16 | F | Editar un ítem del plan: precio y descuento | El total del plan se recalcula | P1 | OK |
| TRA-17 | I | Eliminar un ítem de un plan ya aprobado | El total y el saldo se actualizan | P1 | OK |
| TRA-18 | N | [API] Ítem con costo, precio o descuento negativo | Se rechaza | P1 | OK |
| TRA-19 | N | Bajar el total de un plan por debajo de lo pagado, por cualquier vía | Se rechaza e indica cuánto está pagado | P1 | OK |
| TRA-20 | F | Cancelar un plan, con y sin pagos | Con pagos se rechaza hasta anularlos; sin pagos deja de generar deuda | P2 | OK |
| TRA-21 | I | Marcar un ítem como próxima sesión | Queda identificado para la siguiente cita | P2 | OK |

## 9. Agenda: matriz de sillones

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| AGE-01 | F | Abrir la matriz | Una columna por sillón activo, con horas de 07:00 a 22:00 | P1 | OK |
| AGE-02 | F | Crear una cita haciendo clic en un espacio libre | Aparece en ese sillón y a esa hora | P1 | OK |
| AGE-03 | F | Crear una cita con «Nueva Cita» | Se guarda con los datos elegidos | P1 | OK |
| AGE-04 | F | Cita de varios bloques, como 09:00 a 10:30 | Ocupa los bloques correctos | P1 | OK |
| AGE-05 | N | Hora de fin igual o anterior a la de inicio | «La hora de fin de la cita debe ser posterior a la hora de inicio» | P1 | OK |
| AGE-06 | N | Mismo doctor, horario solapado, otro sillón | «El doctor ya tiene una cita…» | P1 | OK |
| AGE-07 | N | Mismo sillón, horario solapado, otro doctor | «El Box N ya está ocupado…» | P1 | OK |
| AGE-08 | F | Cita que termina justo cuando empieza otra | Se permite: no se solapan | P1 | OK |
| AGE-09 | F | Otro doctor en otro sillón a la misma hora | Se permite | P1 | OK |
| AGE-10 | S | Dos personas guardan a la vez la misma cita, en dos equipos | Solo una se crea; la otra recibe el aviso, sin error interno | P1 | OK |
| AGE-11 | N | Doctor inexistente o paciente inexistente ([API]) | Responde 404; no se reasigna a otro doctor | P1 | OK |
| AGE-12 | N | Sillón desactivado o inexistente ([API]) | «No existe o está desactivado» | P1 | OK |
| AGE-13 | F | Editar una cita: cambiar hora, sillón y motivo | Se mueve en la matriz | P1 | OK |
| AGE-14 | N | Mover una cita a un horario ocupado | Se rechaza y sigue en su lugar original | P1 | OK |
| AGE-15 | F | Cancelar una cita | Pide confirmar, sigue visible con su color propio y tachada | P1 | OK |
| AGE-16 | F | Crear otra cita en el espacio de una cancelada | Se permite: libera el horario | P1 | OK |
| AGE-17 | F | Marcar «No asistió» | Queda como constancia y libera el horario | P1 | OK |
| AGE-18 | N | Cancelar una cita ya atendida | «No se puede cancelar una cita que ya fue atendida» | P1 | OK |
| AGE-19 | F | Avanzar una cita: programada, recepción, sillón, finalizada | Cada paso cambia de estado y registra la hora real | P1 | OK |
| AGE-20 | I | Finalizar una cita | Se crea la evolución y la cuenta de cobro, y se actualiza el odontograma | P1 | OK |
| AGE-21 | I | Finalizar con varios tratamientos seleccionados | Todos quedan realizados y en la misma cuenta | P1 | OK |
| AGE-22 | I | Finalizar una cita sin plan | La evolución usa el motivo; la cuenta usa el motivo o el tratamiento | P1 | OK |
| AGE-23 | N | La misma cita, finalizada dos veces ([API]) | La segunda se rechaza; no duplica evolución ni cuenta | P1 | OK |
| AGE-24 | F | Calcular la duración en sillón | Se registran los minutos reales y aparecen en Reportes | P2 | OK |
| AGE-25 | F | Navegar: día anterior, día siguiente y Hoy | Muestra el día correcto | P2 | OK |
| AGE-26 | F | Filtrar por especialidad y por doctor | Muestra solo lo correspondiente | P2 | OK |
| AGE-27 | S | Doctor edita o finaliza una cita de otro doctor | «Solo puedes modificar tus propias citas» | P1 | OK |
| AGE-28 | S | Doctor agenda para otro doctor | Se rechaza | P1 | OK |
| AGE-29 | F | Asistente y recepción modifican citas de cualquier doctor | Se permite | P1 | OK |
| AGE-30 | S | Asistente intenta crear una cita | No tiene ese permiso; [API] responde 403 | P2 | OK |
| AGE-31 | I | Agregar un cuarto sillón | La matriz muestra una columna más y el texto indica la cantidad real | P2 | OK |
| AGE-32 | V | Medir con los cinco anchos de pantalla | Llena el ancho, con columnas iguales y sin desbordes | P2 | OK |
| AGE-33 | V | Con 6 sillones o más | Se desplaza dentro de la tabla, sin romper la página | P3 | OK |
| AGE-34 | N | [API] Cambiar de cualquier modo una cita FINALIZADA | «Esta cita ya fue atendida y no se puede modificar» | P1 | OK |
| AGE-35 | N | [API] Reactivar una cita cancelada sobre un horario ya ocupado | Se rechaza por solape | P1 | OK |
| AGE-36 | F | [API] Finalizar directamente una cita PROGRAMADA | Se permite. Crea evolución y cuenta, y no afecta el promedio de minutos | P2 | OK |
| AGE-37 | F | Cita que cruza la medianoche | Cuenta el día en que empieza, en la agenda y en Reportes | P3 | OK |
| AGE-38 | F | Crear una cita en una fecha pasada | Decidir si se permite registrar citas históricas | P3 | DECIDIR |

## 10. Agenda: vista mensual

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| CAL-01 | F | Abrir la vista mensual | Muestra el mes correcto, con la semana empezando el lunes | P1 | OK |
| CAL-02 | F | Comprobar meses de 28, 30 y 31 días | Todos los días están en su lugar | P2 | OK |
| CAL-03 | F | Cambiar de mes y de año; volver con Hoy | Muestra el período correcto | P2 | OK |
| CAL-04 | F | El día actual | Está resaltado | P3 | OK |
| CAL-05 | F | Doble clic en un día | Abre una cita nueva con esa fecha | P2 | OK |
| CAL-06 | F | Clic en una cita | Abre su edición | P2 | OK |
| CAL-07 | F | Día con más de 3 citas | Muestra 3 y un indicador con la cantidad restante | P3 | OK |
| CAL-08 | F | Cita cancelada | Se ve tachada, con su color | P2 | OK |
| CAL-09 | F | Crear en la matriz y mirar la vista mensual | Coincide | P1 | OK |
| CAL-10 | F | Cita a las 23:30 | Aparece en el día local correcto | P1 | OK |
| CAL-11 | V | Medir con los cinco anchos de pantalla | Llena el ancho, sin desbordes | P2 | OK |
| CAL-12 | V | Abrir en celular | Se puede usar y la página no se desborda | P3 | OK |

## 11. Evolución clínica

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| EVO-01 | I | Finalizar una cita | Se crea una evolución con la fecha de la cita, no con la fecha actual | P1 | OK |
| EVO-02 | F | Revisar una evolución automática con diagnóstico | Dice «Diagnóstico (tomado del odontograma)» y muestra la patología | P1 | OK |
| EVO-03 | F | Evolución automática sin hallazgos | «Sin diagnóstico registrado en el odontograma» | P2 | OK |
| EVO-04 | F | Revisar el procedimiento | Lista los tratamientos y piezas de la cita | P1 | OK |
| EVO-05 | F | Evolución manual | Pide motivo, diagnóstico y procedimiento, y se muestra «Registrada manualmente» | P1 | OK |
| EVO-06 | N | Guardar una evolución manual sin diagnóstico | No permite guardar | P1 | OK |
| EVO-07 | F | Revisar el formulario antes de guardar | Avisa que no se podrá modificar | P2 | OK |
| EVO-08 | S | [API] Editar una evolución automática o manual | Responde 405, también para el administrador | P1 | OK |
| EVO-09 | S | [API] Eliminar una evolución | Responde 405 | P1 | OK |
| EVO-10 | S | Revisar la lista de permisos | Ya no existe `HISTORIA_CLINICA_UPDATE` | P2 | OK |
| EVO-11 | F | Doctor agrega una observación | Se muestra con autor, rol y fecha | P1 | OK |
| EVO-12 | F | Asistente agrega una observación | Se permite | P1 | OK |
| EVO-13 | N | Observación vacía o de más de 2.000 caracteres | No se guarda | P2 | OK |
| EVO-14 | S | [API] Editar o borrar una observación | No existe esa acción | P1 | OK |
| EVO-15 | S | Recepción intenta abrir Evolución | No aparece en el menú; [API] responde 403 | P1 | OK |
| EVO-16 | S | Asistente intenta crear una evolución | No tiene ese permiso; [API] responde 403 | P1 | OK |
| EVO-17 | N | Dos evoluciones para la misma cita | «Esta cita ya tiene una evolución registrada» | P1 | OK |
| EVO-18 | F | Doctor registró una nota antes de finalizar la cita | Se conserva la suya y no se crea otra | P1 | OK |
| EVO-19 | I | Vincular una evolución con «Tratamiento realizado hoy» | El ítem queda completado y se refleja en el odontograma | P1 | OK |
| EVO-20 | I | Marcar «próxima sesión» | El ítem queda como próxima sesión | P2 | OK |
| EVO-21 | F | Fecha y hora predeterminadas a las 22:30 | Usa la fecha y hora locales, no UTC | P1 | OK |
| EVO-22 | F | Guardar con la hora indicada y volver a abrirla | Conserva la misma hora, sin desfase | P1 | OK |
| EVO-23 | F | Registrar receta e indicaciones | Se muestran y se pueden imprimir | P2 | OK |
| EVO-24 | F | Ver el historial con varias evoluciones | Ordenado de la más reciente a la más antigua | P2 | OK |
| EVO-25 | S | Texto con `<script>` en notas y observaciones | Se muestra como texto | P1 | OK |

## 12. Radiografías

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| RAD-01 | F | Registrar un estudio con la URL de una imagen | Aparece y la imagen se ve | P1 | OK |
| RAD-02 | F | Registrar cada tipo de estudio | Todos se guardan con su tipo | P2 | OK |
| RAD-03 | N | Sin URL o sin tipo | No permite guardar | P2 | OK |
| RAD-04 | S | URL que empieza con `javascript:` | No se ejecuta; idealmente se rechaza | P1 | OK |
| RAD-05 | N | URL inválida o imagen eliminada | Se muestra un error de imagen, sin romper la pantalla | P2 | OK |
| RAD-06 | F | Asociar a una pieza FDI y filtrar por ella | Muestra solo esa pieza | P2 | OK |
| RAD-07 | F | Vacío en el filtro | Muestra todas | P3 | OK |
| RAD-08 | F | Abrir el visor | Muestra la imagen, la fecha y el informe | P2 | OK |
| RAD-09 | F | Fecha predeterminada a las 22:30 | Usa la fecha local, no UTC | P2 | OK |
| RAD-10 | F | Eliminar como administrador | Desaparece y queda en auditoría | P1 | OK |
| RAD-11 | S | Doctor o asistente intenta eliminar | No tiene ese permiso; [API] responde 403 | P1 | OK |
| RAD-12 | S | Recepción intenta abrir | No aparece en el menú; [API] responde 403 | P1 | OK |
| RAD-13 | S | Abrir un estudio y revisar la auditoría | Queda un registro `VIEW` | P2 | OK |
| RAD-14 | F | Cambiar de paciente | No muestra imágenes del anterior | P1 | OK |
| RAD-15 | O | Restaurar una copia y abrir una radiografía | El registro vuelve, pero la imagen depende de que su enlace siga disponible. Confirmar dónde se guardan las imágenes | P1 | OK |
| RAD-16 | V | Revisar la tarjeta de una radiografía | Muestra el título escrito al registrarla | P3 | OK |

## 13. Prótesis y laboratorio

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| PRO-01 | F | Crear una orden con todos los datos | Aparece en la lista con paciente, doctor y laboratorio | P1 | OK |
| PRO-02 | N | Sin paciente, doctor, laboratorio o tipo | No permite guardar | P2 | OK |
| PRO-03 | F | Sin fecha de entrega | Se propone en 7 días | P3 | OK |
| PRO-04 | F | Fecha de envío predeterminada a las 22:30 | Usa la fecha local, no UTC | P2 | OK |
| PRO-05 | F | Recorrer los estados de la orden | Cada cambio se guarda | P1 | OK |
| PRO-06 | F | Marcar como recibida | Registra la fecha real de recepción | P2 | OK |
| PRO-07 | F | Filtrar por estado | Muestra solo ese estado | P3 | OK |
| PRO-08 | S | Doctor asigna una orden a otro doctor | Se rechaza | P2 | OK |
| PRO-09 | S | Doctor reasigna una orden existente | Solo los administradores | P2 | OK |
| PRO-10 | S | Asistente intenta crear o actualizar | [API] Responde 403 | P1 | OK |
| PRO-11 | F | Recepción actualiza el estado | Se permite | P1 | OK |
| PRO-12 | S | Recepción intenta crear una orden | [API] Responde 403 | P2 | OK |
| PRO-13 | N | [API] Costo negativo | Se rechaza | P2 | OK |
| PRO-14 | N | Fecha de entrega anterior a la de envío | Se rechaza | P3 | OK |
| PRO-15 | F | Moneda en costo y etiquetas | Usa el símbolo configurado | P2 | OK |
| PRO-16 | I | Pagar al laboratorio como egreso | La caja se descuenta. Decidir si debe quedar vinculado a la orden | P3 | DECIDIR |
| PRO-17 | V | Revisar la lista de órdenes | Muestra el color y las piezas de cada orden | P2 | OK |

## 14. Caja operativa

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| CAJ-01 | F | Primer ingreso del día, sin caja, con permiso | El sistema exige abrir la caja con un fondo | P1 | OK |
| CAJ-02 | F | Sin caja abierta y sin permiso para abrirla | Se muestra el bloqueo, sin opción de abrir ni montos | P1 | OK |
| CAJ-03 | F | Abrir la caja con un fondo | La gaveta muestra ese fondo y desaparece el bloqueo | P1 | OK |
| CAJ-04 | N | Fondo negativo | Se rechaza | P1 | OK |
| CAJ-05 | N | Abrir una segunda caja | «Ya existe una sesión de caja abierta» | P1 | OK |
| CAJ-06 | S | Dos personas abren la caja a la vez, en dos equipos | Solo una queda abierta | P1 | OK |
| CAJ-07 | I | Cobro en efectivo | La gaveta sube ese monto | P1 | OK |
| CAJ-08 | I | Cobro con tarjeta o transferencia | La gaveta no cambia, y aparece en el total por método | P1 | OK |
| CAJ-09 | F | Egreso en cada categoría | Baja la gaveta y aparece en movimientos | P1 | OK |
| CAJ-10 | N | Egreso mayor que el efectivo disponible | «No hay efectivo suficiente…»; la gaveta no cambia | P1 | OK |
| CAJ-11 | N | Egreso de 0, negativo o con 3 decimales | Se rechaza | P1 | OK |
| CAJ-12 | N | Egreso sin motivo | No permite guardar | P2 | OK |
| CAJ-13 | F | Retirar hasta el último centavo | Se permite y la gaveta queda en 0 | P2 | OK |
| CAJ-14 | F | Comprobar la fórmula | Fondo + ingresos − egresos = efectivo en gaveta | P1 | OK |
| CAJ-15 | F | Cierre con el conteo exacto | Diferencia 0; la caja queda cerrada | P1 | OK |
| CAJ-16 | F | Cierre con sobrante y con faltante | Registra la diferencia con su signo | P1 | OK |
| CAJ-17 | N | Cierre sin indicar el conteo | «Debes indicar el efectivo contado» | P1 | OK |
| CAJ-18 | N | Conteo negativo | Se rechaza | P2 | OK |
| CAJ-19 | F | Caja abierta de un día anterior | Bloquea hasta hacer el arqueo y cierre pendiente | P1 | OK |
| CAJ-20 | N | Abrir una nueva caja sin cerrar la del día anterior | Se rechaza con la fecha pendiente | P1 | OK |
| CAJ-21 | F | Abrir, cerrar y volver a abrir el mismo día | Funciona, con movimientos separados | P2 | OK |
| CAJ-22 | N | Cobro en efectivo con la caja cerrada | Se rechaza | P1 | OK |
| CAJ-23 | F | Cobro con transferencia con la caja cerrada | Decidir si la barrera debe impedirlo; por API se permite | P3 | DECIDIR |
| CAJ-24 | S | Sin `CAJA_READ` | [API] La consulta del estado no incluye montos | P1 | OK |
| CAJ-25 | S | Doctor o asistente intenta abrir, cerrar o registrar egresos | [API] Responde 403 | P1 | OK |
| CAJ-26 | F | Cambio de día a medianoche con la caja abierta | Pasa a «Caja anterior sin cerrar» | P1 | OK |
| CAJ-27 | F | Barra superior | Coincide con el efectivo en gaveta y se actualiza | P2 | OK |
| CAJ-28 | V | Sin egresos | Muestra el total sin signo negativo | P3 | OK |
| CAJ-29 | F | Auditoría tras abrir, cerrar y registrar un egreso | Hay un registro por cada uno | P1 | OK |
| CAJ-30 | F | Registrar cobros y egresos y revisar «Movimientos del Turno» | Aparecen con hora, medio, comprobante y monto; los anulados no | P1 | OK |

## 15. Cobranzas y pagos

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| COB-01 | F | Abono a un plan aprobado | Baja el saldo pendiente | P1 | OK |
| COB-02 | N | Abono mayor que el saldo | «Supera el saldo pendiente» | P1 | OK |
| COB-03 | F | Abono exacto al saldo | El saldo queda en 0 | P1 | OK |
| COB-04 | N | Cobrar a un paciente con saldo 0 | «No tiene saldo pendiente» | P1 | OK |
| COB-05 | N | Abonar a un plan solo propuesto | «Solo se puede cobrar sobre un plan de tratamiento aprobado» | P1 | OK |
| COB-06 | N | Plan de otro paciente ([API]) | «El plan no pertenece a este paciente» | P1 | OK |
| COB-07 | F | Consulta directa sin plan | Se registra sin afectar la deuda de planes | P1 | OK |
| COB-08 | N | Consulta directa sin concepto | «Indica el concepto» | P1 | OK |
| COB-09 | N | Monto 0, negativo, con 3 decimales o gigante | Se rechaza con mensaje claro | P1 | OK |
| COB-10 | F | Cobrar con cada medio de pago | Se guarda el medio real | P1 | OK |
| COB-11 | F | Cobro con comprobante | Aparece en el historial | P2 | OK |
| COB-12 | S | Doble clic en Confirmar | Se registra un solo pago | P1 | OK |
| COB-13 | S | Dos personas cobran a la vez el saldo restante | Solo una lo logra; la deuda nunca queda negativa | P1 | OK |
| COB-14 | I | Cobro con doctor de comisión | Se suma a su comisión con el porcentaje vigente | P1 | OK |
| COB-15 | N | Doctor de comisión inexistente ([API]) | Responde 404 | P1 | OK |
| COB-16 | F | Buscar un paciente y ver su historial | Muestra solo sus pagos | P1 | OK |
| COB-17 | S | Doctor o asistente intenta abrir Cobranzas | No aparece; [API] responde 403 | P1 | OK |
| COB-18 | F | Totales de la pantalla | Presupuestado − abonado = pendiente | P1 | OK |

### Anulación de pagos

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| ANU-01 | F | Anular un pago en efectivo de la caja abierta | Sale de la gaveta y el saldo vuelve a subir | P1 | OK |
| ANU-02 | F | Anular un pago con tarjeta | La gaveta no cambia y el saldo sube | P1 | OK |
| ANU-03 | F | Anular un efectivo de una caja cerrada, con caja abierta y efectivo suficiente | Se devuelve desde la caja abierta; el arqueo anterior no cambia | P1 | OK |
| ANU-04 | N | Anular efectivo de una caja cerrada sin caja abierta | Pide abrir la caja | P1 | OK |
| ANU-05 | N | Anular efectivo de una caja cerrada sin suficiente efectivo | «No hay efectivo suficiente…» | P1 | OK |
| ANU-06 | N | Sin motivo | Se rechaza | P1 | OK |
| ANU-07 | N | Anular dos veces | «Este pago ya fue anulado» | P1 | OK |
| ANU-08 | F | Revisar el historial | El pago sigue visible, marcado y con su motivo | P1 | OK |
| ANU-09 | I | Revisar Reportes tras anular | El ingreso deja de contar; la devolución no cuenta como egreso | P1 | OK |
| ANU-10 | I | Revisar la comisión del doctor | Resta justo lo que generó ese cobro | P1 | OK |
| ANU-11 | I | Anular un pago de una cuenta de cita | Se anulan todos sus pagos y la cuenta vuelve a pendiente | P1 | OK |
| ANU-12 | S | Recepción intenta anular | No ve el botón; [API] responde 403 | P1 | OK |
| ANU-13 | S | Dar `CAJA_ANULAR_PAGOS` a un rol | Ese rol ya puede anular | P2 | OK |
| ANU-14 | F | Revisar la auditoría | Registra quién, cuándo y por qué | P1 | OK |
| ANU-15 | I | Tratamientos tras anular | Siguen como realizados | P2 | OK |

### Cuenta de cobro de una cita

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| CCI-01 | I | Finalizar una cita con tratamientos | Aparece en «Cobros de citas pendientes» con sus líneas | P1 | OK |
| CCI-02 | F | Finalizar una cita sin plan, con tratamiento del catálogo | La cuenta usa el precio base | P1 | OK |
| CCI-03 | F | Editar conceptos y montos, y guardar | Sigue pendiente, con los cambios | P1 | OK |
| CCI-04 | F | Agregar una línea manual | Se suma al total | P1 | OK |
| CCI-05 | N | Línea con monto negativo, con 3 decimales o sin concepto | Se rechaza | P1 | OK |
| CCI-06 | F | Plan con abono previo | La línea propone solo el saldo pendiente y muestra el costo | P1 | OK |
| CCI-07 | F | Mismo tratamiento en una segunda cita | No se vuelve a cobrar | P1 | OK |
| CCI-08 | F | Confirmar el pago en efectivo | La cuenta queda pagada y sube la gaveta | P1 | OK |
| CCI-09 | F | Confirmar con tarjeta | Registra el método real y no cambia la gaveta | P1 | OK |
| CCI-10 | I | Líneas de plan y líneas directas en la misma cuenta | Las de plan abonan al plan; las otras son cobro directo | P1 | OK |
| CCI-11 | N | Confirmar una cuenta con total 0 | Pide cerrarla sin pago | P1 | OK |
| CCI-12 | N | Monto mayor que el saldo del plan | Se rechaza por el límite de saldo | P1 | OK |
| CCI-13 | N | Confirmar en efectivo sin caja abierta | Se rechaza | P1 | OK |
| CCI-14 | F | Cerrar sin pago con motivo | Queda cerrada y el motivo se conserva | P1 | OK |
| CCI-15 | N | Cerrar sin pago sin motivo | «Indica el motivo» | P1 | OK |
| CCI-16 | N | Editar o confirmar una cuenta ya cerrada | «Ya fue cerrado» | P1 | OK |
| CCI-17 | S | Dos personas confirman la misma cuenta a la vez | Solo se paga una vez | P1 | OK |
| CCI-18 | F | Revisar la auditoría | Registra creación, edición y cierre | P2 | OK |

## 16. Nómina y comisiones

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| NOM-01 | F | Abrir Nómina como administrador | Lista a todo el personal activo | P1 | OK |
| NOM-02 | F | Registrar y editar un contrato | Se guarda y se refleja en los cálculos | P1 | OK |
| NOM-03 | N | Comisión mayor a 100 %, o salario negativo | Se rechaza | P1 | OK |
| NOM-04 | F | Cobro de 1.000 con doctor al 40 % | Comisión generada: 400 | P1 | OK |
| NOM-05 | I | Cambiar el porcentaje a 10 % y cobrar otros 1.000 | Comisión total: 500; el cobro anterior conserva su 40 % | P1 | OK |
| NOM-06 | I | Contrato creado después de un cobro | Ese cobro no genera comisión | P1 | OK |
| NOM-07 | F | Liquidar una parte del saldo | El saldo baja y aparece en el historial | P1 | OK |
| NOM-08 | N | Liquidar más que el saldo | «No puede superar el saldo», mostrado dentro del formulario | P1 | OK |
| NOM-09 | F | Adelanto a un doctor | Baja el saldo disponible | P1 | OK |
| NOM-10 | I | Anular un cobro ya liquidado | «Pagado de más» y aviso; no permite liquidar | P1 | OK |
| NOM-11 | I | Cobros nuevos tras un sobrepago | Compensan primero lo pagado de más | P1 | OK |
| NOM-12 | F | Adelanto a personal con sueldo fijo | Sale de la caja y aparece como pendiente | P1 | OK |
| NOM-13 | F | Pagar sueldo con adelanto pendiente | Propone el descuento y el neto correcto | P1 | OK |
| NOM-14 | N | Descontar más que los adelantos pendientes | Se rechaza | P1 | OK |
| NOM-15 | N | [API] Neto distinto de sueldo menos descuento | Se rechaza | P1 | OK |
| NOM-16 | F | Sueldo cubierto por completo con adelantos | Se registra sin mover la gaveta | P1 | OK |
| NOM-17 | F | Pagar quincena | Propone la mitad del sueldo | P2 | OK |
| NOM-18 | F | Contrato mixto: adelanto descontado del sueldo | Deja de restar de las comisiones | P1 | OK |
| NOM-19 | F | Bono | No afecta comisión ni adelantos | P2 | OK |
| NOM-20 | N | Pago en efectivo mayor que la gaveta | «No hay efectivo suficiente» | P1 | OK |
| NOM-21 | N | Pago en efectivo sin caja abierta | Se rechaza | P1 | OK |
| NOM-22 | F | Pago sin descontar de caja | La gaveta no cambia | P1 | OK |
| NOM-23 | N | Monto 0, salvo sueldo cubierto con adelantos | Se rechaza | P2 | OK |
| NOM-24 | S | Doctor abre Nómina | Solo se ve a sí mismo, sin botones de pago ni contrato | P1 | OK |
| NOM-25 | S | [API] Doctor consulta la liquidación de otra persona | Responde 403 | P1 | OK |
| NOM-26 | S | Asistente o recepción abre Nómina | No aparece en el menú | P1 | OK |
| NOM-27 | S | [API] Otro rol intenta crear o editar un contrato | Responde 403 | P1 | OK |
| NOM-28 | V | Valores en cero | No muestra `-$0,00` | P3 | OK |
| NOM-29 | N | [API] `metodo_pago` con un texto inventado | Se rechaza | P2 | OK |
| NOM-30 | F | Empleado desactivado con saldo | Decidir: hoy desaparece de la lista aunque tenga saldo por pagar | P2 | DECIDIR |

## 17. Control de asistencia

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| ASI-01 | F | Sin marcajes hoy | «Fuera de turno»; solo Entrada activo | P1 | OK |
| ASI-02 | F | Marcar Entrada | «En turno»; solo Descanso y Salida activos | P1 | OK |
| ASI-03 | F | Marcar Descanso | «En descanso»; solo Fin Descanso activo | P1 | OK |
| ASI-04 | F | Marcar Fin Descanso | Vuelve a En turno; Descanso y Salida activos | P1 | OK |
| ASI-05 | F | Marcar Salida | «Turno cerrado»; solo Entrada activo | P1 | OK |
| ASI-06 | F | Nueva entrada el mismo día | Permite un segundo turno | P2 | OK |
| ASI-07 | F | Pasar el cursor por un botón bloqueado | Explica el motivo | P2 | OK |
| ASI-08 | S | [API] Marcar un evento no permitido | Responde 409 y no se registra | P1 | OK |
| ASI-09 | S | Doble clic rápido en Entrada | Se registra una sola | P1 | OK |
| ASI-10 | F | Marcar en otra pestaña y usar un botón desactualizado | Se rechaza con explicación y los botones se corrigen | P2 | OK |
| ASI-11 | F | Acceso rápido «Fichar Turno» | Solo ofrece lo permitido y actualiza la pantalla | P1 | OK |
| ASI-12 | F | Una persona marca | No afecta el turno de otra | P1 | OK |
| ASI-13 | F | Olvidar la salida y volver al día siguiente | Puede marcar Entrada y ve un aviso de jornada sin salida | P1 | OK |
| ASI-14 | F | Bitácora | Muestra hora real, persona, rol, evento e IP | P1 | OK |
| ASI-15 | F | Filtrar por día | Solo ese día | P1 | OK |
| ASI-16 | F | Fecha predeterminada a las 22:30 | El día local, no el de UTC | P1 | OK |
| ASI-17 | S | Empleado sin permiso de supervisión | Solo ve sus marcajes | P1 | OK |
| ASI-18 | F | Marcar con observación | Se muestra en la bitácora | P3 | OK |
| ASI-19 | F | IP desde otro equipo de la red | Muestra la IP real de ese equipo, sobre todo con HTTPS | P2 | OK |

### Correcciones del administrador

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| COR-01 | F | Lista de jornadas sin salida | Muestra persona, fecha y último marcaje | P1 | OK |
| COR-02 | F | Pulsar Corregir en la lista | Prellena persona, día y tipo; deja la hora vacía | P1 | OK |
| COR-03 | F | Guardar una salida olvidada | La jornada sale de la lista y el aviso desaparece | P1 | OK |
| COR-04 | F | Bitácora | Muestra «Corregido», con motivo y autor | P1 | OK |
| COR-05 | N | Sin motivo o sin hora | No permite guardar | P1 | OK |
| COR-06 | N | Fecha u hora futura | Se rechaza | P1 | OK |
| COR-07 | N | Orden imposible, como entrada tras entrada | Explica el motivo dentro del formulario | P1 | OK |
| COR-08 | F | Entrada olvidada hoy | La persona queda En turno | P1 | OK |
| COR-09 | F | Descanso completo con inicio y fin en un turno cerrado | Se agregan ambos marcajes | P1 | OK |
| COR-10 | N | Descanso sin fin en un turno cerrado | Se rechaza y explica el motivo | P1 | OK |
| COR-11 | N | Fin anterior al inicio, o que abarque la salida | Se rechaza | P1 | OK |
| COR-12 | F | Anular un marcaje hecho por error | Deja de contar y sigue visible, tachado y con motivo | P1 | OK |
| COR-13 | N | Anular dos veces | «Ya está anulado» | P2 | OK |
| COR-14 | N | Anular un marcaje del que dependen otros | Explica que se deben anular primero los posteriores | P1 | OK |
| COR-15 | F | Corregir una hora: anular y agregar | Queda el marcaje correcto y el anterior visible | P1 | OK |
| COR-16 | S | Otros roles | No ven Corregir, Anular ni la lista; [API] responde 403 | P1 | OK |
| COR-17 | F | Auditoría | Registra correcciones y anulaciones con su motivo | P1 | OK |
| COR-18 | F | Marcajes originales | Nunca cambian ni se borran | P1 | OK |

## 18. Panel Principal

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| PAN-01 | F | Saludo | Nombre y rol correctos | P3 | OK |
| PAN-02 | F | Caja en gaveta | Coincide con Caja | P1 | OK |
| PAN-03 | F | Citas para hoy | Número correcto y cuántas están en sillón | P1 | OK |
| PAN-04 | F | Hora del equipo a las 22:30 | Sigue mostrando las citas del día local | P1 | OK |
| PAN-05 | I | Ingresos, egresos y margen del mes | Solo del mes actual; coinciden con Reportes en «Mes actual» | P1 | OK |
| PAN-06 | F | Avanzar una cita desde el Panel | Cambia de estado | P2 | OK |
| PAN-07 | S | Doctor en una cita ajena | No ve el botón para avanzarla | P1 | OK |
| PAN-08 | S | Roles sin caja ni reportes | No ven esos montos | P1 | OK |
| PAN-09 | F | Enlaces de módulos | Abren la pantalla correcta, y solo aparecen los permitidos | P2 | OK |
| PAN-10 | V | Sin referencias internas | No aparece ningún código de historia | P2 | OK |

## 19. Inteligencia de Negocio

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| REP-01 | F | Abrir la pantalla | Inicia en Mes actual y muestra el rango | P1 | OK |
| REP-02 | F | Probar cada período: Hoy, Esta semana, Semana pasada, Mes actual, Mes pasado, Últimos 30 días, Este año y Todo | Indicadores, gráficos y tablas cambian juntos | P1 | OK |
| REP-03 | F | Semana | Va de lunes a hoy; la pasada, de lunes a domingo | P2 | OK |
| REP-04 | F | Rango personalizado | Respeta ambos días, incluidos | P1 | OK |
| REP-05 | N | Fecha inicial posterior a la final | Avisa y mantiene el último rango válido | P2 | OK |
| REP-06 | F | Período sin datos | Muestra ceros y un mensaje, sin tablas | P2 | OK |
| REP-07 | I | Cita finalizada en un día anterior | El tratamiento cuenta el día de la cita | P1 | OK |
| REP-08 | F | Tratamientos más demandados | El gráfico y la tabla coinciden, de mayor a menor | P1 | OK |
| REP-09 | F | Productividad médica | Citas atendidas, minutos y ausentismo correctos | P1 | OK |
| REP-10 | F | Ausentismo | No asistió ÷ total de citas | P2 | OK |
| REP-11 | I | Ingresos | Suman todos los medios, sin pagos anulados | P1 | OK |
| REP-12 | I | Egresos | Incluye nómina y gastos; excluye devoluciones por anulación | P1 | OK |
| REP-13 | F | Margen | Ingresos − egresos | P1 | OK |
| REP-14 | F | Pago a las 23:30 del último día del mes | Cuenta en ese mes | P1 | OK |
| REP-15 | F | Cambiar el período rápidamente | Se queda con el último elegido | P2 | OK |
| REP-16 | F | Cambiar claro y oscuro | Los gráficos se ven bien en ambos | P2 | OK |
| REP-17 | S | Otros roles | No aparece; [API] responde 403, también en los gráficos | P1 | OK |
| REP-18 | F | Moneda | Usa el símbolo configurado | P2 | OK |
| REP-19 | V | Con 10 doctores y nombres largos | No se cortan los textos ni los valores | P3 | OK |

## 20. Auditoría

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| AUD-01 | F | Filtrar por tabla y por acción | Muestra lo correspondiente | P2 | OK |
| AUD-02 | F | Abrir el detalle de un cambio | Muestra datos anteriores y nuevos | P1 | OK |
| AUD-03 | F | Cada registro | Tiene usuario, fecha, acción y origen | P1 | OK |
| AUD-04 | I | Cambiar un precio, cobrar, anular y corregir un marcaje | Todo queda registrado | P1 | OK |
| AUD-05 | I | Cambiar moneda, nombre, logo y tema | Queda registrado | P2 | OK |
| AUD-06 | S | [API] Intentar modificar o borrar un registro | No existe esa acción | P1 | OK |
| AUD-07 | S | Otros roles | No aparece; [API] responde 403 | P1 | OK |
| AUD-08 | S | Buscar contraseñas o hashes en los registros | No aparecen | P1 | OK |
| AUD-09 | F | Revisar y usar el filtro de tablas | Incluye todas las tablas auditadas, y cada opción devuelve sus registros | P2 | OK |
| AUD-10 | F | Con muchos registros | La pantalla sigue respondiendo | P2 | OK |

## 21. Sillones

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| SIL-01 | F | Agregar un sillón con nombre | Aparece en la agenda | P1 | OK |
| SIL-02 | F | Agregar sin nombre | Se llama «Box» y su número | P3 | OK |
| SIL-03 | F | Editar nombre y especialidad | Se refleja en la agenda | P2 | OK |
| SIL-04 | N | Quitar un sillón con citas por atender | Explica cuántas tiene y qué hacer | P1 | OK |
| SIL-05 | F | Quitar un sillón con citas ya pasadas | Se desactiva y las citas conservan su sillón | P1 | OK |
| SIL-06 | F | Quitar un sillón sin citas | Se elimina | P2 | OK |
| SIL-07 | N | Quitar el último sillón activo | «Debe quedar al menos un sillón activo» | P1 | OK |
| SIL-08 | F | Reactivar un sillón | Vuelve a la agenda | P2 | OK |
| SIL-09 | F | Agregar después de eliminar un sillón intermedio | No reutiliza ese número. El más alto sí puede volver, porque un sillón solo se elimina si nunca tuvo citas | P2 | OK |
| SIL-10 | S | Otros roles | No aparece; [API] responde 403 | P1 | OK |
| SIL-11 | F | Día con citas en un sillón desactivado | La columna aparece con «Desactivado» | P2 | OK |

## 22. Configuración

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| CFG-01 | F | Cambiar el nombre de la clínica | Cambia al instante en menú y pestaña | P1 | OK |
| CFG-02 | F | Abrir el acceso sin sesión | Muestra el nombre y el logo nuevos | P1 | OK |
| CFG-03 | N | Nombre vacío o de más de 120 caracteres | No permite guardar | P2 | OK |
| CFG-04 | F | Nombre muy largo, cerca del límite | Se corta con elegancia en el menú | P3 | OK |
| CFG-05 | F | Subir un logo PNG, JPG y WEBP | Aparece en menú, acceso y pestaña | P1 | OK |
| CFG-06 | N | Archivo que no es imagen, con extensión `.png` | «PNG, JPG o WEBP» | P1 | OK |
| CFG-07 | S | Subir un SVG | Se rechaza | P1 | OK |
| CFG-08 | N | Logo de más de 1 MB | «No puede superar 1 MB» | P1 | OK |
| CFG-09 | F | Logo no cuadrado | Se ve sin deformarse | P3 | OK |
| CFG-10 | F | Quitar el logo | Vuelve el diente | P2 | OK |
| CFG-11 | O | Restaurar una copia | El logo y la configuración vuelven | P2 | OK |
| CFG-12 | F | Elegir tema por defecto Claro | Un equipo nuevo abre en Claro, también en el acceso | P1 | OK |
| CFG-13 | F | Elegir el tema con el botón de la barra | Se recuerda en ese equipo | P1 | OK |
| CFG-14 | F | Cambiar el valor por defecto con un tema ya elegido | La elección de esa persona se mantiene y la pantalla lo explica | P2 | OK |
| CFG-15 | F | Elegir cada moneda: Bs., $, US$, S/ y € | La vista previa y todas las pantallas cambian | P1 | OK |
| CFG-16 | F | Símbolo propio, como COP | Se aplica | P2 | OK |
| CFG-17 | N | Símbolo vacío, con números o de más de 8 caracteres | Se rechaza | P2 | OK |
| CFG-18 | I | Con otra moneda, provocar un error de saldo | El mensaje usa el símbolo elegido | P2 | OK |
| CFG-19 | F | Cambiar la moneda con pagos existentes | Solo cambia el símbolo: los montos siguen iguales | P1 | OK |
| CFG-20 | S | Sin sesión | [API] La configuración pública no incluye la moneda | P2 | OK |
| CFG-21 | S | Otros roles | No aparece; [API] responde 403 al modificar | P1 | OK |
| CFG-22 | V | Recorrer todas las pantallas en modo claro | Todo se lee correctamente | P1 | OK |
| CFG-23 | V | Recorrer todas las pantallas en modo oscuro | Todo se lee correctamente | P1 | OK |

## 23. Instalación local y operación

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| OPE-01 | O | Instalar desde cero con `docs/DOCKER.md` en un equipo limpio | Se completa sin pasos adicionales | P1 | PARCIAL |
| OPE-02 | O | Revisar el estado | Base, backend, web y respaldos en marcha; migraciones terminadas con éxito | P1 | OK |
| OPE-03 | S | Comprobar puertos publicados | La base y el backend no se publican fuera de Docker | P1 | OK |
| OPE-04 | S | `/docs` en producción | No está disponible | P1 | OK |
| OPE-05 | S | Arrancar con `SECRET_KEY` corta, `DEBUG=True` o sin zona horaria | El backend se niega a arrancar y explica el motivo | P1 | OK |
| OPE-06 | O | Apagar y encender el equipo | El sistema vuelve solo. Si Docker Desktop no abre al iniciar Windows, configurarlo y documentarlo | P1 | PARCIAL |
| OPE-07 | O | Cortar la luz durante una operación | Al volver, sin datos corruptos ni pagos a medias | P1 | PARCIAL |
| OPE-08 | O | Comprobar la copia automática | Se crea cada día; un día sin copia se recupera al encender | P1 | PARCIAL |
| OPE-09 | O | Guardar copias en un disco externo con `CLINICA_RESPALDOS` | Aparecen allí, y se conservan las últimas 30 | P1 | PARCIAL |
| OPE-10 | O | Restaurar una copia en una base aparte, con la guía | Se restaura sin errores | P1 | OK |
| OPE-11 | O | Comparar los datos restaurados con los originales | Coinciden pacientes, pagos, citas y evoluciones | P1 | OK |
| OPE-12 | O | Desconectar el disco de copias | El sistema sigue y el error aparece en el registro. Definir quién lo revisa | P2 | DECIDIR |
| OPE-13 | O | Actualizar a una versión nueva, con datos | Se aplican migraciones y no se pierde nada | P1 | OK |
| OPE-14 | O | Reiniciar el backend en plena jornada | Vuelve en segundos y las sesiones siguen válidas | P2 | OK |
| OPE-15 | O | Dejar el disco casi lleno | Definir un aviso; las copias fallan con un error visible en el registro | P2 | DECIDIR |
| OPE-16 | O | Fechas y horas | Zona horaria de la clínica configurada, igual a la de los equipos | P1 | OK |
| OPE-17 | O | Cambio de zona u hora en un equipo cliente | Decidir el comportamiento; todos los equipos deben tener la hora correcta | P2 | DECIDIR |
| OPE-18 | O | Recuperar el acceso del administrador en Docker | La guía funciona | P1 | OK |

### Red interna de la sede

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| RED-01 | O | Activar HTTPS con `tls internal` y un nombre interno | El sistema abre por `https://` desde el servidor | P1 | OK |
| RED-02 | O | Abrir desde otro equipo de la clínica | Funciona por nombre, en todos los equipos | P1 | MANUAL |
| RED-03 | O | Instalar el certificado raíz en un equipo | El navegador deja de mostrar advertencias | P1 | MANUAL |
| RED-04 | S | Entrar por HTTP | Redirige a HTTPS | P1 | OK |
| RED-05 | S | Revisar las cabeceras | HSTS, `nosniff` y bloqueo de marcos presentes | P2 | OK |
| RED-06 | S | Probar la conexión directa al puerto 8080 desde otro equipo | No responde: solo escucha en el servidor | P1 | PARCIAL |
| RED-07 | O | Fijar la IP del servidor y reiniciar el router | Los equipos siguen encontrándolo | P1 | MANUAL |
| RED-08 | O | Desconectar la red de un equipo mientras se usa | Muestra un error; al volver, continúa sin perder datos ya guardados | P2 | OK |
| RED-09 | O | Sin internet, pero con la red interna activa | El sistema funciona. Comprobar el tipo de letra y otros recursos externos | P1 | OK |
| RED-10 | O | Cinco equipos trabajando a la vez durante una hora | Sin errores ni lentitud notable | P1 | PARCIAL |
| RED-11 | S | Conectar un equipo ajeno a la red Wi-Fi de pacientes | No debe alcanzar el servidor: separar las redes | P1 | MANUAL |
| RED-12 | F | Tableta o celular en la red | Se puede usar | P3 | PARCIAL |

## 24. Seguridad general

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| SEG-01 | S | Inyección SQL en buscadores y filtros | Sin efecto ni error interno | P1 | OK |
| SEG-02 | S | Código HTML o JavaScript en todos los campos de texto | Se muestra como texto | P1 | OK |
| SEG-03 | S | [API] Cambiar el ID de otro registro en la URL con un rol sin acceso | Responde 403 o 404, nunca los datos | P1 | OK |
| SEG-04 | S | [API] Enviar campos no previstos en pagos y nómina | Se rechazan | P2 | OK |
| SEG-05 | S | Provocar un error de datos | La respuesta no revela SQL ni detalles internos | P1 | OK |
| SEG-06 | S | Ver el código publicado | Sin claves ni contraseñas | P1 | OK |
| SEG-07 | S | Revisar la imagen del backend | Sin `.env`, copias ni pruebas; corre sin ser root | P1 | OK |
| SEG-08 | S | Revisar el repositorio | `.env`, `.env.docker`, `.env.docker.admin` y `backups` no están versionados | P1 | OK |
| SEG-09 | S | Dejar un equipo sin usar durante horas | Decidir si debe cerrarse la sesión por inactividad: hoy solo vence a las 8 horas | P2 | DECIDIR |
| SEG-10 | S | Permisos de la carpeta de copias | Solo personal autorizado: contienen datos clínicos sin cifrar | P1 | MANUAL |
| SEG-11 | S | Ejecutar `npm audit` y `pip-audit` | Sin vulnerabilidades conocidas | P1 | OK |
| SEG-12 | S | Por HTTPS, intentar saltarse el límite de login falsificando `X-Forwarded-For` | El bloqueo se aplica igual | P1 | OK |

## 25. Rendimiento y datos en volumen

Carga antes una base de prueba con 5.000 pacientes, 50.000 citas y 100.000 pagos.

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| REN-01 | O | Abrir cada pantalla | Carga en menos de 3 segundos | P2 | OK |
| REN-02 | O | Buscar pacientes | Responde en menos de 1 segundo | P2 | OK |
| REN-03 | O | Reportes con «Todo» | Responde en menos de 5 segundos | P2 | OK |
| REN-04 | O | Agenda de un mes con más de 5.000 citas | Muestra las primeras y avisa que hay más | P2 | OK |
| REN-05 | O | Tiempo de la copia y tamaño del archivo | Termina dentro de un margen aceptable | P2 | OK |
| REN-06 | O | Memoria del servidor tras una jornada | Sin crecimiento continuo | P2 | PARCIAL |
| REN-07 | O | Nómina y productividad con muchos usuarios | Responden en menos de 3 segundos | P3 | OK |

## 26. Flujos completos de una jornada

| ID | Tipo | Caso y pasos | Resultado esperado | Prio | Estado |
|---|---|---|---|---|---|
| E2E-01 | I | **Paciente nuevo con plan:** registrar, odontograma, presupuesto, aprobar, agendar, atender, finalizar, cobrar | Saldo, evolución, odontograma, caja, comisión y reportes coinciden | P1 | OK |
| E2E-02 | I | **Consulta simple:** registrar, agendar, atender, finalizar y cobrar sin plan | Se cobra sin plan y deja su evolución | P1 | OK |
| E2E-03 | I | **Tratamiento en varias citas:** dos citas para el mismo plan, con abono parcial | Nunca se cobra dos veces; el saldo cuadra al final | P1 | OK |
| E2E-04 | I | **Paciente que no acepta:** presupuesto propuesto y consulta cobrada | El plan sigue propuesto, sin deuda | P1 | OK |
| E2E-05 | I | **Cancelación y reemplazo:** cancelar y dar el espacio a otro paciente | Ambas citas quedan visibles | P1 | OK |
| E2E-06 | I | **Error de cobro:** cobrar, anular, corregir y volver a cobrar | Caja, saldo, comisión y reportes quedan correctos | P1 | OK |
| E2E-07 | I | **Día completo de caja:** abrir, cobrar con todos los medios, gastos, adelanto y arqueo | El arqueo cuadra y el reporte del día coincide | P1 | OK |
| E2E-08 | I | **Fin de mes:** comisiones, adelantos y sueldos | Los saldos finales cuadran contra los pagos | P1 | OK |
| E2E-09 | I | **Turno:** entrada, descanso, salida, olvido y corrección | La bitácora refleja lo ocurrido | P1 | OK |
| E2E-10 | I | **Prótesis:** presupuesto, orden, recepción, instalación y pago al laboratorio | Cada etapa queda registrada | P2 | OK |
| E2E-11 | I | **Recuperación:** jornada completa, copia, restauración en otra base y comparación | Todo coincide | P1 | OK |
| E2E-12 | I | **Paralelo con el método actual:** una semana comparando cada día caja y agenda | Sin diferencias, o con cada diferencia explicada | P1 | MANUAL |
