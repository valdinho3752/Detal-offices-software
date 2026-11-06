import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  ShieldAlert,
  Search,
  Filter,
  Eye,
  Calendar,
  User,
  Clock,
  Layers,
  FileCode,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { verFechaHora } from '../utils/fechas';

export default function AuditoriaForenseView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filtros
  const [tablaFiltro, setTablaFiltro] = useState('');
  const [accionFiltro, setAccionFiltro] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const loadLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const params = [];
      if (tablaFiltro) params.push(`tabla=${tablaFiltro}`);
      if (accionFiltro) params.push(`accion=${accionFiltro}`);
      const query = params.length > 0 ? `?${params.join('&')}` : '';

      const data = await api.getAuditoria(query);
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Error cargando bitácora de auditoría');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [tablaFiltro, accionFiltro]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Auditoría Forense & Trazabilidad</h1>
          <p className="text-slate-400 text-sm">
            Bitácora inmutable de seguridad con inspección de cambios JSONB antes y después
          </p>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Filtros */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary-400" />
          <span className="text-xs font-semibold text-slate-300">Tabla / Entidad:</span>
          <select
            value={tablaFiltro}
            onChange={(e) => setTablaFiltro(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs font-semibold"
          >
            <option value="">Todas las Tablas</option>
            <option value="pacientes">Pacientes</option>
            <option value="antecedentes_medicos">Antecedentes médicos</option>
            <option value="citas">Citas</option>
            <option value="odontogramas">Odontogramas</option>
            <option value="visitas_evolucion">Evoluciones</option>
            <option value="observaciones_evolucion">Observaciones de evolución</option>
            <option value="radiografias_estudios">Radiografías</option>
            <option value="ordenes_laboratorio_protesis">Prótesis y laboratorio</option>
            <option value="cajas_sesiones">Cajas y arqueos</option>
            <option value="egresos_caja">Egresos de caja</option>
            <option value="pagos">Pagos de pacientes</option>
            <option value="cobros_cita">Cuentas de citas</option>
            <option value="pagos_empleados">Pagos al personal</option>
            <option value="registro_asistencia">Marcajes de asistencia</option>
            <option value="catalogo_tratamientos">Catálogo de tratamientos</option>
            <option value="sillones">Sillones</option>
            <option value="configuracion_clinica">Configuración</option>
            <option value="usuarios">Usuarios</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-teal-400" />
          <span className="text-xs font-semibold text-slate-300">Acción:</span>
          <select
            value={accionFiltro}
            onChange={(e) => setAccionFiltro(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs font-semibold"
          >
            <option value="">Todas las Acciones</option>
            <option value="INSERT">INSERT (Creación)</option>
            <option value="UPDATE">UPDATE (Modificación)</option>
            <option value="DELETE">DELETE (Eliminación)</option>
            <option value="VIEW">VIEW (Lectura Confidencial)</option>
          </select>
        </div>
      </div>

      {/* Lista de Registros de Auditoría */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
        <h2 className="text-base font-semibold text-white flex items-center justify-between pb-3 border-b border-slate-700/60">
          <span>Eventos de Auditoría Registrados ({logs.length})</span>
        </h2>

        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Cargando registros forenses...</div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No se encontraron eventos de auditoría para los filtros indicados.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Usuario</th>
                  <th className="py-3 px-4">Tabla / Módulo</th>
                  <th className="py-3 px-4 text-center">Acción</th>
                  <th className="py-3 px-4">IP / Origen</th>
                  <th className="py-3 px-4 text-right">Detalle JSONB</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40 text-slate-300">
                {logs.map((log) => {
                  const badgeClass =
                    log.accion === 'INSERT'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : log.accion === 'UPDATE'
                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                      : log.accion === 'DELETE'
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                      : 'bg-slate-800 border-slate-700 text-slate-400';

                  return (
                    <tr key={log.id} className="hover:bg-slate-700/20 transition">
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {verFechaHora(log.fecha_hora)}
                      </td>
                      <td className="py-3 px-4 font-semibold text-white">
                        {log.usuario_nombre || 'Sistema'}
                      </td>
                      <td className="py-3 px-4 font-mono text-primary-700 dark:text-primary-300">{log.tabla_afectada}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                          {log.accion}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">{log.ip_origen || 'Sin registro'}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-xs transition flex items-center gap-1.5 ml-auto"
                        >
                          <Eye className="w-3.5 h-3.5 text-primary-400" /> Inspeccionar Diff
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Visor de Diferencias JSONB */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl p-6 shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-rose-400" />
                  Inspección Forense de Modificación
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Tabla: <span className="text-primary-400 font-mono">{selectedLog.tabla_afectada}</span> · Registro ID:{' '}
                  <span className="text-white font-mono">{selectedLog.registro_id}</span>
                </p>
              </div>

              <button
                onClick={() => setSelectedLog(null)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold"
              >
                Cerrar
              </button>
            </div>

            {/* Comparativa JSONB: Antes vs Después */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4 flex-1 overflow-hidden">
              {/* Datos Previos */}
              <div className="flex flex-col bg-slate-950/80 border border-rose-500/30 rounded-xl p-3 overflow-hidden">
                <span className="text-xs font-bold text-rose-400 mb-2 uppercase tracking-wider">
                  [-] Datos Anteriores (Previos)
                </span>
                <div className="flex-1 overflow-y-auto">
                  <pre className="text-[11px] font-mono text-slate-300 whitespace-pre-wrap">
                    {selectedLog.datos_previos
                      ? JSON.stringify(selectedLog.datos_previos, null, 2)
                      : '// No existen datos previos (Registro Nuevo)'}
                  </pre>
                </div>
              </div>

              {/* Datos Nuevos */}
              <div className="flex flex-col bg-slate-950/80 border border-emerald-500/30 rounded-xl p-3 overflow-hidden">
                <span className="text-xs font-bold text-emerald-400 mb-2 uppercase tracking-wider">
                  [+] Datos Nuevos (Resultado)
                </span>
                <div className="flex-1 overflow-y-auto">
                  <pre className="text-[11px] font-mono text-emerald-300 whitespace-pre-wrap">
                    {selectedLog.datos_nuevos
                      ? JSON.stringify(selectedLog.datos_nuevos, null, 2)
                      : '// Registro eliminado o sin payload'}
                  </pre>
                </div>
              </div>
            </div>

            <div className="p-3 bg-slate-800/80 rounded-xl border border-slate-700 text-xs text-slate-400 flex items-center justify-between font-mono">
              <span>Usuario: {selectedLog.usuario_nombre || 'Desconocido'}</span>
              <span>IP: {selectedLog.ip_origen || 'Sin registro'}</span>
              <span>Fecha: {verFechaHora(selectedLog.fecha_hora)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
