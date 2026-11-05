const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
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
    const errorMsg = data?.detail || `Error en la solicitud: ${response.statusText}`;
    throw new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
  }

  return data;
}

export const api = {
  // ==================== AUTH & FICHAJE (HU-06) ====================
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
      throw new Error(err.detail || 'Credenciales inválidas');
    }
    return res.json();
  },
  getMe: () => request('/auth/me'),
  fichar: (tipo_evento, observaciones = '') =>
    request('/auth/fichar', {
      method: 'POST',
      body: JSON.stringify({ tipo_evento, observaciones }),
    }),
  getAsistencias: (params = '') => request(`/personal/asistencia${params}`),

  // ==================== USUARIOS & ROLES (HU-01, HU-02) ====================
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

  // ==================== PACIENTES & HISTORIA (HU-03) ====================
  getPacientes: (q = '', skip = 0, limit = 100) => {
    const query = q ? `?q=${encodeURIComponent(q)}` : `?skip=${skip}&limit=${limit}`;
    return request(`/pacientes/${query}`);
  },
  getPaciente: (id) => request(`/pacientes/${id}`),
  createPaciente: (data) => request('/pacientes/', { method: 'POST', body: JSON.stringify(data) }),
  updatePaciente: (id, data) => request(`/pacientes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getPacienteSaldo: (id) => request(`/pacientes/${id}/saldo`),

  // ==================== ODONTOGRAMA & PIEZAS (HU-04) ====================
  getOdontogramas: (pacienteId, tipoRegistro = '') =>
    request(`/odontogramas/?paciente_id=${pacienteId}${tipoRegistro ? '&tipo_registro=' + tipoRegistro : ''}`),
  getOdontograma: (id) => request(`/odontogramas/${id}`),
  createOdontograma: (data) => request('/odontogramas/', { method: 'POST', body: JSON.stringify(data) }),
  clonarOdontogramaComoEvolucion: (id) => request(`/odontogramas/${id}/clonar-como-evolucion`, { method: 'POST' }),
  updateOdontograma: (id, data) => request(`/odontogramas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updatePieza: (id, data) => request(`/odontogramas/piezas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  createHallazgo: (data) => request('/odontogramas/hallazgos', { method: 'POST', body: JSON.stringify(data) }),
  deleteHallazgo: (id) => request(`/odontogramas/hallazgos/${id}`, { method: 'DELETE' }),

  // ==================== PLANES DE TRATAMIENTO (HU-04, HU-07) ====================
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

  // ==================== CITAS & GESTIÓN DE SILLÓN (HU-05) ====================
  getCitas: (params = '') => request(`/citas/${params}`),
  createCita: (data) => request('/citas/', { method: 'POST', body: JSON.stringify(data) }),
  updateCita: (id, data) => request(`/citas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCita: (id) => request(`/citas/${id}`, { method: 'DELETE' }),
  controlSillon: (id, data) => request(`/citas/${id}/sillon`, { method: 'PATCH', body: JSON.stringify(data) }),

  // ==================== EVOLUCIÓN CLÍNICA & RECETAS (HU-07) ====================
  getVisitas: (pacienteId) => request(`/visitas/?paciente_id=${pacienteId}`),
  getVisita: (id) => request(`/visitas/${id}`),
  createVisita: (data) => request('/visitas/', { method: 'POST', body: JSON.stringify(data) }),
  updateVisita: (id, data) => request(`/visitas/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  agregarObservacionVisita: (id, texto) =>
    request(`/visitas/${id}/observaciones`, { method: 'POST', body: JSON.stringify({ texto }) }),

  // ==================== RADIOGRAFÍAS & IMÁGENES (HU-08) ====================
  getRadiografias: (pacienteId, piezaFdi = null) => {
    let url = `/radiografias/?paciente_id=${pacienteId}`;
    if (piezaFdi) url += `&pieza_fdi=${piezaFdi}`;
    return request(url);
  },
  getRadiografia: (id) => request(`/radiografias/${id}`),
  createRadiografia: (data) => request('/radiografias/', { method: 'POST', body: JSON.stringify(data) }),
  updateRadiografia: (id, data) => request(`/radiografias/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRadiografia: (id) => request(`/radiografias/${id}`, { method: 'DELETE' }),

  // ==================== PRÓTESIS & LABORATORIO (HU-09) ====================
  getProtesis: (params = '') => request(`/protesis/${params}`),
  createProtesis: (data) => request('/protesis/', { method: 'POST', body: JSON.stringify(data) }),
  updateProtesis: (id, data) => request(`/protesis/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // ==================== CAJA & FINANZAS (HU-10, HU-11) ====================
  getEstadoCaja: () => request('/caja/estado'),
  abrirCaja: (data) => request('/caja/abrir', { method: 'POST', body: JSON.stringify(data) }),
  cerrarCaja: (data) => request('/caja/cerrar', { method: 'POST', body: JSON.stringify(data) }),
  registrarPago: (data) => request('/caja/pagos', { method: 'POST', body: JSON.stringify(data) }),
  registrarEgreso: (data) => request('/caja/egresos', { method: 'POST', body: JSON.stringify(data) }),

  // ==================== NÓMINA & COMISIONES (HU-12) ====================
  getContratos: () => request('/personal/contratos'),
  getComisionesDoctor: (doctorId) => request(`/empleados/comisiones-doctor/${doctorId}`),
  getPagosEmpleados: (usuarioId = '') => request(`/empleados/pagos${usuarioId ? `?usuario_empleado_id=${usuarioId}` : ''}`),
  registrarPagoEmpleado: (data) => request('/empleados/pagos', { method: 'POST', body: JSON.stringify(data) }),

  // ==================== AUDITORÍA FORENSE (HU-13) ====================
  getAuditoria: (params = '') => request(`/auditoria/${params}`),

  // ==================== REPORTES ANALÍTICOS BI (HU-14) ====================
  getReporteDemanda: (limit = 10) => request(`/reportes/tratamientos-demanda?limit=${limit}`),
  getReporteProductividad: () => request('/reportes/productividad-doctores'),
  getReporteFinanciero: () => request('/reportes/resumen-financiero'),
};
