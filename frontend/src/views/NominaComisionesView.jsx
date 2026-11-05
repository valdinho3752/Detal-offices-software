import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Award,
  DollarSign,
  Plus,
  User,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Receipt,
  Clock,
  Sparkles,
} from 'lucide-react';

export default function NominaComisionesView() {
  const { user, tienePermiso } = useAuth();
  // Sin permiso de consulta general, cada doctor solo ve sus propias comisiones
  const verTodos = tienePermiso('EMPLEADOS_READ');
  const [doctores, setDoctores] = useState([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [comisionesData, setComisionesData] = useState(null);
  const [pagosHistorico, setPagosHistorico] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modal registrar pago / anticipo
  const [showModal, setShowModal] = useState(false);
  const [formPago, setFormPago] = useState({
    tipo_pago: 'COMISION_TRATAMIENTOS',
    monto: '',
    descontar_de_caja: true,
    observaciones: '',
  });

  useEffect(() => {
    const init = async () => {
      try {
        const dRes = await api.getDoctores();
        const lista = (Array.isArray(dRes) ? dRes : []).filter((d) => verTodos || d.id === user?.doctor_id);
        setDoctores(lista);
        if (lista.length > 0) {
          setSelectedDoctorId(lista[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    init();
  }, []);

  const selectedDoctor = doctores.find((d) => d.id === selectedDoctorId);

  const loadDoctorFinanzas = async () => {
    if (!selectedDoctor) return;
    setLoading(true);
    setError('');
    try {
      const [comRes, pagRes] = await Promise.all([
        api.getComisionesDoctor(selectedDoctorId),
        api.getPagosEmpleados(selectedDoctor.usuario_id),
      ]);
      setComisionesData(comRes);
      setPagosHistorico(Array.isArray(pagRes) ? pagRes : []);
    } catch (err) {
      setError(err.message || 'Error cargando comisiones');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDoctorFinanzas();
  }, [selectedDoctorId, doctores]);

  const handleRegistrarPago = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const monto = Number(formPago.monto);
      await api.registrarPagoEmpleado({
        usuario_empleado_id: selectedDoctor.usuario_id,
        tipo_pago: formPago.tipo_pago,
        // El saldo de comisiones solo descuenta lo liquidado como comisión
        monto_comisiones: formPago.tipo_pago === 'COMISION_TRATAMIENTOS' ? monto : 0,
        monto_base: formPago.tipo_pago === 'SUELDO_MENSUAL' ? monto : 0,
        monto_neto_pagado: monto,
        metodo_pago: formPago.descontar_de_caja ? 'EFECTIVO_CAJA' : 'TRANSFERENCIA',
        observaciones: formPago.observaciones,
      });

      setSuccess('Pago de personal registrado y procesado exitosamente');
      setShowModal(false);
      setFormPago({
        tipo_pago: 'COMISION_TRATAMIENTOS',
        monto: '',
        descontar_de_caja: true,
        observaciones: '',
      });
      setTimeout(() => setSuccess(''), 3000);
      loadDoctorFinanzas();
    } catch (err) {
      setError(err.message || 'Error al registrar pago');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Nómina & Liquidación de Comisiones</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Cálculo de honorarios médicos según porcentaje contractual, deducción de anticipos y vales (HU-12)
          </p>
        </div>

        {/* Selector de Doctor y Botón Emitir Pago */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2 rounded-xl shadow-sm">
            <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            <select
              value={selectedDoctorId}
              onChange={(e) => setSelectedDoctorId(e.target.value)}
              className="bg-transparent text-slate-900 dark:text-white text-xs font-semibold focus:outline-none cursor-pointer"
            >
              {doctores.map((doc) => (
                <option key={doc.id} value={doc.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                  Dr(a). {doc.nombre_completo || doc.username} ({doc.especialidad || 'General'})
                </option>
              ))}
            </select>
          </div>

          <button
            style={tienePermiso('EMPLEADOS_PAGOS') ? undefined : { display: 'none' }}
            onClick={() => {
              setFormPago({
                tipo_pago: 'COMISION_TRATAMIENTOS',
                monto: comisionesData?.saldo_comision_por_pagar > 0 ? Number(comisionesData.saldo_comision_por_pagar).toFixed(2) : '',
                descontar_de_caja: true,
                observaciones: `Liquidación comisiones Dr(a). ${selectedDoctor?.nombre_completo || selectedDoctor?.username}`,
              });
              setShowModal(true);
            }}
            className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Liquidar Pago / Adelanto
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

      {/* Resumen de Liquidación del Doctor */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-6 space-y-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-700/60 gap-4">
          <div>
            <span className="text-xs font-bold text-teal-600 dark:text-teal-400 uppercase tracking-wider flex items-center gap-1">
              <Award className="w-4 h-4" /> Contrato Profesional
            </span>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
              Dr(a). {selectedDoctor?.nombre_completo || selectedDoctor?.username}
            </h2>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Especialidad: {selectedDoctor?.especialidad || 'Odontología General'} · Colegiado:{' '}
              {selectedDoctor?.numero_colegiatura || 'N/A'}
            </div>
          </div>

          <div className="text-right">
            <span className="text-xs text-slate-500 dark:text-slate-400 block">Comisión Pactada:</span>
            <span className="text-2xl font-bold font-mono text-primary-600 dark:text-primary-400">
              {Number(comisionesData?.porcentaje_pactado || 0)}%
            </span>
          </div>
        </div>

        {/* 4 Métricas de Comisión */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Producción Cobrada */}
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Total Producido Efectivo</span>
            <div className="text-xl font-bold text-slate-900 dark:text-white font-mono">
              ${Number(comisionesData?.total_cobrado_por_sus_tratamientos || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Tratamientos pagados por pacientes</div>
          </div>

          {/* Comisión Bruta */}
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Comisión Bruta Generada</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
              ${Number(comisionesData?.comision_bruta_generada || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-emerald-600 dark:text-emerald-500 mt-1">{Number(comisionesData?.porcentaje_pactado || 0)}% del producido</div>
          </div>

          {/* Anticipos Retirados */}
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Comisiones ya Liquidadas</span>
            <div className="text-xl font-bold text-amber-600 dark:text-amber-400 font-mono">
              -${Number(comisionesData?.comisiones_ya_liquidadas || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-amber-600 dark:text-amber-500 mt-1">Pagadas al profesional</div>
          </div>

          {/* Neto a Pagar */}
          <div className="p-4 bg-primary-50 dark:bg-primary-600/10 border border-primary-200 dark:border-primary-500/30 rounded-xl">
            <span className="text-xs text-primary-700 dark:text-primary-300 block mb-1 font-semibold">Neto a Liquidar</span>
            <div className="text-2xl font-bold text-primary-600 dark:text-primary-400 font-mono">
              ${Number(comisionesData?.saldo_comision_por_pagar || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-primary-600/80 dark:text-primary-300/80 mt-1">Bruta menos lo ya liquidado</div>
          </div>
        </div>
      </div>

      {/* Historial de Pagos y Liquidaciones */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2 pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <Receipt className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          Historial de Pagos & Vales de Nómina
        </h3>

        {pagosHistorico.length === 0 ? (
          <div className="py-8 text-center text-slate-500 dark:text-slate-400 text-xs">
            No se han registrado pagos previos a este profesional.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Fecha / Hora</th>
                  <th className="py-3 px-4">Tipo de Pago</th>
                  <th className="py-3 px-4 text-center">Descontado de Caja</th>
                  <th className="py-3 px-4">Observaciones</th>
                  <th className="py-3 px-4 text-right">Monto Pagado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {pagosHistorico.map((pago) => (
                  <tr key={pago.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/20 transition">
                    <td className="py-3 px-4 font-mono text-slate-500 dark:text-slate-400">
                      {pago.fecha_hora_pago ? new Date(pago.fecha_hora_pago).toLocaleString() : 'Fecha'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold border ${
                          pago.tipo_pago === 'COMISION_TRATAMIENTOS'
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                            : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {pago.tipo_pago}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center font-mono">
                      {pago.metodo_pago === 'EFECTIVO_CAJA' ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold">SÍ (Gaveta)</span>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500">NO</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 dark:text-slate-400 italic">{pago.observaciones || '-'}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">
                      ${Number(pago.monto_neto_pagado).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Registrar Pago / Vale */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Emitir Pago a Profesional</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Registra una liquidación de comisión o un vale / anticipo de sueldo (HU-12).
            </p>

            <form onSubmit={handleRegistrarPago} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo de Pago *</label>
                <select
                  value={formPago.tipo_pago}
                  onChange={(e) => setFormPago({ ...formPago, tipo_pago: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="COMISION_TRATAMIENTOS" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Liquidación de Comisiones Médicas</option>
                  <option value="ADELANTO" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Anticipo / Vale de Sueldo</option>
                  <option value="SUELDO_MENSUAL" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Sueldo Base Mensual</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Monto a Pagar ($) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="0.00"
                  value={formPago.monto}
                  onChange={(e) => setFormPago({ ...formPago, monto: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-base font-mono font-bold focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">¿Descontar de Caja Física?</span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400">Resta el monto de la gaveta de caja diaria (HU-10)</span>
                </div>
                <input
                  type="checkbox"
                  checked={formPago.descontar_de_caja}
                  onChange={(e) => setFormPago({ ...formPago, descontar_de_caja: e.target.checked })}
                  className="rounded border-slate-300 dark:border-slate-700 text-primary-500 focus:ring-0 cursor-pointer w-4 h-4"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Observaciones</label>
                <textarea
                  rows="2"
                  placeholder="Liquidación quincenal, comisiones por endodoncias..."
                  value={formPago.observaciones}
                  onChange={(e) => setFormPago({ ...formPago, observaciones: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
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
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Confirmar Pago
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
