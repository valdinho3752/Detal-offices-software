import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
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
} from 'lucide-react';

export default function AsistenciaFichajeView() {
  const { user, tienePermiso } = useAuth();
  const [asistencias, setAsistencias] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filtros de supervisión
  const [selectedUsuarioId, setSelectedUsuarioId] = useState('');
  const [fechaFiltro, setFechaFiltro] = useState(new Date().toISOString().split('T')[0]);
  const [observacion, setObservacion] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      let query = '';
      const params = [];
      if (selectedUsuarioId) params.push(`usuario_id=${selectedUsuarioId}`);
      if (fechaFiltro) params.push(`fecha=${fechaFiltro}`);
      if (params.length > 0) query = `?${params.join('&')}`;

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

  useEffect(() => {
    loadData();
  }, [selectedUsuarioId, fechaFiltro]);

  const handleFichar = async (tipo_evento) => {
    setSubmitting(true);
    setError('');
    try {
      await api.fichar(tipo_evento, observacion);
      setSuccess(`Marcaje de ${tipo_evento} registrado correctamente`);
      setObservacion('');
      setTimeout(() => setSuccess(''), 3000);
      loadData();
    } catch (err) {
      setError(err.message || 'Error al registrar marcaje');
    } finally {
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
            Registro de jornada de doctores y personal clínico con trazabilidad de IP (HU-06)
          </p>
        </div>
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
              <Clock className="w-4 h-4" /> Marcador Biométrico / Digital
            </span>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
              {user?.nombre_completo || user?.username}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Presiona el botón correspondiente para registrar el inicio, descanso o fin de tu turno laboral.
            </p>
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
              <button
                disabled={submitting}
                onClick={() => handleFichar('ENTRADA')}
                className="px-3 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/20"
              >
                <LogIn className="w-4 h-4" /> Entrada
              </button>
              <button
                disabled={submitting}
                onClick={() => handleFichar('INICIO_DESCANSO')}
                className="px-3 py-2.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-amber-600/20"
              >
                <Coffee className="w-4 h-4" /> Descanso
              </button>
              <button
                disabled={submitting}
                onClick={() => handleFichar('FIN_DESCANSO')}
                className="px-3 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-sky-600/20"
              >
                <Coffee className="w-4 h-4" /> Fin Descanso
              </button>
              <button
                disabled={submitting}
                onClick={() => handleFichar('SALIDA')}
                className="px-3 py-2.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-rose-600/20"
              >
                <LogOut className="w-4 h-4" /> Salida
              </button>
            </div>
          </div>
        </div>
      </div>

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
          <span>Bitácora de Marcajes ({asistencias.length} registros)</span>
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
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {asistencias.map((a) => {
                  const empNombre = a.usuario?.nombre_completo || a.usuario?.username || 'Personal';
                  const horaStr = a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : '--:--';

                  const badgeClass =
                    a.tipo_evento === 'ENTRADA'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : a.tipo_evento === 'SALIDA'
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400';

                  return (
                    <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/20 transition">
                      <td className="py-3 px-4 font-mono font-bold text-primary-600 dark:text-primary-400">{horaStr}</td>
                      <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">{empNombre}</td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">{a.usuario?.rol?.nombre || 'General'}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                          {a.tipo_evento}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400">{a.ip_address || '127.0.0.1'}</td>
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 italic">{a.observaciones || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
