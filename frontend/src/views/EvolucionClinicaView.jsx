import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  FileText,
  User,
  Plus,
  Pill,
  CheckCircle2,
  Calendar,
  AlertCircle,
  FileCheck,
  Sparkles,
  Printer,
  Shield,
  Stethoscope,
  Link as LinkIcon,
  Clock,
  Activity,
  Check,
  ChevronRight,
  Filter,
} from 'lucide-react';
import PacienteSearchInput from '../components/PacienteSearchInput';

export default function EvolucionClinicaView() {
  const { user, tienePermiso } = useAuth();
  const puedeObservar = tienePermiso('HISTORIA_CLINICA_OBSERVAR');
  const [observacionesNuevas, setObservacionesNuevas] = useState({});
  const [searchParams] = useSearchParams();
  const pacienteIdParam = searchParams.get('paciente_id');

  const [pacientes, setPacientes] = useState([]);
  const [selectedPacienteId, setSelectedPacienteId] = useState(pacienteIdParam || '');
  const [doctores, setDoctores] = useState([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [visitas, setVisitas] = useState([]);
  const [planes, setPlanes] = useState([]);
  const [citasPaciente, setCitasPaciente] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form nueva visita de evolución
  const [showModal, setShowModal] = useState(false);
  const [formVisita, setFormVisita] = useState({
    fecha_hora: new Date().toISOString().slice(0, 16),
    cita_id: '',
    motivo_consulta: '',
    observaciones_clinicas: '',
    diagnostico: '',
    procedimiento_realizado: '',
    item_plan_completado_id: '',
    item_plan_proxima_sesion_id: '',
    receta_medicamentos: '',
    indicaciones_postoperatorias: '',
  });

  // Filtros para vincular cita en el modal
  const [filtroFechaCita, setFiltroFechaCita] = useState('');
  const [filtroDoctorCita, setFiltroDoctorCita] = useState('');

  useEffect(() => {
    const loadDoctores = async () => {
      try {
        const docRes = await api.getDoctores();
        const list = Array.isArray(docRes) ? docRes : [];
        setDoctores(list);
        if (user?.doctor_id) {
          setSelectedDoctorId(user.doctor_id);
        } else if (list.length > 0) {
          setSelectedDoctorId(list[0].id);
        }
      } catch (err) {
        console.error('Error cargando doctores:', err);
      }
    };
    loadDoctores();
  }, [user]);

  useEffect(() => {
    const loadPacientes = async () => {
      try {
        const pRes = await api.getPacientes('', 0, 100);
        setPacientes(Array.isArray(pRes) ? pRes : []);
        if (pacienteIdParam) {
          setSelectedPacienteId(pacienteIdParam);
        } else if (pRes?.length > 0) {
          setSelectedPacienteId(pRes[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadPacientes();
  }, []);

  const loadVisitasYPlanes = async () => {
    if (!selectedPacienteId) return;
    setLoading(true);
    setError('');
    try {
      const [vRes, plRes, cRes] = await Promise.all([
        api.getVisitas(selectedPacienteId),
        api.getPlanes(selectedPacienteId),
        api.getCitas(`?paciente_id=${selectedPacienteId}`),
      ]);
      setVisitas(Array.isArray(vRes) ? vRes : []);
      setPlanes(Array.isArray(plRes) ? plRes : []);
      setCitasPaciente(Array.isArray(cRes) ? cRes : []);
    } catch (err) {
      setError(err.message || 'Error cargando evolución clínica');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVisitasYPlanes();
  }, [selectedPacienteId]);

  const handleCreateVisita = async (e) => {
    e.preventDefault();
    setError('');
    try {
      // La API actualiza los ítems del plan y el odontograma en la misma operación
      await api.createVisita({
        paciente_id: selectedPacienteId,
        doctor_id: selectedDoctorId || user?.doctor_id,
        cita_id: formVisita.cita_id || null,
        item_plan_id: formVisita.item_plan_completado_id || null,
        proximo_item_plan_id: formVisita.item_plan_proxima_sesion_id || null,
        fecha_hora: formVisita.fecha_hora ? new Date(formVisita.fecha_hora).toISOString() : new Date().toISOString(),
        motivo_consulta: formVisita.motivo_consulta,
        observaciones_clinicas: formVisita.observaciones_clinicas,
        diagnostico: formVisita.diagnostico || formVisita.observaciones_clinicas || 'Atención Odontológica',
        procedimiento_realizado: formVisita.procedimiento_realizado,
        receta_medicamentos: formVisita.receta_medicamentos,
        indicaciones_postoperatorias: formVisita.indicaciones_postoperatorias,
      });

      setSuccess('Evolución clínica, tratamientos sincronizados y receta registrados con éxito');
      setShowModal(false);
      setFormVisita({
        fecha_hora: new Date().toISOString().slice(0, 16),
        cita_id: '',
        motivo_consulta: '',
        observaciones_clinicas: '',
        diagnostico: '',
        procedimiento_realizado: '',
        item_plan_completado_id: '',
        item_plan_proxima_sesion_id: '',
        receta_medicamentos: '',
        indicaciones_postoperatorias: '',
      });
      setTimeout(() => setSuccess(''), 3000);
      loadVisitasYPlanes();
    } catch (err) {
      setError(err.message || 'Error al guardar evolución clínica');
    }
  };

  const handleAgregarObservacion = async (e, visitaId) => {
    e.preventDefault();
    const texto = (observacionesNuevas[visitaId] || '').trim();
    if (!texto) return;
    try {
      await api.agregarObservacionVisita(visitaId, texto);
      setObservacionesNuevas((prev) => ({ ...prev, [visitaId]: '' }));
      setSuccess('Observación agregada a la evolución');
      setTimeout(() => setSuccess(''), 3000);
      loadVisitasYPlanes();
    } catch (err) {
      setError(err.message || 'Error al agregar la observación');
    }
  };

  // Extraer todos los items de los planes del paciente
  const todosLosItems = [];
  planes.forEach((p) => {
    if (p.items) {
      p.items.forEach((it) => {
        todosLosItems.push(it);
      });
    }
  });

  const itemsPendientes = todosLosItems.filter((it) => it.estado !== 'COMPLETADO');

  // Filtrar citas del paciente para vincular en el modal
  const citasFiltradas = citasPaciente.filter((c) => {
    // Una cita cancelada no se atendió, y cada cita admite una sola evolución
    if (c.estado === 'CANCELADA' || visitas.some((v) => v.cita_id === c.id)) return false;
    if (filtroFechaCita) {
      const fechaC = c.fecha_inicio_programada ? c.fecha_inicio_programada.slice(0, 10) : '';
      if (fechaC !== filtroFechaCita) return false;
    }
    if (filtroDoctorCita && c.doctor_id !== filtroDoctorCita) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Evolución Clínica & Recetario Médico</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Registro cronológico de atención SOEP, sincronización con odontograma y prescripciones (HU-07)
          </p>
        </div>

        {/* Selectores de Paciente, Doctor y Botón Nueva Nota */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Selector de Paciente con Barra de Búsqueda */}
          <div className="w-full sm:w-72">
            <PacienteSearchInput
              pacientes={pacientes}
              selectedPacienteId={selectedPacienteId}
              onSelectPaciente={(id) => setSelectedPacienteId(id)}
              placeholder="Buscar paciente por nombre o CI..."
            />
          </div>

          {/* Selector de Doctor Asignado (Admin) / Badge Bloqueado (Doctor) */}
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2 rounded-xl shadow-sm">
            <Stethoscope className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            {user?.puedeElegirDoctor ? (
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold uppercase">Doctor:</span>
                <select
                  value={selectedDoctorId}
                  onChange={(e) => setSelectedDoctorId(e.target.value)}
                  className="bg-transparent text-slate-900 dark:text-white text-xs font-semibold focus:outline-none cursor-pointer"
                  title="Como Administrador puedes registrar notas a nombre de cualquier Doctor"
                >
                  {doctores.map((doc) => (
                    <option key={doc.id} value={doc.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                      Dr(a). {doc.nombre_completo || doc.username}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="flex items-center gap-1.5" title="Doctor asignado según tu perfil profesional">
                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold uppercase">Doctor:</span>
                <span className="text-slate-900 dark:text-white text-xs font-semibold">
                  Dr(a). {doctores.find((d) => d.id === user?.doctor_id)?.nombre_completo || user?.username || 'Tú'} (Tú)
                </span>
                <Shield className="w-3.5 h-3.5 text-slate-400 ml-1" />
              </div>
            )}
          </div>

          <button
            style={tienePermiso('HISTORIA_CLINICA_CREATE') ? undefined : { display: 'none' }}
            onClick={() => {
              setFormVisita({
                fecha_hora: new Date().toISOString().slice(0, 16),
                cita_id: '',
                motivo_consulta: '',
                observaciones_clinicas: '',
                diagnostico: '',
                procedimiento_realizado: '',
                item_plan_completado_id: '',
                item_plan_proxima_sesion_id: '',
                receta_medicamentos: '',
                indicaciones_postoperatorias: '',
              });
              setShowModal(true);
            }}
            className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Nueva Nota de Evolución
          </button>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-500 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* SECCIÓN 1: Sincronización de Tratamientos con Odontograma (Point 3) */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700/60 gap-2">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              Plan de Tratamiento & Odontograma Sincronizado
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Visualiza en tiempo real los tratamientos completados (azul), en curso/próxima sesión (ámbar) y planificados (rojo).
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 px-2.5 py-1 rounded-lg border border-blue-200 dark:border-blue-500/20">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block"></span> Alta / Completado (Azul)
            </span>
            <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-200 dark:border-amber-500/20">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span> Próxima Sesión (Ámbar)
            </span>
            <span className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-2.5 py-1 rounded-lg border border-rose-200 dark:border-rose-500/20">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span> Planificado (Rojo)
            </span>
          </div>
        </div>

        {todosLosItems.length === 0 ? (
          <div className="py-6 text-center text-slate-500 dark:text-slate-400 text-xs">
            Este paciente no posee ítems registrados en sus planes de tratamiento activos.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {todosLosItems.map((item) => {
              const isCompletado = item.estado === 'COMPLETADO';
              const isProxima = item.estado === 'PROXIMA_SESION' || item.es_proxima_sesion;

              return (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-xl border transition flex flex-col justify-between gap-3 shadow-sm ${
                    isCompletado
                      ? 'bg-blue-50/60 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800/40 text-blue-900 dark:text-blue-200'
                      : isProxima
                      ? 'bg-amber-50/60 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/40 text-amber-900 dark:text-amber-200'
                      : 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/40 text-slate-800 dark:text-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white">
                        {item.pieza_fdi ? `Pieza FDI #${item.pieza_fdi}` : 'Procedimiento General'}
                        {item.superficie ? ` · ${item.superficie}` : ''}
                      </span>

                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                          isCompletado
                            ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30'
                            : isProxima
                            ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30'
                            : 'bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/30'
                        }`}
                      >
                        {isCompletado ? 'Alta Médica' : isProxima ? 'Próxima Sesión' : 'Planificado'}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">
                      {item.tratamiento?.nombre || 'Tratamiento Dental'}
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      Costo: ${Number(item.precio_unitario || 0).toFixed(2)}
                    </p>
                  </div>

                  {/* Acciones directas para el odontograma */}
                  <div className="pt-2 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between text-xs">
                    {!isCompletado ? (
                      <button
                        onClick={() => {
                          setFormVisita({
                            fecha_hora: new Date().toISOString().slice(0, 16),
                            cita_id: '',
                            motivo_consulta: `Atención: ${item.tratamiento?.nombre} (Pieza ${item.pieza_fdi || 'General'})`,
                            observaciones_clinicas: '',
                            diagnostico: '',
                            procedimiento_realizado: `Se ejecutó tratamiento ${item.tratamiento?.nombre}`,
                            item_plan_completado_id: item.id,
                            item_plan_proxima_sesion_id: '',
                            receta_medicamentos: '',
                            indicaciones_postoperatorias: '',
                          });
                          setShowModal(true);
                        }}
                        className="text-emerald-600 dark:text-emerald-400 hover:underline font-semibold flex items-center gap-1"
                      >
                        <Check className="w-3.5 h-3.5" /> Registrar Realizado (Alta)
                      </button>
                    ) : (
                      <span className="text-blue-600 dark:text-blue-400 font-semibold flex items-center gap-1 text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Pintado en Azul en Odontograma
                      </span>
                    )}

                    {!isCompletado && !isProxima && (
                      <button
                        onClick={async () => {
                          try {
                            await api.updateItemPlan(item.id, { estado: 'PROXIMA_SESION', es_proxima_sesion: true });
                            setSuccess(`Tratamiento de pieza ${item.pieza_fdi || 'General'} marcado para la próxima sesión`);
                            setTimeout(() => setSuccess(''), 3000);
                            loadVisitasYPlanes();
                          } catch (err) {
                            setError(err.message || 'Error al actualizar estado');
                          }
                        }}
                        className="text-amber-600 dark:text-amber-400 hover:underline font-semibold text-[11px]"
                      >
                        Programar próxima sesión
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECCIÓN 2: Historial de Notas de Evolución Clínica */}
      <div className="space-y-4">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          Historial Cronológico de Sesiones de Atención
        </h3>

        {loading ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs">Cargando expediente clínico...</div>
        ) : visitas.length === 0 ? (
          <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-12 text-center text-slate-500 dark:text-slate-400 shadow-sm">
            <FileText className="w-12 h-12 text-slate-400 dark:text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Sin notas de evolución previas</h3>
            <p className="text-xs text-slate-500 mt-1">
              Haz clic en "Nueva Nota de Evolución" para registrar la sesión clínica de hoy.
            </p>
          </div>
        ) : (
          visitas.map((visita) => {
            const fechaStr = visita.fecha_hora
              ? new Date(visita.fecha_hora).toLocaleDateString()
              : visita.created_at
              ? new Date(visita.created_at).toLocaleDateString()
              : 'Fecha';
            const horaStr = visita.fecha_hora
              ? new Date(visita.fecha_hora).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : visita.created_at
              ? new Date(visita.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : '';
            const doctorNombre = visita.doctor_nombre || 'Dr(a). Tratante';

            return (
              <div
                key={visita.id}
                className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-6 space-y-4 shadow-sm"
              >
                {/* Encabezado Nota */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700/60 gap-2">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-500/30 rounded-xl">
                      <FileCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        {visita.motivo_consulta || visita.motivo_visita || 'Consulta de Evolución Odontológica'}
                      </h3>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        Atendido por: <span className="text-teal-600 dark:text-teal-400 font-semibold">{doctorNombre}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    {visita.generada_automaticamente && (
                      <span
                        className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 flex items-center gap-1"
                        title="Se creó al finalizar la cita. Solo admite observaciones del doctor o asistente"
                      >
                        <Shield className="w-3 h-3" /> Generada al finalizar la cita
                      </span>
                    )}
                    {visita.cita_id && (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/30 text-primary-600 dark:text-primary-400 flex items-center gap-1">
                        <LinkIcon className="w-3 h-3" /> Vinculada a Cita Programada
                      </span>
                    )}

                    <div className="text-xs font-mono text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
                      {fechaStr} {horaStr}
                    </div>
                  </div>
                </div>

                {/* Contenido Clínico */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/40 rounded-xl space-y-1">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[10px]">
                      Observaciones Clínicas / Diagnóstico:
                    </span>
                    <p className="text-slate-700 dark:text-slate-200 whitespace-pre-line mt-1">
                      {visita.recomendaciones || visita.diagnostico || 'Sin observaciones registradas.'}
                    </p>
                  </div>

                  <div className="p-3.5 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/40 rounded-xl space-y-1">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider text-[10px]">
                      Procedimiento Realizado:
                    </span>
                    <p className="text-slate-700 dark:text-slate-200 whitespace-pre-line mt-1">
                      {visita.procedimiento_realizado || 'No especificado.'}
                    </p>
                  </div>
                </div>

                {/* Receta Médica si existe */}
                {(visita.receta_medicamentos || visita.indicaciones_proxima_visita) && (
                  <div className="p-4 bg-primary-50/50 dark:bg-primary-950/30 border border-primary-200 dark:border-primary-500/30 rounded-xl space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-primary-700 dark:text-primary-400 flex items-center gap-1.5 uppercase tracking-wider">
                        <Pill className="w-4 h-4" /> Receta Médica & Cuidados Post-Operatorios
                      </span>
                      <button
                        onClick={() => window.print()}
                        className="px-2 py-1 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 rounded text-[10px] text-slate-700 dark:text-slate-300 flex items-center gap-1 transition"
                      >
                        <Printer className="w-3 h-3" /> Imprimir Receta
                      </button>
                    </div>

                    {visita.receta_medicamentos && (
                      <div className="text-xs text-slate-900 dark:text-white bg-white dark:bg-slate-900/80 p-2.5 rounded-lg font-mono border border-slate-200 dark:border-slate-700/60">
                        {visita.receta_medicamentos}
                      </div>
                    )}

                    {visita.indicaciones_proxima_visita && (
                      <p className="text-[11px] text-slate-600 dark:text-slate-300 italic pt-1">
                        Indicaciones: {visita.indicaciones_proxima_visita}
                      </p>
                    )}
                  </div>
                )}

                {/* Observaciones del doctor y asistente: solo se agregan */}
                <div className="pt-3 border-t border-slate-200 dark:border-slate-700/60 space-y-2 text-xs">
                  <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[10px]">
                    Observaciones del Doctor / Asistente
                  </span>
                  {(visita.observaciones || []).map((obs) => (
                    <div
                      key={obs.id}
                      className="p-2.5 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/40 rounded-lg"
                    >
                      <p className="text-slate-700 dark:text-slate-200 whitespace-pre-line">{obs.texto}</p>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">
                        {obs.autor_nombre || 'Usuario'} ({obs.rol_autor}) · {new Date(obs.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                  {puedeObservar ? (
                    <form onSubmit={(e) => handleAgregarObservacion(e, visita.id)} className="flex items-start gap-2">
                      <textarea
                        rows="2"
                        maxLength={2000}
                        placeholder="Agregar una observación. Una vez guardada no se puede modificar."
                        value={observacionesNuevas[visita.id] || ''}
                        onChange={(e) => setObservacionesNuevas((prev) => ({ ...prev, [visita.id]: e.target.value }))}
                        className="flex-1 px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      <button
                        type="submit"
                        disabled={!(observacionesNuevas[visita.id] || '').trim()}
                        className="px-3 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-semibold transition flex items-center gap-1 whitespace-nowrap"
                      >
                        <Plus className="w-3.5 h-3.5" /> Agregar
                      </button>
                    </form>
                  ) : (
                    (visita.observaciones || []).length === 0 && (
                      <p className="text-slate-500 dark:text-slate-400">Sin observaciones registradas.</p>
                    )
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal Nueva Visita (Points 3, 4, 6) */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Registrar Evolución de Atención Odontológica</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Completa los hallazgos de la sesión, vincula a la cita realizada, avanza el plan sincronizado y prescribe receta (HU-07).
            </p>

            <form onSubmit={handleCreateVisita} className="space-y-4">
              <ErrorModal mensaje={error} />
              {/* SECCIÓN FECHA Y VINCULACIÓN A CITA (Point 4) */}
              <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
                <span className="text-[11px] font-bold text-primary-600 dark:text-primary-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-4 h-4" /> Fecha de Atención y Vinculación con Cita (HU-05 / HU-07)
                </span>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Fecha y Hora de la Atención *
                    </label>
                    <input
                      type="datetime-local"
                      required
                      value={formVisita.fecha_hora}
                      onChange={(e) => setFormVisita({ ...formVisita, fecha_hora: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Doctor Responsable *
                    </label>
                    {user?.puedeElegirDoctor ? (
                      <select
                        value={selectedDoctorId}
                        onChange={(e) => setSelectedDoctorId(e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        {doctores.map((doc) => (
                          <option key={doc.id} value={doc.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                            Dr(a). {doc.nombre_completo || doc.username}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold">
                        Dr(a). {doctores.find((d) => d.id === user?.doctor_id)?.nombre_completo || user?.username} (Tú)
                      </div>
                    )}
                  </div>
                </div>

                {/* Filtro y Selector de Citas Finalizadas / Realizadas */}
                <div className="pt-2 border-t border-slate-200 dark:border-slate-700/60 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                      <LinkIcon className="w-3.5 h-3.5 text-primary-500" />
                      Vincular a Cita Realizada (Opcional):
                    </label>

                    {/* Filtros de Cita */}
                    <div className="flex items-center gap-2">
                      <input
                        type="date"
                        value={filtroFechaCita}
                        onChange={(e) => setFiltroFechaCita(e.target.value)}
                        className="px-2 py-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-[11px] text-slate-800 dark:text-slate-200"
                        title="Filtrar citas por fecha"
                      />
                      {doctores.length > 0 && (
                        <select
                          value={filtroDoctorCita}
                          onChange={(e) => setFiltroDoctorCita(e.target.value)}
                          className="px-2 py-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-[11px] text-slate-800 dark:text-slate-200"
                          title="Filtrar citas por doctor"
                        >
                          <option value="">Todos los doctores</option>
                          {doctores.map((d) => (
                            <option key={d.id} value={d.id}>
                              Dr(a). {d.nombre_completo || d.username}
                            </option>
                          ))}
                        </select>
                      )}
                      {(filtroFechaCita || filtroDoctorCita) && (
                        <button
                          type="button"
                          onClick={() => {
                            setFiltroFechaCita('');
                            setFiltroDoctorCita('');
                          }}
                          className="text-[10px] text-primary-600 dark:text-primary-400 hover:underline"
                        >
                          Limpiar
                        </button>
                      )}
                    </div>
                  </div>

                  <select
                    value={formVisita.cita_id}
                    onChange={(e) => {
                      const cid = e.target.value;
                      const cita = citasPaciente.find((c) => c.id === cid);
                      if (cita) {
                        setFormVisita({
                          ...formVisita,
                          cita_id: cid,
                          fecha_hora: cita.fecha_inicio_programada ? cita.fecha_inicio_programada.slice(0, 16) : formVisita.fecha_hora,
                          motivo_consulta: formVisita.motivo_consulta || cita.motivo_consulta || 'Atención en cita programada',
                          item_plan_completado_id: cita.item_plan_id || formVisita.item_plan_completado_id,
                        });
                        if (cita.doctor_id) {
                          setSelectedDoctorId(cita.doctor_id);
                        }
                      } else {
                        setFormVisita({ ...formVisita, cita_id: '' });
                      }
                    }}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">-- Sin vincular a cita previa (Atención directa de guardia o espontánea) --</option>
                    {citasFiltradas.map((c) => {
                      const doc = doctores.find((d) => d.id === c.doctor_id);
                      const fFecha = c.fecha_inicio_programada ? c.fecha_inicio_programada.slice(0, 10) : '';
                      const fHora = c.fecha_inicio_programada ? c.fecha_inicio_programada.slice(11, 16) : '';
                      return (
                        <option key={c.id} value={c.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                          [{fFecha} {fHora}] {doc ? `Dr(a). ${doc.nombre_completo || doc.username}` : ''} - {c.motivo_consulta || 'Cita general'} ({c.estado})
                        </option>
                      );
                    })}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Motivo de la Sesión / Consulta *
                </label>
                <input
                  type="text"
                  required
                  placeholder="ej. Control de endodoncia, Restauración estética pieza 21"
                  value={formVisita.motivo_consulta}
                  onChange={(e) => setFormVisita({ ...formVisita, motivo_consulta: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Observaciones Clínicas / Diagnóstico
                  </label>
                  <textarea
                    rows="3"
                    placeholder="Evolución clínica, tolerancia a la anestesia, respuesta gingival..."
                    value={formVisita.observaciones_clinicas}
                    onChange={(e) => setFormVisita({ ...formVisita, observaciones_clinicas: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Procedimiento Realizado
                  </label>
                  <textarea
                    rows="3"
                    placeholder="Se realizó aislamiento absoluto, grabado ácido 15 seg, composite Filtek..."
                    value={formVisita.procedimiento_realizado}
                    onChange={(e) => setFormVisita({ ...formVisita, procedimiento_realizado: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* SECCIÓN 3: Conexión con el Plan de Tratamiento & Odontograma (Point 3) */}
              <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
                <span className="text-[11px] font-bold text-primary-600 dark:text-primary-400 uppercase tracking-wider block">
                  Flujo del Plan de Tratamiento & Odontograma (HU-04 / HU-07)
                </span>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Tratamiento Realizado Hoy (Marcar COMPLETADO / Azul en Odontograma):
                    </label>
                    <select
                      value={formVisita.item_plan_completado_id}
                      onChange={(e) => setFormVisita({ ...formVisita, item_plan_completado_id: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="">-- Ninguno / Procedimiento no planificado --</option>
                      {itemsPendientes.map((it) => (
                        <option key={it.id} value={it.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                          Pieza {it.pieza_fdi || 'Gen'}: {it.tratamiento?.nombre} ({it.estado})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Tratamiento para la PRÓXIMA SESIÓN (Marcar Ámbar):
                    </label>
                    <select
                      value={formVisita.item_plan_proxima_sesion_id}
                      onChange={(e) => setFormVisita({ ...formVisita, item_plan_proxima_sesion_id: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="">-- Ninguno programado --</option>
                      {itemsPendientes.map((it) => (
                        <option key={it.id} value={it.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                          Pieza {it.pieza_fdi || 'Gen'}: {it.tratamiento?.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* SECCIÓN 4: Receta y Farmacología */}
              <div className="border-t border-slate-200 dark:border-slate-800 pt-3">
                <span className="text-[11px] font-bold text-teal-600 dark:text-teal-400 uppercase tracking-wider block mb-2">
                  Receta Médica Odontológica
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Fármacos Prescritos (Dosis y Frecuencia)
                    </label>
                    <textarea
                      rows="3"
                      placeholder="ej. Ibuprofeno 600mg: 1 comprimido cada 8 horas por 3 días. Amoxicilina 875mg..."
                      value={formVisita.receta_medicamentos}
                      onChange={(e) => setFormVisita({ ...formVisita, receta_medicamentos: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Indicaciones Post-Operatorias
                    </label>
                    <textarea
                      rows="3"
                      placeholder="No enjuagarse las primeras 24 hrs, dieta blanda y fría, aplicar compresas con hielo..."
                      value={formVisita.indicaciones_postoperatorias}
                      onChange={(e) => setFormVisita({ ...formVisita, indicaciones_postoperatorias: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-primary-600/20"
                >
                  Guardar Nota y Receta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
