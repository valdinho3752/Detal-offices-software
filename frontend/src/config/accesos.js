// Qué necesita cada pantalla. La API es quien bloquea de verdad; esto solo oculta lo que no se puede usar.
const PERMISOS_POR_RUTA = {
  '/pacientes': ['PACIENTES_READ'],
  '/odontograma': ['ODONTOGRAMA_READ'],
  '/citas': ['CITAS_READ'],
  '/asistencia': ['ASISTENCIA_FICHAR', 'ASISTENCIA_READ_ALL'],
  '/evolucion': ['HISTORIA_CLINICA_READ'],
  '/visitas': ['HISTORIA_CLINICA_READ'],
  '/radiografias': ['RADIOGRAFIAS_READ'],
  '/protesis': ['PROTESIS_READ'],
  '/caja': ['CAJA_READ'],
  '/cobranzas': ['CAJA_PAGOS'],
  '/auditoria': ['AUDITORIA_READ'],
  '/reportes': ['REPORTES_READ'],
  '/usuarios': ['USUARIOS_MANAGE', 'ROLES_MANAGE'],
};

// Un doctor solo puede cambiar sus propias citas; la API aplica la misma regla
const ROLES_GESTION_AGENDA = ['ADMIN', 'RECEPCION', 'RECEPCIONISTA', 'ASISTENTE'];

export function puedeModificarCita(cita, user) {
  return ROLES_GESTION_AGENDA.includes(user?.rol_str) || !user?.doctor_id || cita?.doctor_id === user.doctor_id;
}

export function puedeAcceder(ruta, { user, isAdmin, tienePermiso }) {
  if (isAdmin) return true;
  if (ruta === '/tratamientos') return false; // Exclusivo del administrador
  // Cada doctor puede consultar sus propias comisiones
  if (ruta === '/nomina') return Boolean(user?.doctor_id) || tienePermiso('EMPLEADOS_READ');
  const requeridos = PERMISOS_POR_RUTA[ruta];
  return !requeridos || requeridos.some(tienePermiso);
}
