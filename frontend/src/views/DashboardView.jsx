import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { puedeAcceder } from '../config/accesos';
import {
  Users,
  Calendar,
  DollarSign,
  TrendingUp,
  Clock,
  Activity,
  ShieldAlert,
  FileText,
  Camera,
  Layers,
  Award,
  ChevronRight,
  AlertTriangle,
  Play,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export default function DashboardView() {
  const auth = useAuth();
  const { user, tienePermiso } = auth;
  const accesible = (ruta) => puedeAcceder(ruta, auth);
  const verCaja = tienePermiso('CAJA_READ');
  const verFinanzas = tienePermiso('REPORTES_READ');
  const verCitas = tienePermiso('CITAS_READ');
  const [caja, setCaja] = useState(null);
  const [citasHoy, setCitasHoy] = useState([]);
  const [resumenFinanzas, setResumenFinanzas] = useState(null);
  const [pacientesCount, setPacientesCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const hoyStr = new Date().toISOString().split('T')[0];

  const loadData = async () => {
    setLoading(true);
    try {
      const [cajaRes, citasRes, finanzasRes, pacientesRes] = await Promise.allSettled([
        api.getEstadoCaja(),
        verCitas ? api.getCitas(`?fecha_inicio=${hoyStr}&fecha_fin=${hoyStr}`) : [],
        verFinanzas ? api.getReporteFinanciero() : null,
        tienePermiso('PACIENTES_READ') ? api.getPacientes('', 0, 1) : [],
      ]);

      if (cajaRes.status === 'fulfilled') setCaja(cajaRes.value);
      if (citasRes.status === 'fulfilled') setCitasHoy(Array.isArray(citasRes.value) ? citasRes.value : []);
      if (finanzasRes.status === 'fulfilled') setResumenFinanzas(finanzasRes.value);
      if (pacientesRes.status === 'fulfilled') {
        // total or length
        const pData = pacientesRes.value;
        if (Array.isArray(pData)) setPacientesCount(pData.length);
      }
    } catch (err) {
      console.error('Error cargando dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateSillon = async (citaId, nuevoEstado) => {
    try {
      await api.controlSillon(citaId, { estado: nuevoEstado });
      loadData();
    } catch (err) {
      alert(`Error al actualizar estado: ${err.message}`);
    }
  };

  const modulos = [
    { title: 'Gestión de Pacientes', desc: 'Directorio clínico y antecedentes anamnésicos (HU-03)', href: '/pacientes', icon: Users, color: 'bg-blue-500' },
    { title: 'Odontograma Dental', desc: 'Mapeo gráfico FDI y planes de tratamiento (HU-04)', href: '/odontograma', icon: Activity, color: 'bg-emerald-500' },
    { title: 'Agenda de Citas & Sillón', desc: 'Gestión por doctor, box y tiempos de atención (HU-05)', href: '/citas', icon: Calendar, color: 'bg-indigo-500' },
    { title: 'Control Horario (Fichaje)', desc: 'Registro de jornada laboral de doctores y personal (HU-06)', href: '/asistencia', icon: Clock, color: 'bg-amber-500' },
    { title: 'Evolución Clínica', desc: 'Notas de visita, recetas y próximos pasos (HU-07)', href: '/evolucion', icon: FileText, color: 'bg-teal-500' },
    { title: 'Visor Radiográfico', desc: 'RX digitales y diagnóstico por pieza dental (HU-08)', href: '/radiografias', icon: Camera, color: 'bg-cyan-500' },
    { title: 'Prótesis & Laboratorio', desc: 'Control de órdenes, color Vita y entregas (HU-09)', href: '/protesis', icon: Layers, color: 'bg-purple-500' },
    { title: 'Caja Operativa Diaria', desc: 'Apertura, egresos, arqueo físico y cierres (HU-10)', href: '/caja', icon: DollarSign, color: 'bg-emerald-600' },
    { title: 'Cobranzas & Pagos', desc: 'Cobro de presupuestos, abonos y deudas (HU-11)', href: '/cobranzas', icon: DollarSign, color: 'bg-green-500' },
    { title: 'Nómina & Comisiones', desc: 'Liquidación médica según porcentaje y adelantos (HU-12)', href: '/nomina', icon: Award, color: 'bg-violet-500' },
    { title: 'Auditoría Forense', desc: 'Trazabilidad de cambios con diff de datos (HU-13)', href: '/auditoria', icon: ShieldAlert, color: 'bg-rose-500' },
    { title: 'Inteligencia de Negocio', desc: 'Métricas de productividad, demanda y margen (HU-14)', href: '/reportes', icon: TrendingUp, color: 'bg-sky-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Saludo y fecha */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Panel Principal</h1>
          <p className="text-slate-400 text-sm">
            Bienvenido, <span className="text-primary-400 font-semibold">{user?.nombre_completo || user?.username}</span> · Rol:{' '}
            <span className="capitalize text-slate-300 font-medium">{user?.rol_nombre || user?.rol_str}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/citas"
            style={tienePermiso('CITAS_CREATE') ? undefined : { display: 'none' }}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-primary-600/20 transition flex items-center gap-1.5"
          >
            <Calendar className="w-4 h-4" />
            Nueva Cita
          </Link>
          <Link
            to="/pacientes"
            style={tienePermiso('PACIENTES_CREATE') ? undefined : { display: 'none' }}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <Users className="w-4 h-4" />
            Registrar Paciente
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Caja Gaveta */}
        {verCaja && <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-4 flex items-center gap-4">
          <div className={`p-3 rounded-xl ${caja?.abierta ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Caja en Gaveta (HU-10)</div>
            <div className="text-xl font-bold text-white mt-0.5">
              ${Number(caja?.saldo_en_gaveta || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] mt-0.5 font-medium flex items-center gap-1">
              {caja?.abierta ? (
                <span className="text-emerald-400 flex items-center gap-1">● Turno Abierto</span>
              ) : (
                <span className="text-rose-400 flex items-center gap-1">○ Caja Cerrada</span>
              )}
            </div>
          </div>
        </div>}

        {/* Citas de Hoy */}
        {verCitas && <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-4 flex items-center gap-4">
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl">
            <Calendar className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Citas para Hoy (HU-05)</div>
            <div className="text-xl font-bold text-white mt-0.5">{citasHoy.length}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {citasHoy.filter((c) => c.estado === 'EN_SILLON').length} actualmente en sillón
            </div>
          </div>
        </div>}

        {/* Ingresos del Mes */}
        {verFinanzas && <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-4 flex items-center gap-4">
          <div className="p-3 bg-sky-500/10 text-sky-400 rounded-xl">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Ingresos del Mes (HU-14)</div>
            <div className="text-xl font-bold text-white mt-0.5">
              ${Number(resumenFinanzas?.total_ingresos || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-emerald-400 mt-0.5">
              Margen: ${Number(resumenFinanzas?.balance_neto_operativo || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>}

        {/* Egresos Operativos */}
        {verFinanzas && <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-4 flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Egresos / Gastos (HU-10)</div>
            <div className="text-xl font-bold text-white mt-0.5">
              ${Number(resumenFinanzas?.total_egresos || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Insumos, laboratorio y anticipos</div>
          </div>
        </div>}
      </div>

      {/* Grid: Citas de Hoy y Estado de Sillón + Módulos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Columna Izquierda / Central: Agenda Hoy en Sillón */}
        <div className="lg:col-span-2 bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-indigo-400" />
                Control de Citas & Sillón Dental (Hoy)
              </h2>
              <p className="text-xs text-slate-400">Transiciones de flujo clínico en tiempo real (HU-05)</p>
            </div>
            <Link to="/citas" className="text-xs text-primary-400 hover:text-primary-300 font-medium flex items-center gap-1">
              Ver Agenda Completa <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {citasHoy.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-sm">
              No hay citas programadas para el día de hoy.{' '}
              <Link to="/citas" className="text-primary-400 hover:underline">
                Programar una cita ahora
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {citasHoy.slice(0, 5).map((cita) => {
                const pacienteNombre = cita.paciente ? `${cita.paciente.nombres} ${cita.paciente.apellidos}` : 'Paciente';
                const hora = cita.hora_inicio ? cita.hora_inicio.slice(0, 5) : '--:--';
                return (
                  <div
                    key={cita.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl gap-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-12 text-center py-1 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono font-bold text-primary-400">
                        {hora}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{pacienteNombre}</div>
                        <div className="text-xs text-slate-400">
                          {cita.motivo || 'Consulta odontológica'} · Box: {cita.box_numero || '1'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                          cita.estado === 'EN_SILLON'
                            ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse'
                            : cita.estado === 'FINALIZADA'
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                            : cita.estado === 'EN_ESPERA'
                            ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                            : cita.estado === 'CANCELADA'
                            ? 'bg-stone-500/10 border-dashed border-stone-500/50 text-stone-400 line-through'
                            : 'bg-slate-800 border-slate-700 text-slate-400'
                        }`}
                      >
                        {cita.estado}
                      </span>

                      {/* Botones de acción de flujo */}
                      {(cita.estado === 'PROGRAMADA' || cita.estado === 'CONFIRMADA') && (
                        <button
                          onClick={() => handleUpdateSillon(cita.id, 'EN_ESPERA')}
                          className="px-2.5 py-1 bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/30 text-xs rounded-lg transition"
                          title="Marcar llegada a sala de espera"
                        >
                          En Espera
                        </button>
                      )}
                      {cita.estado === 'EN_ESPERA' && (
                        <button
                          onClick={() => handleUpdateSillon(cita.id, 'EN_SILLON')}
                          className="px-2.5 py-1 bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/30 text-xs rounded-lg transition flex items-center gap-1"
                          title="Hacer pasar al sillón dental"
                        >
                          <Play className="w-3 h-3" /> A Sillón
                        </button>
                      )}
                      {cita.estado === 'EN_SILLON' && (
                        <button
                          onClick={() => handleUpdateSillon(cita.id, 'FINALIZADA')}
                          className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/30 text-xs rounded-lg transition flex items-center gap-1"
                          title="Finalizar atención clínica"
                        >
                          <CheckCircle2 className="w-3 h-3" /> Finalizar
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Columna Derecha: Alertas y Estado Rápido */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2 pb-3 border-b border-slate-700/60">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Acciones Prioritarias
          </h2>

          <div className="space-y-3">
            <Link
              to="/caja"
              style={accesible('/caja') ? undefined : { display: 'none' }}
              className="block p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl hover:border-primary-500/40 transition group"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 group-hover:text-primary-400">
                <span>Arqueo y Cierre de Caja</span>
                <ChevronRight className="w-4 h-4" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Verifica el conteo de billetes y registra egresos menores de turno.
              </p>
            </Link>

            <Link
              to="/protesis"
              style={accesible('/protesis') ? undefined : { display: 'none' }}
              className="block p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl hover:border-primary-500/40 transition group"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 group-hover:text-primary-400">
                <span>Órdenes de Laboratorio (HU-09)</span>
                <ChevronRight className="w-4 h-4" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Supervisa el estado de coronas, prótesis y fecha de llegada prometida.
              </p>
            </Link>

            <Link
              to="/auditoria"
              style={accesible('/auditoria') ? undefined : { display: 'none' }}
              className="block p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl hover:border-primary-500/40 transition group"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 group-hover:text-primary-400">
                <span>Bitácora de Auditoría (HU-13)</span>
                <ChevronRight className="w-4 h-4" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Inspecciona modificaciones de historia clínica y transacciones financieras.
              </p>
            </Link>
          </div>
        </div>
      </div>

      {/* Grid de Todos los 14 Módulos Clínicos */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4">Módulos del Sistema (HU-01 a HU-14)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {modulos.filter((m) => accesible(m.href)).map((m, idx) => {
            const Icon = m.icon;
            return (
              <Link
                key={idx}
                to={m.href}
                className="bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-primary-500/50 rounded-2xl p-4 transition duration-150 flex flex-col justify-between group shadow-sm hover:shadow-lg"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className={`p-2.5 rounded-xl text-white ${m.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-primary-400 transition" />
                  </div>
                  <h3 className="text-sm font-semibold text-white group-hover:text-primary-400 transition">{m.title}</h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{m.desc}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
