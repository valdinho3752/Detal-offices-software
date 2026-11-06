# Resultados de QA

Última ejecución: 2026-11-05 20:06, contra https://localhost:8443.

| Estado | Casos |
|---|---|
| MANUAL | 6 |
| OK | 531 |
| PARCIAL | 9 |
| **Total** | **546** |

Automatizados en esta ejecución: 2 (0 en pantalla y 2 por API).


## Falta comprobar o decidir

| Caso | Estado | Prio | Motivo |
|---|---|---|---|
| E2E-12 | MANUAL | P1 | Una semana en paralelo con el método actual, comparando caja y agenda cada día. |
| RED-02 | MANUAL | P1 | Abrir el sistema por nombre desde otro equipo de la clínica. |
| RED-03 | MANUAL | P1 | Instalar el certificado raíz en cada equipo y comprobar que el navegador no avisa. |
| RED-07 | MANUAL | P1 | Fijar la IP del servidor y reiniciar el router. |
| RED-11 | MANUAL | P1 | Conectar un equipo a la Wi-Fi de pacientes; depende de cómo esté separada la red. |
| SEG-10 | MANUAL | P1 | Definir quién accede a la carpeta de copias. Hoy cualquier usuario de Windows con sesión en el equipo puede leerla y modificarla. |
| OPE-01 | PARCIAL | P1 | Instalación en una carpeta limpia, con los pasos de docs/DOCKER.md y otra base. Falta repetirla en un equipo sin nada instalado. |
| OPE-06 | PARCIAL | P1 | Los contenedores vuelven solos al detenerse de forma brusca. Falta apagar el equipo: Docker Desktop tiene desactivado el inicio automático. |
| OPE-07 | PARCIAL | P1 | Se mató la base durante cobros simultáneos y no quedaron pagos a medias. Falta un corte de luz real, que también afecta al disco. |
| OPE-08 | PARCIAL | P1 | La copia se crea al encender, aunque no sea la hora programada, si la anterior tiene más de 24 horas. Falta observar varios días seguidos en el equipo real. |
| OPE-09 | PARCIAL | P1 | La carpeta configurable y la conservación de las últimas copias funcionan. Falta probar con el disco externo. |
| RED-06 | PARCIAL | P1 | El puerto solo escucha en 127.0.0.1 y no responde por la IP de red del servidor. Falta probarlo desde otro equipo. |
| RED-10 | PARCIAL | P1 | Cinco clientes simultáneos durante 3 minutos, sin errores. Falta una hora con cinco equipos reales. |
| REN-06 | PARCIAL | P2 | Sin crecimiento continuo de memoria durante una carga corta. Falta medir una jornada real. |
| RED-12 | PARCIAL | P3 | Comprobado con emulación táctil de tableta y celular. Falta un dispositivo real en la red. |
