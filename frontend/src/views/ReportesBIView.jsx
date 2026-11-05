import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, BarChart3, DollarSign, TrendingUp, Users } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';

const moneda = (valor) => `$${Number(valor || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}`;
const TARJETA = 'bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm';
const CELDA = 'py-2 px-3';

// El gráfico lo dibuja matplotlib en el servidor; la petición lleva la sesión, por eso no es un <img> directo
function GraficoServidor({ nombre, descripcion, tema }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let vigente = true;
    let urlCreada = null;
    api.getGraficoReporte(nombre, tema)
      .then((blob) => {
        if (!vigente) return;
        urlCreada = URL.createObjectURL(blob);
        setUrl(urlCreada);
        setError('');
      })
      .catch((err) => vigente && setError(err.message || 'No se pudo generar el gráfico'));
    return () => {
      vigente = false;
      if (urlCreada) URL.revokeObjectURL(urlCreada);
    };
  }, [nombre, tema]);

  if (error) return <p className="py-8 text-center text-rose-600 dark:text-rose-400 text-xs">{error}</p>;
  if (!url) return <p className="py-8 text-center text-slate-500 dark:text-slate-400 text-xs">Generando gráfico...</p>;
  return <img src={url} alt={descripcion} className="w-full h-auto" />;
}

export default function ReportesBIView() {
  const { isDark } = useTheme();
  const tema = isDark ? 'oscuro' : 'claro';
  const [demanda, setDemanda] = useState([]);
  const [productividad, setProductividad] = useState([]);
  const [finanzas, setFinanzas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const cargar = async () => {
      try {
        const [dRes, pRes, fRes] = await Promise.all([
          api.getReporteDemanda(10),
          api.getReporteProductividad(),
          api.getReporteFinanciero(),
        ]);
        setDemanda(dRes?.ranking_tratamientos || []);
        setProductividad((pRes?.doctores || []).filter((d) => d.total_citas > 0).sort((a, b) => b.citas_finalizadas - a.citas_finalizadas));
        setFinanzas(fRes);
      } catch (err) {
        setError(err.message || 'Error cargando reportes analíticos');
      } finally {
        setLoading(false);
      }
    };
    cargar();
  }, []);

  const margen = Number(finanzas?.balance_neto_operativo || 0);
  const primero = demanda[0];
  const descripcionDemanda = primero
    ? `Barras de los ${demanda.length} tratamientos más realizados. El primero es ${primero.nombre}, con ${primero.cantidad_realizada}. Los valores están en la tabla inferior.`
    : 'Todavía no hay tratamientos completados.';
  const descripcionProductividad = productividad.length
    ? `Citas atendidas, minutos por cita y ausentismo de ${Math.min(productividad.length, 10)} profesionales. Los valores están en la tabla inferior.`
    : 'Todavía no hay citas registradas.';

  const metricas = [
    { titulo: 'Ingresos Facturados', valor: finanzas?.total_ingresos, nota: 'Cobros en todos los medios, sin pagos anulados', Icono: TrendingUp },
    { titulo: 'Egresos & Costos', valor: finanzas?.total_egresos, nota: 'Laboratorio, insumos, sueldos y gastos menores', Icono: DollarSign },
    { titulo: 'Margen Neto Operativo', valor: margen, nota: 'Ingresos menos egresos', Icono: Activity },
  ];

  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Reportes Analíticos & Business Intelligence</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Demanda de tratamientos, productividad médica y resultado financiero (HU-14)</p>
      </div>

      {error && (
        <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metricas.map(({ titulo, valor, nota, Icono }) => (
          <div key={titulo} className="bg-white dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</span>
              <Icono className="w-5 h-5 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{loading ? '...' : moneda(valor)}</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">{nota}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className={TARJETA}>
          <div className="pb-3 border-b border-slate-200 dark:border-slate-700/60">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              Tratamientos Más Demandados
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Procedimientos completados, de mayor a menor
            </p>
          </div>
          <GraficoServidor nombre="tratamientos-demanda" descripcion={descripcionDemanda} tema={tema} />
          {demanda.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
                <thead className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700/60">
                  <tr>
                    <th className={CELDA}>Tratamiento</th>
                    <th className={`${CELDA} text-right`}>Cantidad</th>
                    <th className={`${CELDA} text-right`}>Facturación</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 tabular-nums">
                  {demanda.map((item) => (
                    <tr key={item.tratamiento_id}>
                      <td className={CELDA}>{item.nombre}</td>
                      <td className={`${CELDA} text-right`}>{item.cantidad_realizada}</td>
                      <td className={`${CELDA} text-right`}>{moneda(item.facturacion_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className={TARJETA}>
          <div className="pb-3 border-b border-slate-200 dark:border-slate-700/60">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              Productividad Médica
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Los 10 profesionales con más citas atendidas; cada columna tiene su propia escala</p>
          </div>
          <GraficoServidor nombre="productividad-doctores" descripcion={descripcionProductividad} tema={tema} />
          {productividad.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
                <thead className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700/60">
                  <tr>
                    <th className={CELDA}>Profesional</th>
                    <th className={`${CELDA} text-right`}>Citas</th>
                    <th className={`${CELDA} text-right`}>Atendidas</th>
                    <th className={`${CELDA} text-right`}>Min. por cita</th>
                    <th className={`${CELDA} text-right`}>Horas en sillón</th>
                    <th className={`${CELDA} text-right`}>Ausentismo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 tabular-nums">
                  {productividad.map((d) => (
                    <tr key={d.doctor_id}>
                      <td className={CELDA}>{d.doctor_nombre}</td>
                      <td className={`${CELDA} text-right`}>{d.total_citas}</td>
                      <td className={`${CELDA} text-right`}>{d.citas_finalizadas}</td>
                      <td className={`${CELDA} text-right`}>{d.promedio_minutos_por_cita}</td>
                      <td className={`${CELDA} text-right`}>{(d.tiempo_total_sillon_minutos / 60).toFixed(1)}</td>
                      <td className={`${CELDA} text-right`}>{d.tasa_ausentismo_porcentaje}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
