import React, { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, BarChart3, Banknote, TrendingUp, Users } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import { aFechaLocal, aPeriodoApi, inicioDelDia } from '../utils/fechas';
import { useMoneda } from '../context/MonedaContext';

const TARJETA = 'bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm';
const CELDA = 'py-2 px-3';
const ACTUALIZANDO = 'transition-opacity opacity-50';

const sumarDias = (d, dias) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + dias);
const lunesDe = (d) => sumarDias(d, -((d.getDay() + 6) % 7));
const fechaVisible = (d) => d.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });

// Los periodos en curso terminan hoy, para no contar como pendientes las citas futuras
const PERIODOS = [
  { id: 'hoy', etiqueta: 'Hoy', rango: (h) => [h, h] },
  { id: 'semana', etiqueta: 'Esta semana', rango: (h) => [lunesDe(h), h] },
  { id: 'semana_pasada', etiqueta: 'Semana pasada', rango: (h) => [sumarDias(lunesDe(h), -7), sumarDias(lunesDe(h), -1)] },
  { id: 'mes', etiqueta: 'Mes actual', rango: (h) => [new Date(h.getFullYear(), h.getMonth(), 1), h] },
  { id: 'mes_pasado', etiqueta: 'Mes pasado', rango: (h) => [new Date(h.getFullYear(), h.getMonth() - 1, 1), new Date(h.getFullYear(), h.getMonth(), 0)] },
  { id: 'ultimos_30', etiqueta: 'Últimos 30 días', rango: (h) => [sumarDias(h, -29), h] },
  { id: 'anio', etiqueta: 'Este año', rango: (h) => [new Date(h.getFullYear(), 0, 1), h] },
  { id: 'todo', etiqueta: 'Todo', rango: () => [null, null] },
];

function rangoDePeriodo(id) {
  const [desde, hasta] = PERIODOS.find((p) => p.id === id).rango(inicioDelDia(new Date()));
  return { id, desde, hasta };
}

function textoDelRango({ desde, hasta }) {
  if (!desde) return 'Todo el historial';
  if (desde.getTime() === hasta.getTime()) return fechaVisible(desde);
  return `Del ${fechaVisible(desde)} al ${fechaVisible(hasta)}`;
}

function SelectorPeriodo({ filtro, onCambiar }) {
  const [personalizando, setPersonalizando] = useState(false);
  const [textos, setTextos] = useState({ desde: '', hasta: '' });
  const invertido = Boolean(textos.desde && textos.hasta && textos.desde > textos.hasta);

  const abrirPersonalizado = () => {
    const hoy = aFechaLocal();
    setTextos({
      desde: filtro.desde ? aFechaLocal(filtro.desde) : hoy,
      hasta: filtro.hasta ? aFechaLocal(filtro.hasta) : hoy,
    });
    setPersonalizando(true);
  };

  const cambiarFecha = (campo, valor) => {
    const nuevos = { ...textos, [campo]: valor };
    setTextos(nuevos);
    // Un rango incompleto o invertido no se aplica: sigue visible el último válido
    if (nuevos.desde && nuevos.hasta && nuevos.desde <= nuevos.hasta) {
      onCambiar({
        id: 'personalizado',
        desde: new Date(`${nuevos.desde}T00:00:00`),
        hasta: new Date(`${nuevos.hasta}T00:00:00`),
      });
    }
  };

  const claseBoton = (activo) => `px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
    activo
      ? 'bg-primary-600 border-primary-600 text-white'
      : 'bg-white dark:bg-slate-800/70 border-slate-200 dark:border-slate-700/60 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/60'
  }`;
  const claseFecha = 'px-2 py-1.5 rounded-lg text-xs border border-slate-200 dark:border-slate-700/60 bg-white dark:bg-slate-800/70 text-slate-900 dark:text-white';

  return (
    <div className="space-y-2">
      <div role="group" aria-label="Periodo del reporte" className="flex flex-wrap items-center gap-2">
        {PERIODOS.map((p) => (
          <button
            key={p.id}
            type="button"
            aria-pressed={!personalizando && filtro.id === p.id}
            className={claseBoton(!personalizando && filtro.id === p.id)}
            onClick={() => { setPersonalizando(false); onCambiar(rangoDePeriodo(p.id)); }}
          >
            {p.etiqueta}
          </button>
        ))}
        <button type="button" aria-pressed={personalizando} className={claseBoton(personalizando)} onClick={abrirPersonalizado}>
          Personalizado
        </button>
      </div>
      {personalizando && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
          <label className="flex items-center gap-1.5">
            Desde
            <input type="date" value={textos.desde} onChange={(e) => cambiarFecha('desde', e.target.value)} className={claseFecha} />
          </label>
          <label className="flex items-center gap-1.5">
            Hasta
            <input type="date" value={textos.hasta} onChange={(e) => cambiarFecha('hasta', e.target.value)} className={claseFecha} />
          </label>
          {invertido && <span role="alert" className="text-rose-600 dark:text-rose-400">La fecha inicial no puede ser posterior a la final</span>}
        </div>
      )}
      <p className="text-xs text-slate-500 dark:text-slate-400" data-testid="rango-reporte">{textoDelRango(filtro)}</p>
    </div>
  );
}

