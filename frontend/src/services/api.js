const API_BASE = '/api/v1';

function mensajeDeValidacion(mensaje) {
  const texto = String(mensaje || '').replace(/^Value error, /, '');
  if (texto.startsWith('value is not a valid email')) return 'El correo electrónico no es válido';
  if (texto === 'Field required') return 'Falta completar un campo obligatorio';
  if (texto.startsWith('Input should be a valid date')) return 'La fecha no es válida';
  return texto;
}

// La API describe los datos rechazados como una lista: se muestra solo el texto para la persona
function textoDeError(detalle, porDefecto) {
  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle)) {
    return detalle.map((e) => mensajeDeValidacion(e.msg)).filter(Boolean).join('. ') || porDefecto;
  }
  return porDefecto;
}

const escriturasEnCurso = new Map();

// Un doble clic no debe cobrar ni registrar dos veces: la misma escritura en curso no se reenvía
function request(endpoint, options = {}) {
  if (!options.method || options.method === 'GET' || options.body instanceof FormData) {
    return enviar(endpoint, options);
  }
  const clave = `${options.method} ${endpoint} ${options.body ?? ''}`;
  if (!escriturasEnCurso.has(clave)) {
    escriturasEnCurso.set(clave, enviar(endpoint, options).finally(() => escriturasEnCurso.delete(clave)));
  }
  return escriturasEnCurso.get(clave);
}

const RUTA_CAMBIO_CONTRASENA = '/auth/cambiar-contrasena';
let renovacionDeSesion = null;

async function enviar(endpoint, options) {
  const token = localStorage.getItem('token');
  const headers = {
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !endpoint.includes('/auth/login')) {
    // Enviada con el token anterior mientras se cambiaba la contraseña: la sesión sigue, con el token nuevo
    if (renovacionDeSesion && !endpoint.includes(RUTA_CAMBIO_CONTRASENA)) await renovacionDeSesion.catch(() => {});
    const tokenActual = localStorage.getItem('token');
    if (tokenActual && tokenActual !== token) return enviar(endpoint, options);

    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Sesión expirada');
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(textoDeError(data?.detail, `Error en la solicitud: ${response.statusText}`));
  }

  return data;
}

