import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  DollarSign,
  TrendingDown,
  TrendingUp,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle2,
  PlusCircle,
  FileText,
  Clock,
  Sparkles,
  Layers,
  AlertCircle,
} from 'lucide-react';

export default function CajaOperativaView() {
  const { user } = useAuth();
  const [caja, setCaja] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modales
  const [showAbrirModal, setShowAbrirModal] = useState(false);
  const [showCerrarModal, setShowCerrarModal] = useState(false);
  const [showEgresoModal, setShowEgresoModal] = useState(false);

  // Forms
  const [montoApertura, setMontoApertura] = useState('100.00');
  const [egresoForm, setEgresoForm] = useState({
    categoria: 'COMPRA_INSUMOS',
    concepto: '',
    monto: '',
    comprobante_numero: '',
    observaciones: '',
  });
  const [cierreForm, setCierreForm] = useState({
    monto_real_fisico: '',
    justificacion_descuadre: '',
  });

  const loadCaja = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getEstadoCaja();
      setCaja(data);
    } catch (err) {
      setError(err.message || 'Error cargando estado de caja');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCaja();
  }, []);

  const handleAbrirCaja = async (e) => {
    e.preventDefault();
    try {
      await api.abrirCaja({
        monto_apertura: Number(montoApertura),
        observaciones: 'Apertura de turno por ' + (user?.nombre_completo || user?.username),
      });
      setSuccess('Caja abierta exitosamente con fondo inicial');
      setShowAbrirModal(false);
      setTimeout(() => setSuccess(''), 3000);
      loadCaja();
    } catch (err) {
      setError(err.message || 'Error al abrir caja');
    }
  };

  const handleRegistrarEgreso = async (e) => {
    e.preventDefault();
    try {
      await api.registrarEgreso({
        categoria: egresoForm.categoria,
        monto: Number(egresoForm.monto),
        concepto_motivo: egresoForm.concepto,
        numero_recibo_comprobante: egresoForm.comprobante_numero || null,
      });
      setSuccess('Egreso operativo registrado en caja');
      setShowEgresoModal(false);
      setEgresoForm({
        categoria: 'COMPRA_INSUMOS',
        concepto: '',
        monto: '',
        comprobante_numero: '',
        observaciones: '',
      });
      setTimeout(() => setSuccess(''), 3000);
      loadCaja();
    } catch (err) {
      setError(err.message || 'Error al registrar egreso');
    }
  };

  const handleCerrarCaja = async (e) => {
    e.preventDefault();
    try {
      const saldoTeorico = Number(caja?.saldo_en_gaveta || 0);
      const montoReal = Number(cierreForm.monto_real_fisico);
      const diferencia = montoReal - saldoTeorico;

      if (Math.abs(diferencia) > 0.001 && !cierreForm.justificacion_descuadre) {
        setError('Existe un descuadre de caja. Por favor ingresa una justificación');
        return;
      }

      await api.cerrarCaja({
        monto_cierre_real: montoReal,
        observaciones: cierreForm.justificacion_descuadre,
      });

      setSuccess('Caja arqueada y cerrada exitosamente');
      setShowCerrarModal(false);
      setTimeout(() => setSuccess(''), 3000);
      loadCaja();
    } catch (err) {
      setError(err.message || 'Error al cerrar caja');
    }
  };

  const saldoTeorico = Number(caja?.saldo_en_gaveta || 0);
  const montoRealInput = Number(cierreForm.monto_real_fisico || 0);
  const diferenciaCalculada = montoRealInput ? montoRealInput - saldoTeorico : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Caja Operativa Diaria & Arqueo</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            Control de fondo en gaveta, egresos menores y auditoría de descuadres de turno (HU-10)
          </p>
        </div>

        <div className="flex items-center gap-2">
          {caja?.abierta ? (
            <>
              <button
                onClick={() => setShowEgresoModal(true)}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-amber-600/20"
              >
                <TrendingDown className="w-4 h-4" />
                Registrar Egreso
              </button>
              <button
                onClick={() => {
                  setCierreForm({
                    monto_real_fisico: saldoTeorico.toFixed(2),
                    justificacion_descuadre: '',
                  });
                  setShowCerrarModal(true);
                }}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-rose-600/20"
              >
                <Lock className="w-4 h-4" />
                Cerrar Turno & Arqueo
              </button>
            </>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800 text-xs font-semibold">
              <Lock className="w-3.5 h-3.5" />
              <span>Caja Cerrada</span>
            </div>
          )}
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* KPI Cards de Caja */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Saldo en Gaveta */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Efectivo en Gaveta
            </span>
            <div className={`p-2 rounded-xl ${caja?.abierta ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white">
            ${saldoTeorico.toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] font-medium flex items-center gap-1.5">
            {caja?.abierta ? (
              <span className="text-emerald-400">● Caja abierta por {caja.usuario_apertura_nombre || 'Usuario'}</span>
            ) : (
              <span className="text-rose-400">○ Caja cerrada actualmente</span>
            )}
          </div>
        </div>

        {/* Fondo de Apertura */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Fondo Apertura
            </span>
            <div className="p-2 bg-primary-500/10 text-primary-400 rounded-xl">
              <Unlock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white">
            ${Number(caja?.monto_apertura || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Fondo base para cambio / vueltos
          </div>
        </div>

        {/* Total Ingresos Efectivo */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Ingresos del Turno
            </span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            +${Number(caja?.total_ingresos || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Cobros de tratamientos en efectivo
          </div>
        </div>

        {/* Total Egresos */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Egresos Operativos
            </span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-xl">
              <TrendingDown className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-amber-400">
            -${Number(caja?.total_egresos || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Gastos menores y retiros
          </div>
        </div>
      </div>

      {/* Historial de Movimientos de Caja */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
        <h2 className="text-base font-semibold text-white flex items-center justify-between pb-3 border-b border-slate-700/60">
          <span>Movimientos del Turno de Caja</span>
          <span className="text-xs text-slate-400">
            Fórmula: Fondo Inicial ({caja?.monto_apertura || 0}) + Ingresos ({caja?.total_ingresos || 0}) - Egresos ({caja?.total_egresos || 0})
          </span>
        </h2>

        {(!caja?.movimientos || caja.movimientos.length === 0) ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No se han registrado movimientos de egreso o cobro en este turno.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Hora</th>
                  <th className="py-3 px-4">Tipo</th>
                  <th className="py-3 px-4">Concepto / Categoría</th>
                  <th className="py-3 px-4">Comprobante</th>
                  <th className="py-3 px-4 text-right">Monto</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40 text-slate-300">
                {caja.movimientos.map((m, idx) => (
                  <tr key={idx} className="hover:bg-slate-700/20 transition">
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : '--:--'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.tipo === 'INGRESO'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {m.tipo}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-white">{m.concepto}</td>
                    <td className="py-3 px-4 font-mono text-slate-400">{m.comprobante_numero || '-'}</td>
                    <td
                      className={`py-3 px-4 text-right font-mono font-bold ${
                        m.tipo === 'INGRESO' ? 'text-emerald-400' : 'text-amber-400'
                      }`}
                    >
                      {m.tipo === 'INGRESO' ? '+' : '-'}${Number(m.monto).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Abrir Caja */}
      {showAbrirModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Apertura de Turno de Caja</h3>
            <p className="text-xs text-slate-400 mb-4">
              Ingresa el fondo inicial de dinero en efectivo con el que se arranca la jornada.
            </p>

            <form onSubmit={handleAbrirCaja} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Fondo Inicial ($) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={montoApertura}
                  onChange={(e) => setMontoApertura(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm font-mono font-bold"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAbrirModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-emerald-600/20"
                >
                  Confirmar Apertura
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Registrar Egreso */}
      {showEgresoModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Registrar Egreso Menor de Caja</h3>
            <p className="text-xs text-slate-400 mb-4">
              Salida de efectivo autorizada para insumos, delivery, mantenimiento o adelantos.
            </p>

            <form onSubmit={handleRegistrarEgreso} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Categoría de Gasto *</label>
                <select
                  value={egresoForm.categoria}
                  onChange={(e) => setEgresoForm({ ...egresoForm, categoria: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                >
                  <option value="COMPRA_INSUMOS">Insumos Menores & Descartables</option>
                  <option value="PAGO_LABORATORIO_PROTESIS">Pago a Laboratorio Dental</option>
                  <option value="GASTO_OPERATIVO">Servicios / Envíos</option>
                  <option value="ADELANTO_SUELDO">Adelanto / Vale de Empleado</option>
                  <option value="OTRO">Otro Gasto Operativo</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Concepto / Motivo *</label>
                <input
                  type="text"
                  required
                  placeholder="ej. Compra de mascarillas y guantes en farmacia"
                  value={egresoForm.concepto}
                  onChange={(e) => setEgresoForm({ ...egresoForm, concepto: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Monto ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="0.00"
                    value={egresoForm.monto}
                    onChange={(e) => setEgresoForm({ ...egresoForm, monto: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Nº Comprobante</label>
                  <input
                    type="text"
                    placeholder="Boleta / Factura"
                    value={egresoForm.comprobante_numero}
                    onChange={(e) => setEgresoForm({ ...egresoForm, comprobante_numero: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowEgresoModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Registrar Salida
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Cierre y Arqueo */}
      {showCerrarModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Arqueo Físico & Cierre de Caja</h3>
            <p className="text-xs text-slate-400 mb-4">
              Realiza el conteo físico de los billetes y monedas en gaveta.
            </p>

            <form onSubmit={handleCerrarCaja} className="space-y-4">
              <div className="p-3.5 bg-slate-800/80 rounded-xl border border-slate-700 flex justify-between items-center text-xs">
                <span className="text-slate-400">Saldo Teórico del Sistema:</span>
                <span className="font-mono font-bold text-white text-sm">
                  ${saldoTeorico.toFixed(2)}
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Efectivo Físico Real Contado ($) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={cierreForm.monto_real_fisico}
                  onChange={(e) => setCierreForm({ ...cierreForm, monto_real_fisico: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm font-mono font-bold"
                />
              </div>

              {/* Indicador de Descuadre */}
              <div
                className={`p-3 rounded-xl border text-xs flex items-center justify-between font-mono font-bold ${
                  Math.abs(diferenciaCalculada) < 0.001
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : diferenciaCalculada > 0
                    ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                }`}
              >
                <span>
                  {Math.abs(diferenciaCalculada) < 0.001
                    ? '✓ Caja Cuadrada Perfecta'
                    : diferenciaCalculada > 0
                    ? '▲ Sobrante de Caja'
                    : '▼ Faltante de Caja'}
                </span>
                <span>${diferenciaCalculada.toFixed(2)}</span>
              </div>

              {Math.abs(diferenciaCalculada) > 0.001 && (
                <div>
                  <label className="block text-xs font-semibold text-rose-400 mb-1">
                    Justificación Obligatoria del Descuadre *
                  </label>
                  <textarea
                    rows="2"
                    required
                    placeholder="Explica la causa del sobrante o faltante detectado..."
                    value={cierreForm.justificacion_descuadre}
                    onChange={(e) => setCierreForm({ ...cierreForm, justificacion_descuadre: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-rose-500/40 rounded-xl text-white text-xs"
                  />
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCerrarModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Cerrar y Archivar Turno
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
