"""
Casos que estas pruebas no pueden dar por aprobados, con el motivo. Se escriben en el documento en cada ejecución.

MANUAL: requiere un segundo equipo, hardware o personas.
PARCIAL: comprobado aquí de forma simulada; falta confirmarlo en el equipo real.
DECIDIR: el comportamiento actual está comprobado, pero el caso pide una decisión de la clínica.
"""

CASOS = {
    # Requieren equipos, red física o personas
    "RED-02": ("MANUAL", "Abrir el sistema por nombre desde otro equipo de la clínica."),
    "RED-03": ("MANUAL", "Instalar el certificado raíz en cada equipo y comprobar que el navegador no avisa."),
    "RED-07": ("MANUAL", "Fijar la IP del servidor y reiniciar el router."),
    "RED-11": ("MANUAL", "Conectar un equipo a la Wi-Fi de pacientes; depende de cómo esté separada la red."),
    "E2E-12": ("MANUAL", "Una semana en paralelo con el método actual, comparando caja y agenda cada día."),
    "SEG-10": ("MANUAL", "Definir quién accede a la carpeta de copias. Hoy cualquier usuario de Windows con sesión en el equipo puede leerla y modificarla."),

    # Simulados aquí
    "OPE-01": ("PARCIAL", "Instalación en una carpeta limpia, con los pasos de docs/DOCKER.md y otra base. Falta repetirla en un equipo sin nada instalado."),
    "OPE-06": ("PARCIAL", "Los contenedores vuelven solos al detenerse de forma brusca. Falta apagar el equipo: Docker Desktop tiene desactivado el inicio automático."),
    "OPE-07": ("PARCIAL", "Se mató la base durante cobros simultáneos y no quedaron pagos a medias. Falta un corte de luz real, que también afecta al disco."),
    "OPE-08": ("PARCIAL", "La copia se crea al arrancar si falta la del día. Falta observar varios días seguidos en el equipo real."),
    "OPE-09": ("PARCIAL", "La carpeta configurable y la conservación de las últimas copias funcionan. Falta probar con el disco externo."),
    "RED-06": ("PARCIAL", "El puerto solo escucha en 127.0.0.1 y no responde por la IP de red del servidor. Falta probarlo desde otro equipo."),
    "RED-10": ("PARCIAL", "Cinco clientes simultáneos durante 3 minutos, sin errores. Falta una hora con cinco equipos reales."),
    "RED-12": ("PARCIAL", "Comprobado con emulación táctil de tableta y celular. Falta un dispositivo real en la red."),
    "REN-06": ("PARCIAL", "Sin crecimiento continuo de memoria durante una carga corta. Falta medir una jornada real."),

    # Requieren una decisión
    "PAC-21": ("DECIDIR", "La pantalla no permite marcar un paciente como inactivo; solo la API. Sigue apareciendo en las búsquedas. ¿Hace falta en pantalla?"),
    "AGE-38": ("DECIDIR", "Hoy se permite registrar citas en fechas pasadas. ¿Se mantiene para cargar historia?"),
    "PRO-16": ("DECIDIR", "El egreso descuenta la caja, pero no queda vinculado a la orden. ¿Debe quedar vinculado?"),
    "CAJ-23": ("DECIDIR", "Hoy la API permite cobrar por transferencia con la caja cerrada. ¿Debe impedirse?"),
    "NOM-30": ("DECIDIR", "Un empleado desactivado desaparece de Nómina aunque tenga saldo por pagar. ¿Debe seguir visible?"),
    "OPE-12": ("DECIDIR", "Sin carpeta de copias, el sistema sigue y el error queda en el registro. ¿Quién lo revisa?"),
    "OPE-15": ("DECIDIR", "Una copia que no se puede escribir deja un error en el registro, sin aviso en pantalla. ¿Hace falta un aviso?"),
    "OPE-17": ("DECIDIR", "Las fechas se muestran según la zona horaria de cada equipo. ¿Se obliga a usar la de la clínica?"),
    "SEG-09": ("DECIDIR", "La sesión solo vence a las 8 horas, sin cierre por inactividad. ¿Hace falta?"),
}
