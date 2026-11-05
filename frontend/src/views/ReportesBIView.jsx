import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  TrendingUp,
  Award,
  Clock,
  DollarSign,
  Activity,
  AlertTriangle,
  Users,
  CheckCircle2,
  Calendar,
  BarChart3,
  FileSpreadsheet,
} from 'lucide-react';

export default function ReportesBIView() {
  const [demanda, setDemanda] = useState([]);
  const [productividad, setProductividad] = useState([]);
  const [finanzas, setFinanzas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadReportes = async () => {
    setLoading(true);
    setError('');
    try {
      const [dRes, pRes, fRes] = await Promise.all([
        api.getReporteDemanda(10),
        api.getReporteProductividad(),
        api.getReporteFinanciero(),
      ]);

      setDemanda(Array.isArray(dRes) ? dRes : []);
      setProductividad(Array.isArray(pRes) ? pRes : []);
      setFinanzas(fRes);
    } catch (err) {
      setError(err.message || 'Error cargando reportes analíticos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReportes();
  }, []);

  const totalIngresos = Number(finanzas?.total_ingresos || 0);
  const totalEgresos = Number(finanzas?.total_egresos || 0);
  const margenNeto = Number(finanzas?.margen_neto || 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Reportes Analíticos & Business Intelligence</h1>
          <p className="text-slate-400 text-sm">
            Métricas de productividad médica, ranking de demanda y margen financiero neto (HU-14)
          </p>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* 3 Widgets Financieros Principales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Ingresos */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Ingresos Facturados
            </span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            ${totalIngresos.toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Cobros recaudados en todos los medios
          </div>
        </div>

        {/* Total Egresos */}
        <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Egresos & Costos
            </span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-xl">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            ${totalEgresos.toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Laboratorio, descartables y gastos menores
          </div>
        </div>

        {/* Margen Operativo Neto */}
        <div className={`p-5 rounded-2xl border ${margenNeto >= 0 ? 'bg-primary-600/10 border-primary-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
              Margen Neto Operativo
            </span>
            <div className="p-2 bg-primary-500/20 text-primary-400 rounded-xl">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className={`text-2xl font-bold font-mono ${margenNeto >= 0 ? 'text-primary-400' : 'text-rose-400'}`}>
            ${margenNeto.toLocaleString('es-CL', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400">
            Utilidad operativa neta de la clínica
          </div>
        </div>
      </div>

      {/* Grid: Demanda de Tratamientos vs Productividad por Doctor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Ranking de Demanda de Tratamientos */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-400" />
                Top Tratamientos Más Demandados
              </h2>
              <p className="text-xs text-slate-400">Procedimientos con mayor volumen en la clínica</p>
            </div>
          </div>

          {demanda.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-xs">Sin registros de tratamientos.</div>
          ) : (
            <div className="space-y-3">
              {demanda.map((item, idx) => {
                const totalFacturado = Number(item.total_recaudado || item.precio_base * item.cantidad_realizada || 0);
                return (
                  <div
                    key={idx}
                    className="p-3 bg-slate-900/60 border border-slate-700/40 rounded-xl flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-slate-800 text-primary-400 font-bold flex items-center justify-center text-xs">
                        #{idx + 1}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white">{item.tratamiento_nombre}</div>
                        <div className="text-[10px] text-slate-400">
                          {item.cantidad_realizada} procedimientos completados
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        ${totalFacturado.toFixed(2)}
                      </span>
                      <span className="block text-[10px] text-slate-500">Recaudado</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2. Productividad y No-Show por Doctor */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-teal-400" />
                Productividad Médica & Desempeño
              </h2>
              <p className="text-xs text-slate-400">
                Minutos en sillón dental y tasa de ausentismo (no-show) por profesional
              </p>
            </div>
          </div>

          {productividad.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-xs">Sin registros de productividad.</div>
          ) : (
            <div className="space-y-3">
              {productividad.map((doc, idx) => {
                const noShow = Number(doc.tasa_no_show_porcentaje || 0);

                return (
                  <div
                    key={idx}
                    className="p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-white">
                        Dr(a). {doc.doctor_nombre}
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {doc.total_citas} citas agendadas
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                      <div className="p-2 bg-slate-800/60 rounded-lg flex items-center gap-2">
                        <Clock className="w-4 h-4 text-primary-400" />
                        <div>
                          <div className="text-[10px] text-slate-400">Tiempo Medio en Sillón</div>
                          <div className="font-mono font-bold text-white">
                            {doc.tiempo_promedio_sillon_minutos || 45} min
                          </div>
                        </div>
                      </div>

                      <div className="p-2 bg-slate-800/60 rounded-lg flex items-center gap-2">
                        <AlertTriangle className={`w-4 h-4 ${noShow > 15 ? 'text-rose-400' : 'text-emerald-400'}`} />
                        <div>
                          <div className="text-[10px] text-slate-400">Tasa No-Show (Ausentismo)</div>
                          <div className={`font-mono font-bold ${noShow > 15 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {noShow}%
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