export const api = {
  // ==================== AUTH & FICHAJE ====================
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(textoDeError(err.detail, 'Credenciales inválidas'));
    }
    return res.json();
  },
  getMe: () => request('/auth/me'),
  actualizarTiempoSesion: (minutos) => request('/auth/sesion', { method: 'PUT', body: JSON.stringify({ minutos_inactividad: minutos }) }),
  cambiarContrasena: (data) => {
    renovacionDeSesion = request(RUTA_CAMBIO_CONTRASENA, { method: 'POST', body: JSON.stringify(data) })
      .then((respuesta) => {
        localStorage.setItem('token', respuesta.access_token);
        return respuesta;
      })
      .finally(() => { renovacionDeSesion = null; });
    return renovacionDeSesion;
  },
  fichar: (tipo_evento, observaciones = '') =>
    request('/auth/fichar', {
      method: 'POST',
      body: JSON.stringify({ tipo_evento, observaciones }),
    }),
  getEstadoFichaje: () => request('/auth/fichaje/estado'),
  getJornadasSinSalida: () => request('/personal/asistencia/jornadas-sin-salida'),
  anularMarcaje: (id, motivo) => request(`/personal/asistencia/${id}/anular`, { method: 'POST', body: JSON.stringify({ motivo }) }),
  corregirMarcaje: (data) => request('/personal/asistencia/correcciones', { method: 'POST', body: JSON.stringify(data) }),
  getAsistencias: (params = '') => request(`/personal/asistencia${params}`),

  // ==================== USUARIOS & ROLES ====================
  getRoles: () => request('/usuarios/roles'),
  getPermisos: () => request('/usuarios/permisos'),
  createRol: (data) => request('/usuarios/roles', { method: 'POST', body: JSON.stringify(data) }),
  asignarPermisosRol: (rolId, permisoIds) =>
    request(`/usuarios/roles/${rolId}/permisos`, { method: 'POST', body: JSON.stringify(permisoIds) }),
  getUsuarios: () => request('/usuarios/'),
  createUsuario: (data) => request('/usuarios/', { method: 'POST', body: JSON.stringify(data) }),
  updateUsuario: (id, data) => request(`/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getDoctores: () => request('/usuarios/doctores/lista'),
  getAsistentes: () => request('/usuarios/asistentes/lista'),

  // ==================== PACIENTES & HISTORIA ====================
  getPacientes: (q = '', skip = 0, limit = 100, estado = '') => {
    const parametros = new URLSearchParams(q ? { q } : { skip, limit });
    if (estado) parametros.set('estado', estado);
    return request(`/pacientes/?${parametros}`);
  },
  getPaciente: (id) => request(`/pacientes/${id}`),
  createPaciente: (data) => request('/pacientes/', { method: 'POST', body: JSON.stringify(data) }),
  updatePaciente: (id, data) => request(`/pacientes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateAntecedentes: (id, data) => request(`/pacientes/${id}/antecedentes`, { method: 'PUT', body: JSON.stringify(data) }),
  getPacienteSaldo: (id) => request(`/pacientes/${id}/saldo`),

  // ==================== ODONTOGRAMA & PIEZAS ====================
  getOdontogramas: (pacienteId, tipoRegistro = '') =>
    request(`/odontogramas/?paciente_id=${pacienteId}${tipoRegistro ? '&tipo_registro=' + tipoRegistro : ''}`),
  getOdontograma: (id) => request(`/odontogramas/${id}`),
  createOdontograma: (data) => request('/odontogramas/', { method: 'POST', body: JSON.stringify(data) }),
  clonarOdontogramaComoEvolucion: (id) => request(`/odontogramas/${id}/clonar-como-evolucion`, { method: 'POST' }),
  updateOdontograma: (id, data) => request(`/odontogramas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updatePieza: (id, data) => request(`/odontogramas/piezas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  createHallazgo: (data) => request('/odontogramas/hallazgos', { method: 'POST', body: JSON.stringify(data) }),
  deleteHallazgo: (id) => request(`/odontogramas/hallazgos/${id}`, { method: 'DELETE' }),

  // ==================== PLANES DE TRATAMIENTO ====================
  getCatalogoTratamientos: () => request('/tratamientos/catalogo'),
  getCatalogoCompleto: () => request('/tratamientos/catalogo?activo_solo=false'),
  createTratamiento: (data) => request('/tratamientos/catalogo', { method: 'POST', body: JSON.stringify(data) }),
  updateTratamiento: (id, data) => request(`/tratamientos/catalogo/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTratamiento: (id) => request(`/tratamientos/catalogo/${id}`, { method: 'DELETE' }),
  getPlanes: (pacienteId) => request(`/tratamientos/planes?paciente_id=${pacienteId}`),
  createPlan: (data) => request('/tratamientos/planes', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (id, data) => request(`/tratamientos/planes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  createItemPlan: (data) => request('/tratamientos/items', { method: 'POST', body: JSON.stringify(data) }),
  updateItemPlan: (id, data) => request(`/tratamientos/items/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteItemPlan: (id) => request(`/tratamientos/items/${id}`, { method: 'DELETE' }),

  // ==================== CITAS & GESTIÓN DE SILLÓN ====================
  getCitas: (params = '') => request(`/citas/${params}`),
  createCita: (data) => request('/citas/', { method: 'POST', body: JSON.stringify(data) }),
  updateCita: (id, data) => request(`/citas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCita: (id) => request(`/citas/${id}`, { method: 'DELETE' }),
  controlSillon: (id, data) => request(`/citas/${id}/sillon`, { method: 'PATCH', body: JSON.stringify(data) }),

  // ==================== EVOLUCIÓN CLÍNICA & RECETAS ====================
  getVisitas: (pacienteId) => request(`/visitas/?paciente_id=${pacienteId}`),
  getVisita: (id) => request(`/visitas/${id}`),
  createVisita: (data) => request('/visitas/', { method: 'POST', body: JSON.stringify(data) }),
  agregarObservacionVisita: (id, texto) =>
    request(`/visitas/${id}/observaciones`, { method: 'POST', body: JSON.stringify({ texto }) }),

  // ==================== RADIOGRAFÍAS & IMÁGENES ====================
  getRadiografias: (pacienteId, piezaFdi = null) => {
    let url = `/radiografias/?paciente_id=${pacienteId}`;
    if (piezaFdi) url += `&pieza_fdi=${piezaFdi}`;
    return request(url);
  },
  getRadiografia: (id) => request(`/radiografias/${id}`),
  createRadiografia: (data) => request('/radiografias/', { method: 'POST', body: JSON.stringify(data) }),
  updateRadiografia: (id, data) => request(`/radiografias/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRadiografia: (id) => request(`/radiografias/${id}`, { method: 'DELETE' }),

  // ==================== PRÓTESIS & LABORATORIO ====================
  getProtesis: (params = '') => request(`/protesis/${params}`),
  createProtesis: (data) => request('/protesis/', { method: 'POST', body: JSON.stringify(data) }),
  updateProtesis: (id, data) => request(`/protesis/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  pagarLaboratorio: (id) => request(`/protesis/${id}/pagar-laboratorio`, { method: 'POST', body: JSON.stringify({}) }),

  // ==================== CAJA & FINANZAS ====================
  getEstadoCaja: () => request('/caja/estado'),
  abrirCaja: (data) => request('/caja/abrir', { method: 'POST', body: JSON.stringify(data) }),
  cerrarCaja: (data) => request('/caja/cerrar', { method: 'POST', body: JSON.stringify(data) }),
  registrarPago: (data) => request('/caja/pagos', { method: 'POST', body: JSON.stringify(data) }),
  anularPago: (id, motivo) => request(`/caja/pagos/${id}/anular`, { method: 'POST', body: JSON.stringify({ motivo }) }),
  registrarEgreso: (data) => request('/caja/egresos', { method: 'POST', body: JSON.stringify(data) }),

  // ==================== SILLONES ====================
  getSillones: () => request('/sillones/'),
  createSillon: (data) => request('/sillones/', { method: 'POST', body: JSON.stringify(data) }),
  updateSillon: (id, data) => request(`/sillones/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSillon: (id) => request(`/sillones/${id}`, { method: 'DELETE' }),

  // ==================== COBROS DE CITAS ====================
  getCobrosCita: (params = '') => request(`/cobros-cita/${params}`),
  getCobroCita: (id) => request(`/cobros-cita/${id}`),
  updateCobroCita: (id, data) => request(`/cobros-cita/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  confirmarCobroCita: (id, data) => request(`/cobros-cita/${id}/confirmar`, { method: 'POST', body: JSON.stringify(data) }),
  cerrarCobroCitaSinPago: (id, motivo) =>
    request(`/cobros-cita/${id}/cerrar-sin-pago`, { method: 'POST', body: JSON.stringify({ motivo }) }),

  // ==================== CONFIGURACIÓN ====================
  getConfiguracionPublica: () => request('/configuracion/publica'),
  getEstadoCopias: () => request('/configuracion/estado-copias'),
  getConfiguracion: () => request('/configuracion/'),
  subirLogo: (archivo) => {
    const datos = new FormData();
    datos.append('archivo', archivo);
    return request('/configuracion/logo', { method: 'POST', body: datos });
  },
  quitarLogo: () => request('/configuracion/logo', { method: 'DELETE' }),
  updateConfiguracion: (data) => request('/configuracion/', { method: 'PUT', body: JSON.stringify(data) }),

  // ==================== NÓMINA & COMISIONES ====================
  getContratos: () => request('/personal/contratos'),
  crearContrato: (data) => request('/personal/contratos', { method: 'POST', body: JSON.stringify(data) }),
  actualizarContrato: (id, data) => request(`/personal/contratos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getPersonalNomina: () => request('/empleados/personal'),
  getLiquidacion: (usuarioId) => request(`/empleados/liquidacion/${usuarioId}`),
  getPagosEmpleados: (usuarioId = '') => request(`/empleados/pagos${usuarioId ? `?usuario_empleado_id=${usuarioId}` : ''}`),
  registrarPagoEmpleado: (data) => request('/empleados/pagos', { method: 'POST', body: JSON.stringify(data) }),

  // ==================== AUDITORÍA FORENSE ====================
  getAuditoria: (params = '') => request(`/auditoria/${params}`),

  // ==================== REPORTES ANALÍTICOS BI ====================
  getReporteDemanda: (limit = 10, periodo = {}) => request(`/reportes/tratamientos-demanda?${new URLSearchParams({ limit, ...periodo })}`),
  getReporteProductividad: (periodo = {}) => request(`/reportes/productividad-doctores?${new URLSearchParams(periodo)}`),
  getReporteFinanciero: (periodo = {}) => request(`/reportes/resumen-financiero?${new URLSearchParams(periodo)}`),
  getGraficoReporte: async (nombre, tema, periodo = {}) => {
    const res = await fetch(`${API_BASE}/reportes/graficos/${nombre}?${new URLSearchParams({ tema, ...periodo })}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    });
    if (!res.ok) throw new Error('No se pudo generar el gráfico');
    return res.blob();
  },
};
