import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { api } from '../services/api';
import { aFechaLocal } from '../utils/fechas';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  Plus,
  Truck,
  CheckCircle2,
  Clock,
  AlertCircle,
  Calendar,
  Banknote,
  Filter,
  User,
  Sparkles,
  Shield,
  Stethoscope,
} from 'lucide-react';
import PacienteSearchInput from '../components/PacienteSearchInput';
import { useMoneda } from '../context/MonedaContext';

const COLORES_VITA = [
  'A1', 'A2', 'A3', 'A3.5', 'A4',
  'B1', 'B2', 'B3', 'B4',
  'C1', 'C2', 'C3', 'C4',
  'D2', 'D3', 'D4',
  'BLEACH_BL1', 'BLEACH_BL2'
];

const ETIQUETAS_ESTADO = {
  ENVIADO: 'Enviado',
  EN_LABORATORIO: 'En proceso',
  RECIBIDO_EN_CLINICA: 'Recibido',
  PRUEBA_EN_BOCA: 'Prueba en boca',
  AJUSTE_REPETICION: 'Ajuste',
  INSTALADO_FINALIZADO: 'Instalado',
  CANCELADO: 'Cancelado',
};

export default function ProtesisLaboratorioView() {
  const { moneda, simbolo } = useMoneda();
  const { user, tienePermiso } = useAuth();
  const [protesis, setProtesis] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [doctores, setDoctores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filtros
  const [filtroEstado, setFiltroEstado] = useState('');

  // Modal nueva orden
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    paciente_id: '',
    doctor_id: '',
    laboratorio_nombre: '',
    tipo_trabajo: 'CORONA_ZIRCONIO',
    color_vita: 'A2',
    pieza_fdi: '',
    costo_laboratorio: 50,
    costo_paciente: 150,
    fecha_envio: aFechaLocal(),
    fecha_prometida_entrega: '',
    instrucciones: '',
  });

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      let query = '';
      if (filtroEstado) query = `?estado=${filtroEstado}`;

      const [prRes, pacRes, docRes] = await Promise.all([
        api.getProtesis(query),
        api.getPacientes('', 0, 100),
        api.getDoctores(),
      ]);

      setProtesis(Array.isArray(prRes) ? prRes : []);
      setPacientes(Array.isArray(pacRes) ? pacRes : []);
      setDoctores(Array.isArray(docRes) ? docRes : []);
    } catch (err) {
      setError(err.message || 'Error cargando prótesis');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filtroEstado]);

  useEffect(() => {
    if (user?.doctor_id) {
      setForm((prev) => ({ ...prev, doctor_id: user.doctor_id }));
    } else if (doctores.length > 0 && !form.doctor_id) {
      setForm((prev) => ({ ...prev, doctor_id: doctores[0].id }));
    }
  }, [user, doctores]);

  const handleUpdateEstado = async (id, nuevoEstado) => {
    try {
      const payload = { estado: nuevoEstado };
      if (nuevoEstado === 'RECIBIDO_EN_CLINICA') {
        payload.fecha_recepcion_real = aFechaLocal();
      }
      await api.updateProtesis(id, payload);
      setSuccess(`Estado actualizado a ${nuevoEstado}`);
      setTimeout(() => setSuccess(''), 3000);
      loadData();
    } catch (err) {
      setError(err.message || 'Error al actualizar estado');
    }
  };

  const handleCreateProtesis = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.createProtesis({
        paciente_id: form.paciente_id,
        doctor_id: form.doctor_id,
        laboratorio_nombre: form.laboratorio_nombre,
        tipo_trabajo: form.tipo_trabajo,
        piezas_dentales: form.pieza_fdi ? `Pieza ${form.pieza_fdi}` : 'General / Múltiple',
        pieza_fdi: form.pieza_fdi ? parseInt(form.pieza_fdi) : null,
        color_guia_vita: form.color_vita || 'A2',
        color_vita: form.color_vita || 'A2',
        instrucciones_tecnicas: form.instrucciones || '',
        costo_laboratorio: Number(form.costo_laboratorio),
        costo_paciente: Number(form.costo_paciente),
        fecha_envio: form.fecha_envio || aFechaLocal(),
        fecha_entrega_esperada: form.fecha_prometida_entrega || aFechaLocal(new Date(Date.now() + 7*86400000)),
        observaciones: form.observaciones || '',
      });

      setSuccess('Orden de prótesis enviada a laboratorio exitosamente');
      setShowModal(false);
      setTimeout(() => setSuccess(''), 3000);
      loadData();
    } catch (err) {
      setError(err.message || 'Error al crear orden');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Prótesis & Laboratorios Dentales</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            Control de órdenes de coronas, prótesis, guía de color Vita y fechas de entrega prometidas
          </p>
        </div>
        <button
          style={tienePermiso('PROTESIS_CREATE') ? undefined : { display: 'none' }}
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20"
        >
          <Plus className="w-4 h-4" />
          Nueva Orden de Laboratorio
        </button>
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
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-4 flex items-center gap-3">
        <Filter className="w-4 h-4 text-slate-500 dark:text-slate-400" />
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Estado de la Orden:</span>
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value)}
          className="px-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold"
        >
          <option value="">Todos los Estados</option>
          <option value="ENVIADO">Enviado al Laboratorio</option>
          <option value="EN_LABORATORIO">En Proceso / Fabricación</option>
          <option value="RECIBIDO_EN_CLINICA">Recibido en Clínica</option>
          <option value="PRUEBA_EN_BOCA">Prueba en Boca</option>
          <option value="AJUSTE_REPETICION">Ajuste / Repetición</option>
          <option value="INSTALADO_FINALIZADO">Instalado en Paciente</option>
          <option value="CANCELADO">Cancelado</option>
        </select>
      </div>

      {/* Tabla / Tarjetas de Órdenes */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <span>Órdenes de Trabajo Activas ({protesis.length})</span>
        </h2>

        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Cargando órdenes de prótesis...</div>
        ) : protesis.length === 0 ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs">
            No hay órdenes de prótesis registradas.{' '}
            <button onClick={() => setShowModal(true)} className="text-primary-600 dark:text-primary-400 hover:underline font-semibold">
              Crear orden ahora
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 dark:bg-slate-900/60 text-slate-700 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Paciente / Doctor</th>
                  <th className="py-3 px-4">Laboratorio</th>
                  <th className="py-3 px-4">Trabajo & Pieza</th>
                  <th className="py-3 px-4 text-center">Color Vita</th>
                  <th className="py-3 px-4 text-center">Entrega Prometida</th>
                  <th className="py-3 px-4 text-right">Costo Lab</th>
                  <th className="py-3 px-4 text-center">Estado</th>
                  <th className="py-3 px-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40 text-slate-300">
                {protesis.map((p) => {
                  const pacNombre = p.paciente ? `${p.paciente.nombres} ${p.paciente.apellidos}` : 'Paciente';
                  const docNombre = p.doctor ? p.doctor.nombre_completo || p.doctor.username : 'Doctor';

                  return (
                    <tr key={p.id} className="hover:bg-slate-700/20 transition">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{pacNombre}</div>
                        <div className="text-[11px] text-slate-400">Dr(a). {docNombre}</div>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-200">
                        {p.laboratorio_nombre || 'Laboratorio Dental'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-primary-700 dark:text-primary-300">{p.tipo_trabajo}</span>
                        {p.piezas_dentales && (
                          <div className="text-[10px] font-mono text-slate-400">{p.piezas_dentales}</div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 rounded font-mono font-bold text-[11px]">
                          {p.color_guia_vita || 'N/A'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-slate-300">
                        {p.fecha_entrega_esperada ? p.fecha_entrega_esperada.slice(0, 10) : 'Pendiente'}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">
                        {moneda(p.costo_laboratorio)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                            p.estado === 'RECIBIDO_EN_CLINICA'
                              ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                              : p.estado === 'INSTALADO_FINALIZADO'
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                              : p.estado === 'AJUSTE_REPETICION' || p.estado === 'CANCELADO'
                              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                              : 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400'
                          }`}
                        >
                          {ETIQUETAS_ESTADO[p.estado] || p.estado}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-1">
                        {tienePermiso('PROTESIS_UPDATE') && p.estado === 'ENVIADO' && (
                          <button
                            onClick={() => handleUpdateEstado(p.id, 'EN_LABORATORIO')}
                            className="px-2 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-800 dark:text-amber-300 border border-amber-500/30 rounded text-[11px] transition"
                          >
                            En Proceso
                          </button>
                        )}
                        {tienePermiso('PROTESIS_UPDATE') && ['ENVIADO', 'EN_LABORATORIO', 'AJUSTE_REPETICION'].includes(p.estado) && (
                          <button
                            onClick={() => handleUpdateEstado(p.id, 'RECIBIDO_EN_CLINICA')}
                            className="px-2 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-700 dark:text-blue-300 border border-blue-500/30 rounded text-[11px] transition"
                          >
                            Recibir en Clínica
                          </button>
                        )}
                        {tienePermiso('PROTESIS_UPDATE') && p.estado === 'RECIBIDO_EN_CLINICA' && (
                          <button
                            onClick={() => handleUpdateEstado(p.id, 'PRUEBA_EN_BOCA')}
                            className="px-2 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-800 dark:text-amber-300 border border-amber-500/30 rounded text-[11px] transition"
                          >
                            Prueba en Boca
                          </button>
                        )}
                        {tienePermiso('PROTESIS_UPDATE') && p.estado === 'PRUEBA_EN_BOCA' && (
                          <button
                            onClick={() => handleUpdateEstado(p.id, 'AJUSTE_REPETICION')}
                            className="px-2 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-800 dark:text-amber-300 border border-amber-500/30 rounded text-[11px] transition"
                          >
                            Requiere Ajuste
                          </button>
                        )}
                        {tienePermiso('PROTESIS_UPDATE') && ['RECIBIDO_EN_CLINICA', 'PRUEBA_EN_BOCA'].includes(p.estado) && (
                          <button
                            onClick={() => handleUpdateEstado(p.id, 'INSTALADO_FINALIZADO')}
                            className="px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-[11px] transition"
                          >
                            Colocado
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Nueva Orden */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Nueva Orden para Laboratorio Dental</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Ingresa los detalles técnicos, guía de color y fechas para el laboratorio.
            </p>

            <form onSubmit={handleCreateProtesis} className="space-y-4">
              <ErrorModal mensaje={error} />
              <PacienteSearchInput
                label="Paciente"
                required
                pacientes={pacientes}
                selectedPacienteId={form.paciente_id}
                onSelectPaciente={(newPid) => setForm({ ...form, paciente_id: newPid })}
                placeholder="Buscar paciente por nombre o CI..."
              />

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Doctor Solicitante *</label>
                {user?.puedeElegirDoctor ? (
                  <select
                    required
                    value={form.doctor_id}
                    onChange={(e) => setForm({ ...form, doctor_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold"
                  >
                    <option value="">-- Seleccionar Doctor --</option>
                    {doctores.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        Dr(a). {doc.nombre_completo || doc.username} {doc.especialidad ? `(${doc.especialidad})` : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 rounded-xl text-slate-900 dark:text-white text-xs">
                    <span className="font-semibold text-teal-600 dark:text-teal-400 flex items-center gap-2">
                      <Stethoscope className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                      Dr(a). {doctores.find((d) => d.id === user?.doctor_id)?.nombre_completo || user?.username} (Tú)
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <Shield className="w-3.5 h-3.5 text-slate-400" /> Bloqueado a tu perfil
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Laboratorio Dental *</label>
                  <input
                    type="text"
                    required
                    placeholder="ej. Lab Dental Cerámicas & Cía"
                    value={form.laboratorio_nombre}
                    onChange={(e) => setForm({ ...form, laboratorio_nombre: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo de Trabajo *</label>
                  <input
                    type="text"
                    required
                    placeholder="ej. Corona Zirconio, Incrustación E-max"
                    value={form.tipo_trabajo}
                    onChange={(e) => setForm({ ...form, tipo_trabajo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Guía de Color Vita *</label>
                  <select
                    value={form.color_vita}
                    onChange={(e) => setForm({ ...form, color_vita: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono font-bold"
                  >
                    {COLORES_VITA.map((col) => (
                      <option key={col} value={col}>
                        Color {col}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Pieza FDI</label>
                  <input
                    type="number"
                    placeholder="ej. 16, 21"
                    value={form.pieza_fdi}
                    onChange={(e) => setForm({ ...form, pieza_fdi: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Costo Laboratorio ({simbolo}) *</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={form.costo_laboratorio}
                    onChange={(e) => setForm({ ...form, costo_laboratorio: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Fecha Entrega Prometida</label>
                  <input
                    type="date"
                    value={form.fecha_prometida_entrega}
                    onChange={(e) => setForm({ ...form, fecha_prometida_entrega: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Instrucciones Técnicas</label>
                <textarea
                  rows="2"
                  placeholder="Hombro cerámico vestibular, oclusión en céntrica, anatomía suave..."
                  value={form.instrucciones}
                  onChange={(e) => setForm({ ...form, instrucciones: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Generar Orden
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