// El gráfico lo dibuja matplotlib en el servidor; la petición lleva la sesión, por eso no es un <img> directo
function GraficoServidor({ nombre, descripcion, tema, periodo }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState('');
  const [actualizando, setActualizando] = useState(true);

  useEffect(() => {
    let vigente = true;
    setActualizando(true);
    api.getGraficoReporte(nombre, tema, periodo)
      .then((blob) => {
        if (!vigente) return;
        setUrl(URL.createObjectURL(blob));
        setError('');
      })
      .catch((err) => vigente && setError(err.message || 'No se pudo generar el gráfico'))
      .finally(() => vigente && setActualizando(false));
    return () => { vigente = false; };
  }, [nombre, tema, periodo]);

  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  if (error) return <p className="py-8 text-center text-rose-600 dark:text-rose-400 text-xs">{error}</p>;
  if (!url) return <p className="py-8 text-center text-slate-500 dark:text-slate-400 text-xs">Generando gráfico...</p>;
  // Mientras llega el periodo nuevo se conserva el anterior atenuado, sin saltos en la página
  return <img src={url} alt={descripcion} aria-busy={actualizando} className={`w-full h-auto ${actualizando ? ACTUALIZANDO : 'transition-opacity'}`} />;
}

export default function ReportesBIView() {
  const { moneda } = useMoneda();
  const { isDark } = useTheme();
  const tema = isDark ? 'oscuro' : 'claro';
  const [filtro, setFiltro] = useState(() => rangoDePeriodo('mes'));
  const periodo = useMemo(() => (filtro.desde ? aPeriodoApi(filtro.desde, filtro.hasta) : {}), [filtro]);
  const [demanda, setDemanda] = useState([]);
  const [productividad, setProductividad] = useState([]);
  const [finanzas, setFinanzas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let vigente = true;
    const cargar = async () => {
      setLoading(true);
      setError('');
      try {
        const [dRes, pRes, fRes] = await Promise.all([
          api.getReporteDemanda(10, periodo),
          api.getReporteProductividad(periodo),
          api.getReporteFinanciero(periodo),
        ]);
        if (!vigente) return;
        setDemanda(dRes?.ranking_tratamientos || []);
        setProductividad((pRes?.doctores || []).filter((d) => d.total_citas > 0).sort((a, b) => b.citas_finalizadas - a.citas_finalizadas));
        setFinanzas(fRes);
      } catch (err) {
        if (!vigente) return;
        // Sin datos del periodo elegido no se dejan a la vista los de otro
        setDemanda([]);
        setProductividad([]);
        setFinanzas(null);
        setError(err.message || 'Error cargando reportes analíticos');
      } finally {
        if (vigente) setLoading(false);
      }
    };
    cargar();
    return () => { vigente = false; };
  }, [periodo]);

  const margen = Number(finanzas?.balance_neto_operativo || 0);
  const primero = demanda[0];
  const descripcionDemanda = primero
    ? `Barras de los ${demanda.length} tratamientos más realizados. El primero es ${primero.nombre}, con ${primero.cantidad_realizada}. Los valores están en la tabla inferior.`
    : 'Sin tratamientos completados en este periodo.';
  const descripcionProductividad = productividad.length
    ? `Citas atendidas, minutos por cita y ausentismo de ${Math.min(productividad.length, 10)} profesionales. Los valores están en la tabla inferior.`
    : 'Sin citas en este periodo.';
  const valorMetrica = (valor) => {
    if (finanzas) return moneda(valor);
    return loading ? '...' : '—';
  };

  const metricas = [
    { titulo: 'Ingresos Facturados', valor: finanzas?.total_ingresos, nota: 'Cobros en todos los medios, sin pagos anulados', Icono: TrendingUp },
    { titulo: 'Egresos & Costos', valor: finanzas?.total_egresos, nota: 'Laboratorio, insumos, sueldos y gastos menores', Icono: Banknote },
    { titulo: 'Margen Neto Operativo', valor: margen, nota: 'Ingresos menos egresos', Icono: Activity },
  ];

  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Reportes Analíticos & Business Intelligence</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Demanda de tratamientos, productividad médica y resultado financiero</p>
      </div>

      <SelectorPeriodo filtro={filtro} onCambiar={setFiltro} />

      {error && (
        <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div aria-busy={loading} className={`grid grid-cols-1 md:grid-cols-3 gap-4 ${loading ? ACTUALIZANDO : 'transition-opacity'}`}>
        {metricas.map(({ titulo, valor, nota, Icono }) => (
          <div key={titulo} className="bg-white dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</span>
              <Icono className="w-5 h-5 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{valorMetrica(valor)}</div>
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
              Procedimientos realizados en el periodo, de mayor a menor
            </p>
          </div>
          <GraficoServidor nombre="tratamientos-demanda" descripcion={descripcionDemanda} tema={tema} periodo={periodo} />
          {demanda.length > 0 && (
            <div className={`overflow-x-auto ${loading ? ACTUALIZANDO : 'transition-opacity'}`}>
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
          <GraficoServidor nombre="productividad-doctores" descripcion={descripcionProductividad} tema={tema} periodo={periodo} />
          {productividad.length > 0 && (
            <div className={`overflow-x-auto ${loading ? ACTUALIZANDO : 'transition-opacity'}`}>
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
