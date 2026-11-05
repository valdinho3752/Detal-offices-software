import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import {
  DollarSign,
  CreditCard,
  User,
  Plus,
  Receipt,
  CheckCircle2,
  AlertCircle,
  Clock,
  Printer,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import PacienteSearchInput from '../components/PacienteSearchInput';


export default function CobranzasView() {
  const [searchParams] = useSearchParams();
  const pacienteIdParam = searchParams.get('paciente_id');

  const [pacientes, setPacientes] = useState([]);
  const [doctores, setDoctores] = useState([]);
  const [selectedPacienteId, setSelectedPacienteId] = useState(pacienteIdParam || '');
  const [saldoInfo, setSaldoInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modal registrar pago
  const [showModal, setShowModal] = useState(false);
  const [formPago, setFormPago] = useState({
    monto: '',
    medio_pago: 'EFECTIVO',
    numero_comprobante: '',
    doctor_comision_id: '',
    observaciones: '',
    tipo_cobro: 'PLAN',
  });

  useEffect(() => {
    const loadPacientes = async () => {
      try {
        const [pRes, dRes] = await Promise.all([api.getPacientes('', 0, 100), api.getDoctores()]);
        setPacientes(Array.isArray(pRes) ? pRes : []);
        setDoctores(Array.isArray(dRes) ? dRes : []);
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

  const loadSaldo = async () => {
    if (!selectedPacienteId) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.getPacienteSaldo(selectedPacienteId);
      setSaldoInfo(data);
    } catch (err) {
      setError(err.message || 'Error cargando estado de cuenta');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSaldo();
  }, [selectedPacienteId]);

  const handleRegistrarPago = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.registrarPago({
        paciente_id: selectedPacienteId,
        monto: Number(formPago.monto),
        metodo_pago: formPago.medio_pago,
        referencia_comprobante: formPago.numero_comprobante || null,
        doctor_comision_id: formPago.doctor_comision_id || null,
        observaciones: formPago.observaciones,
        es_cobro_directo: esDirecto,
      });

      setSuccess(esDirecto ? 'Consulta cobrada: no afecta el saldo de los planes' : 'Pago recibido y acreditado a la cuenta del paciente');
      setShowModal(false);
      setTimeout(() => setSuccess(''), 3000);
      loadSaldo();
    } catch (err) {
      setError(err.message || 'Error al procesar cobro');
    }
  };

  const selectedPaciente = pacientes.find((p) => p.id === selectedPacienteId);
  const deuda = Number(saldoInfo?.saldo_pendiente || 0);
  const esDirecto = formPago.tipo_cobro === 'DIRECTO';
  const cobrosDirectos = (saldoInfo?.pagos || [])
    .filter((p) => p.es_cobro_directo)
    .reduce((total, p) => total + Number(p.monto), 0);

  const abrirCobro = () => {
    setError('');
    setFormPago({
      monto: deuda > 0 ? deuda.toFixed(2) : '',
      medio_pago: 'EFECTIVO',
      numero_comprobante: '',
      doctor_comision_id: '',
      observaciones: '',
      // Sin saldo en planes aprobados, lo único que se puede cobrar es una consulta
      tipo_cobro: deuda > 0 ? 'PLAN' : 'DIRECTO',
    });
    setShowModal(true);
  };

  const cambiarTipoCobro = (tipo) => {
    setFormPago({ ...formPago, tipo_cobro: tipo, monto: tipo === 'PLAN' ? deuda.toFixed(2) : '' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Cobranzas & Control de Pagos</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Pasarela de abonos multi-medio, actualización en vivo de deuda y comprobantes (HU-11)
          </p>
        </div>

        {/* Selector de Paciente con barra de búsqueda */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="w-full sm:w-72">
            <PacienteSearchInput
              pacientes={pacientes}
              selectedPacienteId={selectedPacienteId}
              onSelectPaciente={(id) => setSelectedPacienteId(id)}
              placeholder="Buscar paciente por nombre o CI..."
            />
          </div>

          <button
            disabled={!selectedPacienteId}
            onClick={abrirCobro}
            className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/20 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Registrar Abono / Pago
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

      {/* Tarjeta de Resumen Financiero del Paciente */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-6 space-y-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-700/60">
          <div>
            <span className="text-xs font-bold text-primary-600 dark:text-primary-400 uppercase tracking-wider">
              Expediente Financiero del Paciente
            </span>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
              {selectedPaciente ? `${selectedPaciente.nombres} ${selectedPaciente.apellidos}` : 'Seleccione un paciente'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {selectedPaciente ? `${selectedPaciente.tipo_documento}: ${selectedPaciente.numero_documento} · Tel: ${selectedPaciente.telefono || 'N/A'}` : 'Utilice el buscador para cargar el saldo y comprobantes'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${
                deuda > 0
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400 animate-pulse'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              }`}
            >
              {deuda > 0 ? 'ESTADO: DEUDOR' : 'ESTADO: AL DÍA'}
            </span>
          </div>
        </div>

        {/* Métricas: Presupuestado vs Abonado vs Saldo Deudor */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Total Presupuestado en Tratamientos</span>
            <div className="text-xl font-bold text-slate-900 dark:text-white font-mono">
              ${Number(saldoInfo?.total_tratamientos ?? saldoInfo?.total_presupuestado ?? 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Planes activos y completados</div>
          </div>

          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Total Abonado a Planes</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
              ${Number(saldoInfo?.total_pagado || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-emerald-600 dark:text-emerald-500 mt-1">
              {cobrosDirectos > 0
                ? `Además, $${cobrosDirectos.toFixed(2)} en consultas directas`
                : 'Ingresado al flujo de caja'}
            </div>
          </div>

          <div className={`p-4 rounded-xl border ${deuda > 0 ? 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30' : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30'}`}>
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Saldo Pendiente por Cobrar</span>
            <div className={`text-2xl font-bold font-mono ${deuda > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
              ${deuda.toLocaleString('es-CL', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              {deuda > 0 ? 'Deuda activa por liquidar' : 'Sin saldos pendientes'}
            </div>
          </div>
        </div>
      </div>

      {/* Historial de Pagos y Recibos Emitidos */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Receipt className="w-5 h-5 text-emerald-500" />
            Comprobantes de Pago del Paciente
          </h3>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-700 dark:text-slate-300 transition flex items-center gap-1.5"
          >
            <Printer className="w-3.5 h-3.5" /> Imprimir Estado de Cuenta
          </button>
        </div>

        {(!saldoInfo?.pagos || saldoInfo.pagos.length === 0) ? (
          <div className="py-8 text-center text-slate-500 dark:text-slate-400 text-xs">
            No se han registrado pagos para este paciente.{' '}
            <button
              onClick={abrirCobro}
              className="text-primary-600 dark:text-primary-400 hover:underline font-semibold"
            >
              Registrar el primer cobro
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Fecha / Hora</th>
                  <th className="py-3 px-4">Nº Comprobante</th>
                  <th className="py-3 px-4">Medio de Pago</th>
                  <th className="py-3 px-4">Observaciones</th>
                  <th className="py-3 px-4 text-right">Monto Pagado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {saldoInfo.pagos.map((pago) => (
                  <tr key={pago.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/20 transition">
                    <td className="py-3 px-4 font-mono text-slate-500 dark:text-slate-400">
                      {pago.created_at ? new Date(pago.created_at).toLocaleString() : 'Fecha'}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900 dark:text-white">
                      {pago.numero_comprobante || 'REC-001'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-300 rounded font-semibold text-[11px]">
                        {pago.medio_pago}
                      </span>
                      {pago.es_cobro_directo && (
                        <span className="ml-1.5 px-2 py-0.5 bg-sky-500/10 border border-sky-500/30 text-sky-700 dark:text-sky-300 rounded font-semibold text-[11px]">
                          Consulta directa
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 dark:text-slate-400 italic">{pago.observaciones || '-'}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      ${Number(pago.monto).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Registrar Abono */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Registrar Cobro / Abono</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Ingresa el pago del paciente y actualiza su saldo deudor (HU-11).
            </p>

            <form onSubmit={handleRegistrarPago} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label htmlFor="cobro-tipo" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo de Cobro *</label>
                <select
                  id="cobro-tipo"
                  value={formPago.tipo_cobro}
                  onChange={(e) => cambiarTipoCobro(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="PLAN" disabled={deuda <= 0} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                    Abono o adelanto a plan aprobado{deuda > 0 ? '' : ' (sin saldo pendiente)'}
                  </option>
                  <option value="DIRECTO" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Consulta directa (sin plan)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Monto a Cobrar ($) *{' '}
                  {!esDirecto && <span className="font-normal text-slate-500 dark:text-slate-400">· máximo ${deuda.toFixed(2)}</span>}
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={!esDirecto && deuda > 0 ? deuda.toFixed(2) : undefined}
                  required
                  placeholder="0.00"
                  value={formPago.monto}
                  onChange={(e) => setFormPago({ ...formPago, monto: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-base font-mono font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Medio de Pago *</label>
                <select
                  value={formPago.medio_pago}
                  onChange={(e) => setFormPago({ ...formPago, medio_pago: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="EFECTIVO" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Efectivo (Ingresa a gaveta de caja)</option>
                  <option value="TARJETA_DEBITO" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Tarjeta Débito (POS)</option>
                  <option value="TARJETA_CREDITO" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Tarjeta Crédito</option>
                  <option value="TRANSFERENCIA" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Transferencia Bancaria</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Doctor que recibe la comisión</label>
                <select
                  value={formPago.doctor_comision_id}
                  onChange={(e) => setFormPago({ ...formPago, doctor_comision_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">Sin comisión</option>
                  {doctores.map((doc) => (
                    <option key={doc.id} value={doc.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                      Dr(a). {doc.nombre_completo}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Nº Comprobante / Voucher</label>
                <input
                  type="text"
                  placeholder="ej. REC-892182 o Transbank #4892"
                  value={formPago.numero_comprobante}
                  onChange={(e) => setFormPago({ ...formPago, numero_comprobante: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label htmlFor="cobro-concepto" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  {esDirecto ? 'Concepto del Cobro *' : 'Observaciones'}
                </label>
                <textarea
                  id="cobro-concepto"
                  rows="2"
                  required={esDirecto}
                  placeholder={esDirecto ? 'Consulta general, evaluación...' : 'Abono a corona zirconio pieza 16...'}
                  value={formPago.observaciones}
                  onChange={(e) => setFormPago({ ...formPago, observaciones: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-emerald-600/20"
                >
                  Procesar Pago
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
