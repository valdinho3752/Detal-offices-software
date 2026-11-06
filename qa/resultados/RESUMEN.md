# Resultados de QA

Última ejecución: 2026-11-05 16:02, contra https://localhost:8443.

| Estado | Casos |
|---|---|
| DECIDIR | 8 |
| FALLA | 11 |
| MANUAL | 6 |
| OK | 505 |
| PARCIAL | 9 |
| Pendiente | 2 |
| **Total** | **541** |

Automatizados en esta ejecución: 69 (37 en pantalla y 32 por API).

## Fallos

| Caso | Prueba | Detalle |
|---|---|---|
| CCI-18 | `test_auditoria_de_la_cuenta_de_cita` | AssertionError: assert False + where False = <apoyo.Respuesta object at 0x000001902C7736B0>.ok + where <apoyo.Respuesta object at 0x000001902C7736B0> = put('/cobros-cita/bc16bc3a-6f09-4bb0-b72b-23310d846ceb', {'lineas':  |
| CFG-11 | `test_jornada_copia_y_restauracion` | RuntimeError: ('exec', '-T', 'db', 'sh', '-c', 'psql -U "$POSTGRES_USER" -d qa_rest_fd5ff1 -Atc "select archivo_url from radiografias where id = \'053d2489-3ad2-495f-b57c-ddad10e8b4df\'"'): ERROR: relation "radiografias" |
| E2E-10 | `test_protesis_de_principio_a_fin` | AssertionError: Recepción registrada assert None |
| E2E-11 | `test_jornada_copia_y_restauracion` | RuntimeError: ('exec', '-T', 'db', 'sh', '-c', 'psql -U "$POSTGRES_USER" -d qa_rest_fd5ff1 -Atc "select archivo_url from radiografias where id = \'053d2489-3ad2-495f-b57c-ddad10e8b4df\'"'): ERROR: relation "radiografias" |
| OPE-13 | `test_actualizar_con_datos` | AssertionError: python: can't open file 'C:\\Users\\alepi\\AppData\\Local\\Temp\\pytest-of-alepi\\pytest-7\\instalacion1\\proyecto\\scripts\\preparar_docker.py': [Errno 2] No such file or directory assert 2 == 0 + where  |
| PAC-21 | `test_paciente_sin_opcion_de_inactivo` | AssertionError: Hoy no se puede marcar inactivo assert 'INACTIVO' == 'ACTIVO' - ACTIVO + INACTIVO ? ++ |
| PAC-23 | `test_listado_con_muchos_pacientes` | playwright._impl._errors.TimeoutError: Locator.wait_for: Timeout 3000ms exceeded. Call log: - waiting for locator("form").last.get_by_title("Cambiar o deseleccionar paciente") to be visible |
| RAD-05 | `test_visor_e_imagen_rota` | AssertionError: {"detail":[{"type":"value_error","loc":["body","archivo_url"],"msg":"Value error, La dirección de la imagen debe empezar con http:// o https://","input":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEA |
| RAD-08 | `test_visor_e_imagen_rota` | AssertionError: {"detail":[{"type":"value_error","loc":["body","archivo_url"],"msg":"Value error, La dirección de la imagen debe empezar con http:// o https://","input":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEA |
| RAD-15 | `test_jornada_copia_y_restauracion` | RuntimeError: ('exec', '-T', 'db', 'sh', '-c', 'psql -U "$POSTGRES_USER" -d qa_rest_fd5ff1 -Atc "select archivo_url from radiografias where id = \'053d2489-3ad2-495f-b57c-ddad10e8b4df\'"'): ERROR: relation "radiografias" |
| USU-26 | `test_doctor_desactivado_con_citas` | AssertionError: assert 'e987e86b-a937-46d8-b9dc-b591ce52de49' not in {'2ced4249-38b4-4277-8685-29945116e2da', '81b6b1ed-8e2a-4116-a426-31f5b9ad3e1b', 'e987e86b-a937-46d8-b9dc-b591ce52de49'} + where 'e987e86b-a937-46d8-b9 |

## Falta comprobar o decidir

| Caso | Estado | Prio | Motivo |
|---|---|---|---|
| NOM-30 | DECIDIR | P2 | Un empleado desactivado desaparece de Nómina aunque tenga saldo por pagar. ¿Debe seguir visible? |
| OPE-12 | DECIDIR | P2 | Sin carpeta de copias, el sistema sigue y el error queda en el registro. ¿Quién lo revisa? |
| OPE-15 | DECIDIR | P2 | Una copia que no se puede escribir deja un error en el registro, sin aviso en pantalla. ¿Hace falta un aviso? |
| OPE-17 | DECIDIR | P2 | Las fechas se muestran según la zona horaria de cada equipo. ¿Se obliga a usar la de la clínica? |
| PAC-21 | DECIDIR | P2 | La pantalla no permite marcar un paciente como inactivo, aunque la base tiene el campo. ¿Hace falta? |
| SEG-09 | DECIDIR | P2 | La sesión solo vence a las 8 horas, sin cierre por inactividad. ¿Hace falta? |
| AGE-38 | DECIDIR | P3 | Hoy se permite registrar citas en fechas pasadas. ¿Se mantiene para cargar historia? |
| CAJ-23 | DECIDIR | P3 | Hoy la API permite cobrar por transferencia con la caja cerrada. ¿Debe impedirse? |
| PRO-16 | DECIDIR | P3 | El egreso descuenta la caja, pero no queda vinculado a la orden. ¿Debe quedar vinculado? |
| E2E-12 | MANUAL | P1 | Una semana en paralelo con el método actual, comparando caja y agenda cada día. |
| RED-02 | MANUAL | P1 | Abrir el sistema por nombre desde otro equipo de la clínica. |
| RED-03 | MANUAL | P1 | Instalar el certificado raíz en cada equipo y comprobar que el navegador no avisa. |
| RED-07 | MANUAL | P1 | Fijar la IP del servidor y reiniciar el router. |
| RED-11 | MANUAL | P1 | Conectar un equipo a la Wi-Fi de pacientes; depende de cómo esté separada la red. |
| SEG-10 | MANUAL | P1 | Definir quién accede a la carpeta de copias. Hoy cualquier usuario de Windows con sesión en el equipo puede leerla y modificarla. |
| OPE-01 | PARCIAL | P1 | Instalación en una carpeta limpia, con los pasos de docs/DOCKER.md y otra base. Falta repetirla en un equipo sin nada instalado. |
| OPE-06 | PARCIAL | P1 | Los contenedores vuelven solos al detenerse de forma brusca. Falta apagar el equipo: Docker Desktop tiene desactivado el inicio automático. |
| OPE-07 | PARCIAL | P1 | Se mató la base durante cobros simultáneos y no quedaron pagos a medias. Falta un corte de luz real, que también afecta al disco. |
| OPE-08 | PARCIAL | P1 | La copia se crea al arrancar si falta la del día. Falta observar varios días seguidos en el equipo real. |
| OPE-09 | PARCIAL | P1 | La carpeta configurable y la conservación de las últimas copias funcionan. Falta probar con el disco externo. |
| RED-06 | PARCIAL | P1 | El puerto solo escucha en 127.0.0.1 y otro contenedor no llega por la IP del servidor. Falta probarlo desde otro equipo. |
| RED-10 | PARCIAL | P1 | Cinco clientes simultáneos durante 3 minutos, sin errores. Falta una hora con cinco equipos reales. |
| REN-06 | PARCIAL | P2 | Sin crecimiento continuo de memoria durante una carga corta. Falta medir una jornada real. |
| RED-12 | PARCIAL | P3 | Comprobado con emulación táctil de tableta y celular. Falta un dispositivo real en la red. |
