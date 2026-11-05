import React, { useState } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Lock,
  Unlock,
  AlertTriangle,
  Calendar,
  DollarSign,
  Clock,
  Sparkles,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export default function CajaBloqueoBarrier({ cajaEstado, onCajaUpdated }) {
  const { user, tienePermiso } = useAuth();

  // Estados locales para formularios de apertura / cierre
  const [montoApertura, setMontoApertura] = useState('100.00');
  const [obsApertura, setObsApertura] = useState('');
  
  const [montoCierreContado, setMontoCierreContado] = useState(
    cajaEstado?.saldo_en_gaveta ? Number(cajaEstado.saldo_en_gaveta).toFixed(2) : '0.00'
  );
  const [obsCierre, setObsCierre] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!cajaEstado?.tipo_bloqueo) {
    return null;
  }

  const isAperturaRequerida = cajaEstado.tipo_bloqueo === 'APERTURA_REQUERIDA';
  const isCierrePendiente = cajaEstado.tipo_bloqueo === 'CIERRE_PENDIENTE_ANTERIOR';
  const puedeOperarCaja = tienePermiso(isAperturaRequerida ? 'CAJA_APERTURA' : 'CAJA_CIERRE');

  // Fecha legible para hoy
  const hoyStr = new Date().toLocaleDateString('es-ES', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const handleAbrirCaja = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const montoNum = Number(montoApertura);
      if (isNaN(montoNum) || montoNum < 0) {
        throw new Error('Ingrese un monto de fondo inicial válido');
      }

      await api.abrirCaja({
        monto_inicial_fondo: montoNum,
        monto_apertura: montoNum,
        observaciones: obsApertura || `Apertura de turno por ${user?.nombre_completo || user?.username}`,
      });

      setSuccess('¡Caja diaria abierta exitosamente! Desbloqueando sistema...');
      setTimeout(async () => {
        setSuccess('');
        if (onCajaUpdated) await onCajaUpdated();
      }, 1000);
    } catch (err) {
      setError(err.message || 'Error abriendo caja');
    } finally {
      setLoading(false);
    }
  };

  const handleCerrarCajaAnterior = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const saldoTeorico = Number(cajaEstado?.saldo_en_gaveta || cajaEstado?.efectivo_actual_en_gaveta || 0);
      const montoContadoNum = Number(montoCierreContado);
      if (isNaN(montoContadoNum) || montoContadoNum < 0) {
        throw new Error('Ingrese el efectivo contado físico');
      }

      const descuadre = montoContadoNum - saldoTeorico;
      if (Math.abs(descuadre) > 0.001 && !obsCierre) {
        throw new Error('Existe una diferencia de arqueo. Por favor ingrese una justificación para el cierre');
      }

      await api.cerrarCaja({
        total_efectivo_contado: montoContadoNum,
        monto_cierre_real: montoContadoNum,
        observaciones: obsCierre || 'Cierre de jornada anterior forzado por inicio de nuevo día',
      });

      setSuccess('Caja previa cerrada y arqueada con éxito. Verificando estado...');
      setTimeout(async () => {
        setSuccess('');
        if (onCajaUpdated) await onCajaUpdated();
      }, 1000);
    } catch (err) {
      setError(err.message || 'Error cerrando caja previa');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-300">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl max-w-xl w-full p-6 sm:p-8 space-y-6 relative overflow-hidden">
        {/* Glow de fondo */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Encabezado con Icono y Badge */}
        <div className="flex flex-col items-center text-center space-y-2 relative">
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg transition transform hover:scale-105 ${
              isAperturaRequerida
                ? 'bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-emerald-500/25'
                : 'bg-gradient-to-tr from-amber-600 to-orange-500 text-white shadow-amber-500/25'
            }`}
          >
            {isAperturaRequerida ? <Unlock className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            <Calendar className="w-3.5 h-3.5 text-primary-500" />
            <span>{hoyStr}</span>
          </div>

          <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            {isAperturaRequerida ? 'Apertura de Caja Diaria Requerida' : 'Atención: Caja Previa sin Cerrar'}
          </h2>

          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-md">
            {isAperturaRequerida
              ? 'El sistema ha detectado el inicio de una nueva jornada clínica. Para garantizar el control contable, debe ingresar el fondo de apertura en gaveta antes de operar.'
              : `Se detectó una caja abierta con fecha ${cajaEstado.fecha_apertura_str || 'anterior'} sin arqueo. Debe cerrar dicha sesión antes de iniciar las operaciones de hoy.`}
          </p>
        </div>

        {/* Notificaciones de Error / Éxito */}
        {error && (
          <div className="p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* Panel de Acción: Para Administrador / Recepción */}
        {puedeOperarCaja ? (
          <div>
            {isAperturaRequerida && (
              <form onSubmit={handleAbrirCaja} className="space-y-4">
                <div className="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-2xl border border-slate-200 dark:border-slate-700/60 space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Fondo Inicial de Efectivo en Gaveta ($ / Bs) *
                    </label>
                    <div className="relative">
                      <DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        value={montoApertura}
                        onChange={(e) => setMontoApertura(e.target.value)}
                        placeholder="100.00"
                        className="w-full pl-9 pr-3 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white font-mono text-sm font-bold focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                      />
                    </div>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                      Monto físico base para cambio y vueltos de caja en este turno.
                    </span>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Observaciones de Apertura (Opcional)
                    </label>
                    <input
                      type="text"
                      value={obsApertura}
                      onChange={(e) => setObsApertura(e.target.value)}
                      placeholder="ej. Turno Mañana / Responsable Recepción"
                      className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-sm rounded-xl transition shadow-lg shadow-emerald-600/25 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Unlock className="w-4 h-4" />
                  <span>{loading ? 'Abriendo Caja...' : 'Abrir Caja y Comenzar Turno'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            )}

            {isCierrePendiente && (
              <form onSubmit={handleCerrarCajaAnterior} className="space-y-4">
                <div className="bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-700/50 p-4 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between text-xs text-amber-800 dark:text-amber-300">
                    <span className="font-semibold">Fecha de Apertura Previa:</span>
                    <span className="font-mono font-bold">{cajaEstado.fecha_apertura_str || 'Día Anterior'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-amber-800 dark:text-amber-300 border-t border-amber-200/60 dark:border-amber-700/40 pt-2">
                    <span className="font-semibold">Saldo Teórico Esperado en Gaveta:</span>
                    <span className="font-mono font-black text-sm">
                      ${Number(cajaEstado.saldo_en_gaveta || cajaEstado.efectivo_actual_en_gaveta || 0).toFixed(2)}
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Total Efectivo Físico Contado ($ / Bs) *
                    </label>
                    <div className="relative">
                      <DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        value={montoCierreContado}
                        onChange={(e) => setMontoCierreContado(e.target.value)}
                        className="w-full pl-9 pr-3 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white font-mono text-sm font-bold focus:ring-2 focus:ring-amber-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Justificación / Observaciones de Cierre
                    </label>
                    <input
                      type="text"
                      value={obsCierre}
                      onChange={(e) => setObsCierre(e.target.value)}
                      placeholder="Cierre de jornada anterior para habilitar nuevo día"
                      className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold text-sm rounded-xl transition shadow-lg shadow-amber-600/25 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Lock className="w-4 h-4" />
                  <span>{loading ? 'Cerrando Caja Previa...' : 'Cerrar Caja Anterior y Proceder'}</span>
                </button>
              </form>
            )}
          </div>
        ) : (
          /* Para Doctores o Personal sin rol de caja */
          <div className="p-5 bg-slate-100 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 rounded-2xl text-center space-y-3">
            <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto" />
            <div className="text-xs text-slate-700 dark:text-slate-300 font-medium">
              Tu usuario ({user?.rol_str || 'Personal'}) no tiene permisos para aperturar o arquear caja.
              <br />
              Por favor solicita al personal de <strong>Recepción o Administración</strong> que realice la apertura de caja para desbloquear la jornada de hoy.
            </div>
            <button
              onClick={async () => {
                if (onCajaUpdated) await onCajaUpdated();
              }}
              className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-800 dark:text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 mx-auto"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Verificar si ya fue abierta</span>
            </button>
          </div>
        )}

        {/* Footer Informativo */}
        <div className="text-center pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-400">
          Clínica Dental Gustavo · Módulo de Control Financiero Diario (HU-10)
        </div>
      </div>
    </div>
  );
}
