import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { aFechaLocal, periodoDelDia } from '../utils/fechas';
import { useAuth } from '../context/AuthContext';
import ErrorModal from '../components/ErrorModal';
import {
  Clock,
  LogIn,
  LogOut,
  Coffee,
  CheckCircle,
  AlertCircle,
  Calendar,
  User,
  Users,
  Shield,
  Pencil,
  AlertTriangle,
} from 'lucide-react';

const BOTONES_MARCAJE = [
  { tipo: 'ENTRADA', texto: 'Entrada', Icono: LogIn, clase: 'bg-emerald-600 enabled:hover:bg-emerald-500 shadow-emerald-600/20' },
  { tipo: 'INICIO_DESCANSO', texto: 'Descanso', Icono: Coffee, clase: 'bg-amber-600 enabled:hover:bg-amber-500 shadow-amber-600/20' },
  { tipo: 'FIN_DESCANSO', texto: 'Fin Descanso', Icono: Coffee, clase: 'bg-sky-600 enabled:hover:bg-sky-500 shadow-sky-600/20' },
  { tipo: 'SALIDA', texto: 'Salida', Icono: LogOut, clase: 'bg-rose-600 enabled:hover:bg-rose-500 shadow-rose-600/20' },
];
const ESTADOS_TURNO = {
  SIN_TURNO: { texto: 'Fuera de turno', clase: 'bg-slate-500/10 border-slate-500/30 text-slate-600 dark:text-slate-300' },
  EN_TURNO: { texto: 'En turno', clase: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400' },
  EN_DESCANSO: { texto: 'En descanso', clase: 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400' },
  TURNO_CERRADO: { texto: 'Turno cerrado', clase: 'bg-slate-500/10 border-slate-500/30 text-slate-600 dark:text-slate-300' },
};
const NOMBRES_EVENTO = { ENTRADA: 'Entrada', INICIO_DESCANSO: 'Inicio de descanso', FIN_DESCANSO: 'Fin de descanso', SALIDA: 'Salida' };

const CAMPO = 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';
const LIMITE_LISTADO = 5000; // Máximo que devuelve la API en una consulta
const CORRECCION_VACIA = { usuario_id: '', tipo_evento: 'SALIDA', fecha: '', hora: '', hora_fin: '', motivo: '' };

function motivoDeBloqueo(tipo, estado) {
  if (tipo === 'ENTRADA') return estado === 'EN_DESCANSO' ? 'Estás en descanso' : 'Ya tienes un turno abierto';
  if (estado === 'SIN_TURNO' || estado === 'TURNO_CERRADO') return 'Primero marca tu entrada';
  if (estado === 'EN_DESCANSO') return 'Primero marca el fin del descanso';
  return 'Todavía no iniciaste un descanso';
}

export default function AsistenciaFichajeView() {
  const { user, tienePermiso, isAdmin } = useAuth();
  const [jornadas, setJornadas] = useState([]);
  const [correccion, setCorreccion] = useState(null);
  const [errorCorreccion, setErrorCorreccion] = useState('');
  const [guardandoCorreccion, setGuardandoCorreccion] = useState(false);
  const [anulacion, setAnulacion] = useState(null);
  const [errorAnulacion, setErrorAnulacion] = useState('');
  const puedeFichar = tienePermiso('ASISTENCIA_FICHAR');
  const [turno, setTurno] = useState(null);
  const [asistencias, setAsistencias] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filtros de supervisión
  const [selectedUsuarioId, setSelectedUsuarioId] = useState('');
  const [fechaFiltro, setFechaFiltro] = useState(aFechaLocal());
  const [observacion, setObservacion] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams(fechaFiltro ? periodoDelDia(fechaFiltro) : {});
      if (selectedUsuarioId) params.set('usuario_id', selectedUsuarioId);
      const query = params.toString() ? `?${params}` : '';

      // Sin permiso para ver a todo el personal, cada empleado consulta solo sus fichajes
      const [asistRes, userRes] = await Promise.all([
        api.getAsistencias(query),
        tienePermiso('USUARIOS_MANAGE') ? api.getUsuarios() : [],
      ]);

      setAsistencias(Array.isArray(asistRes) ? asistRes : []);
      setUsuarios(Array.isArray(userRes) ? userRes : []);
    } catch (err) {
      setError(err.message || 'Error cargando asistencias');
    } finally {
      setLoading(false);
    }
  };

  const cargarJornadas = async () => {
    if (!isAdmin) return;
    try {
      setJornadas(await api.getJornadasSinSalida());
    } catch (err) {
      setError(err.message || 'No se pudieron consultar las jornadas sin salida');
    }
  };

  useEffect(() => { cargarJornadas(); }, []);

  const abrirCorreccion = (datos = {}) => {
    setErrorCorreccion('');
    setCorreccion({ ...CORRECCION_VACIA, fecha: aFechaLocal(), ...datos });
  };

  const guardarCorreccion = async (e) => {
    e.preventDefault();
    setErrorCorreccion('');
    setGuardandoCorreccion(true);
    try {
      await api.corregirMarcaje({
        usuario_id: correccion.usuario_id,
        tipo_evento: correccion.tipo_evento,
        fecha_hora: new Date(`${correccion.fecha}T${correccion.hora}:00`).toISOString(),
        motivo: correccion.motivo,
        ...(correccion.tipo_evento === 'INICIO_DESCANSO' && correccion.hora_fin
          ? { fecha_hora_fin: new Date(`${correccion.fecha}T${correccion.hora_fin}:00`).toISOString() }
          : {}),
      });
      const { fecha } = correccion;
      setCorreccion(null);
      setSuccess('Corrección registrada');
      setTimeout(() => setSuccess(''), 3000);
      // Se muestra el día corregido para que se vea el resultado
      if (fecha === fechaFiltro) loadData();
      else setFechaFiltro(fecha);
      cargarJornadas();
      cargarTurno();
    } catch (err) {
      setErrorCorreccion(err.message || 'No se pudo registrar la corrección');
    } finally {
      setGuardandoCorreccion(false);
    }
  };

  const guardarAnulacion = async (e) => {
    e.preventDefault();
    setErrorAnulacion('');
    try {
      await api.anularMarcaje(anulacion.registro.id, anulacion.motivo);
      setAnulacion(null);
      setSuccess('Marcaje anulado');
      setTimeout(() => setSuccess(''), 3000);
      loadData();
      cargarJornadas();
      cargarTurno();
    } catch (err) {
      setErrorAnulacion(err.message || 'No se pudo anular el marcaje');
    }
  };

  const cargarTurno = async () => {
    try {
      setTurno(await api.getEstadoFichaje());
    } catch (err) {
      setError(err.message || 'No se pudo consultar tu turno');
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedUsuarioId, fechaFiltro]);

  useEffect(() => {
    cargarTurno();
    // También se puede marcar desde el acceso rápido de la barra superior
    const actualizar = () => {
      cargarTurno();
      loadData();
    };
    window.addEventListener('fichaje-registrado', actualizar);
    return () => window.removeEventListener('fichaje-registrado', actualizar);
  }, [selectedUsuarioId, fechaFiltro]);

  const handleFichar = async (tipo_evento) => {
    setSubmitting(true);
    setError('');
    try {
      await api.fichar(tipo_evento, observacion);
      setSuccess(`Marcaje de ${NOMBRES_EVENTO[tipo_evento]} registrado correctamente`);
      setObservacion('');
      setTimeout(() => setSuccess(''), 3000);
      loadData();
    } catch (err) {
      setError(err.message || 'Error al registrar marcaje');
    } finally {
      // También tras un rechazo: pudo marcarse desde otra pantalla
      cargarTurno();
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Control de Asistencia & Fichaje Horario</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            Registro de jornada de doctores y personal clínico con trazabilidad de IP
          </p>
        </div>
        {isAdmin && (
          <button
            type="button"
            onClick={() => abrirCorreccion()}
            className="self-start sm:self-auto px-4 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap"
          >
            <Pencil className="w-3.5 h-3.5" />
            Corregir Marcaje
          </button>
        )}
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Panel Superior: Botonera de Marcaje 1-Click para el Usuario Conectado */}
      <div className="bg-gradient-to-r from-slate-100 to-white dark:from-slate-900 dark:to-slate-800 border border-slate-200 dark:border-slate-700/80 rounded-2xl p-6 shadow-md dark:shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <span className="text-xs font-bold text-primary-600 dark:text-primary-400 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-4 h-4" /> Marcador Digital
            </span>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
              {user?.nombre_completo || user?.username}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Solo se habilitan los marcajes que corresponden a tu turno.
            </p>
            {turno && (
              <span data-testid="estado-turno" className={`inline-block mt-2 px-2.5 py-1 rounded-full text-[11px] font-bold border ${ESTADOS_TURNO[turno.estado].clase}`}>
                {ESTADOS_TURNO[turno.estado].texto}
                {turno.desde && ` · ${turno.estado === 'TURNO_CERRADO' ? 'a las' : 'desde las'} ${new Date(turno.desde).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
              </span>
            )}
            {turno?.jornada_sin_salida && (
              <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                Tu jornada del {new Date(`${turno.jornada_sin_salida}T00:00:00`).toLocaleDateString()} quedó sin salida. Avisa al administrador.
              </p>
            )}
          </div>

          <div className="w-full md:w-auto">
            <input
              type="text"
              placeholder="Observación o nota opcional..."
              value={observacion}
              onChange={(e) => setObservacion(e.target.value)}
              className="w-full md:w-64 px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 text-xs mb-3 focus:outline-none focus:border-primary-500"
            />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {BOTONES_MARCAJE.map(({ tipo, texto, Icono, clase }) => {
                const permitido = puedeFichar && Boolean(turno?.permitidos.includes(tipo));
                return (
                  <button
                    key={tipo}
                    type="button"
                    disabled={submitting || !permitido}
                    title={!permitido && turno ? motivoDeBloqueo(tipo, turno.estado) : undefined}
                    onClick={() => handleFichar(tipo)}
                    className={`${clase} px-3 py-2.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg`}
                  >
                    <Icono className="w-4 h-4" /> {texto}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {jornadas.length > 0 && (
        <section aria-label="Jornadas sin salida" className="bg-amber-50 dark:bg-amber-500/10 border border-amber-300 dark:border-amber-500/30 rounded-2xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            Jornadas sin salida ({jornadas.length})
          </h2>
          <ul className="divide-y divide-amber-200 dark:divide-amber-500/20">
            {jornadas.map((j) => (
              <li key={`${j.usuario_id}-${j.fecha}`} className="py-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-700 dark:text-slate-300">
                <span>
                  <strong className="text-slate-900 dark:text-white">{j.empleado_nombre}</strong>
                  {' · '}
                  {new Date(`${j.fecha}T00:00:00`).toLocaleDateString()}
                  {' · Último marcaje: '}
                  {NOMBRES_EVENTO[j.ultimo_evento]} a las {new Date(j.ultima_hora).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <button
                  type="button"
                  onClick={() => abrirCorreccion({ usuario_id: j.usuario_id, fecha: j.fecha, tipo_evento: j.ultimo_evento === 'INICIO_DESCANSO' ? 'FIN_DESCANSO' : 'SALIDA' })}
                  className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-500/40 text-amber-800 dark:text-amber-300 rounded-lg font-semibold"
                >
                  Corregir
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Supervisión y Filtros */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          <input
            type="date"
            value={fechaFiltro}
            onChange={(e) => setFechaFiltro(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold"
          />
        </div>

        <div
          className="flex items-center gap-2"
          style={usuarios.length > 0 ? undefined : { display: 'none' }}
        >
          <Users className="w-4 h-4 text-teal-600 dark:text-teal-400" />
          <select
            value={selectedUsuarioId}
            onChange={(e) => setSelectedUsuarioId(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold"
          >
            <option value="">Todo el Personal</option>
            {usuarios.map((u) => (
              <option key={u.id} value={u.id}>
                {`${u.nombre || ''} ${u.apellido || ''}`.trim() || u.username} ({u.rol?.nombre})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Historial de Marcajes */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <span>Bitácora de Marcajes ({asistencias.length >= LIMITE_LISTADO ? `primeros ${LIMITE_LISTADO}` : asistencias.length} registros)</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-normal">
            Fecha: {fechaFiltro || 'Todas las fechas'}
          </span>
        </h2>

        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Cargando bitácora de asistencia...</div>
        ) : asistencias.length === 0 ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs">
            No hay registros de marcaje para los filtros seleccionados.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 dark:bg-slate-900/60 text-slate-700 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Hora</th>
                  <th className="py-3 px-4">Empleado</th>
                  <th className="py-3 px-4">Rol</th>
                  <th className="py-3 px-4 text-center">Tipo Evento</th>
                  <th className="py-3 px-4">IP / Origen</th>
                  <th className="py-3 px-4">Observaciones</th>
                  {isAdmin && <th className="py-3 px-4"><span className="sr-only">Acciones</span></th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {asistencias.map((a) => {
                  const empNombre = a.empleado_nombre || 'Personal';
                  const horaStr = a.fecha_hora ? new Date(a.fecha_hora).toLocaleTimeString() : '--:--';

                  const badgeClass =
                    a.tipo_evento === 'ENTRADA'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : a.tipo_evento === 'SALIDA'
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400';

                  return (
                    <tr key={a.id} className={`hover:bg-slate-50 dark:hover:bg-slate-700/20 transition ${a.anulado ? 'opacity-60' : ''}`}>
                      <td className={`py-3 px-4 font-mono font-bold text-primary-600 dark:text-primary-400 ${a.anulado ? 'line-through' : ''}`}>{horaStr}</td>
                      <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">{empNombre}</td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">{a.empleado_rol || '-'}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                          {NOMBRES_EVENTO[a.tipo_evento] || a.tipo_evento}
                        </span>
                        {a.es_correccion && (
                          <span className="block mt-1 text-[10px] font-bold text-amber-700 dark:text-amber-400">Corregido</span>
                        )}
                        {a.anulado && (
                          <span className="block mt-1 text-[10px] font-bold text-rose-700 dark:text-rose-400">Anulado</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400">{a.ip_registro || '-'}</td>
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 italic">
                        {a.es_correccion ? `${a.motivo_correccion} (registró ${a.corregido_por_nombre || 'administrador'})` : a.observaciones || '-'}
                        {a.anulado && (
                          <span className="block not-italic text-rose-700 dark:text-rose-400">
                            Anulado: {a.motivo_anulacion} ({a.anulado_por_nombre || 'administrador'})
                          </span>
                        )}
                      </td>
                      {isAdmin && (
                        <td className="py-3 px-4 text-right">
                          {!a.anulado && (
                            <button
                              type="button"
                              onClick={() => { setErrorAnulacion(''); setAnulacion({ registro: a, motivo: '' }); }}
                              className="text-xs font-semibold text-rose-600 dark:text-rose-400 hover:underline"
                            >
                              Anular
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {correccion && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div role="dialog" aria-label="Corregir marcaje" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Corregir Marcaje</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Agrega un marcaje olvidado. Los marcajes existentes no cambian, y este queda identificado como corrección.
            </p>
            <form onSubmit={guardarCorreccion} className="space-y-4">
              <ErrorModal mensaje={errorCorreccion} />
              <div>
                <label htmlFor="cor-empleado" className={ETIQUETA}>Empleado *</label>
                <select id="cor-empleado" required value={correccion.usuario_id} onChange={(e) => setCorreccion({ ...correccion, usuario_id: e.target.value })} className={CAMPO}>
                  <option value="">Selecciona a la persona</option>
                  {usuarios.map((u) => (
                    <option key={u.id} value={u.id}>{`${u.nombre || ''} ${u.apellido || ''}`.trim() || u.username}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="cor-tipo" className={ETIQUETA}>Marcaje *</label>
                <select id="cor-tipo" value={correccion.tipo_evento} onChange={(e) => setCorreccion({ ...correccion, tipo_evento: e.target.value })} className={CAMPO}>
                  {Object.entries(NOMBRES_EVENTO).map(([tipo, nombre]) => <option key={tipo} value={tipo}>{nombre}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="cor-fecha" className={ETIQUETA}>Fecha *</label>
                  <input id="cor-fecha" type="date" required max={aFechaLocal()} value={correccion.fecha} onChange={(e) => setCorreccion({ ...correccion, fecha: e.target.value })} className={CAMPO} />
                </div>
                <div>
                  <label htmlFor="cor-hora" className={ETIQUETA}>Hora real *</label>
                  <input id="cor-hora" type="time" required value={correccion.hora} onChange={(e) => setCorreccion({ ...correccion, hora: e.target.value })} className={CAMPO} />
                </div>
              </div>
              {correccion.tipo_evento === 'INICIO_DESCANSO' && (
                <div>
                  <label htmlFor="cor-hora-fin" className={ETIQUETA}>Hora de fin del descanso</label>
                  <input id="cor-hora-fin" type="time" value={correccion.hora_fin} onChange={(e) => setCorreccion({ ...correccion, hora_fin: e.target.value })} className={CAMPO} />
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Indícala si el turno ya continuó después del descanso.</p>
                </div>
              )}
              <div>
                <label htmlFor="cor-motivo" className={ETIQUETA}>Motivo *</label>
                <textarea id="cor-motivo" rows="2" required maxLength={500} placeholder="Ej. Olvidó marcar la salida" value={correccion.motivo} onChange={(e) => setCorreccion({ ...correccion, motivo: e.target.value })} className={CAMPO} />
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => setCorreccion(null)} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
                <button type="submit" disabled={guardandoCorreccion} className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold">
                  {guardandoCorreccion ? 'Guardando...' : 'Guardar Corrección'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {anulacion && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div role="dialog" aria-label="Anular marcaje" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Anular Marcaje</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              {NOMBRES_EVENTO[anulacion.registro.tipo_evento]} de {anulacion.registro.empleado_nombre} del {new Date(anulacion.registro.fecha_hora).toLocaleString()}.
              Dejará de contar, pero seguirá visible en la bitácora. Para corregir una hora, anúlalo y agrega el marcaje correcto.
            </p>
            <form onSubmit={guardarAnulacion} className="space-y-4">
              <ErrorModal mensaje={errorAnulacion} />
              <div>
                <label htmlFor="anu-motivo" className={ETIQUETA}>Motivo *</label>
                <textarea id="anu-motivo" rows="2" required maxLength={500} value={anulacion.motivo} onChange={(e) => setAnulacion({ ...anulacion, motivo: e.target.value })} className={CAMPO} />
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => setAnulacion(null)} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold">Anular Marcaje</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
