import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarCheck, ChevronRight, Plus, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import ErrorModal from './ErrorModal';
import { useMoneda } from '../context/MonedaContext';

const CAMPO_BASE =
  'px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500';
const CAMPO = `w-full ${CAMPO_BASE}`;
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';

const lineasDe = (cobro) =>
  cobro.lineas.map((l) => ({
    id: l.id,
    concepto: l.concepto,
    monto: Number(l.monto).toFixed(2),
    costo_referencia: l.costo_referencia,
    aplica_a_plan: l.aplica_a_plan,
    plan_titulo: l.plan_titulo,
    item_plan_id: l.item_plan_id,
  }));

const fechaCorta = (valor) => (valor ? new Date(valor).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'Sin fecha');

export default function CobrosCitaPanel({ cobroInicialId, recarga, doctores, onCobroCerrado, onAviso }) {
  const { moneda } = useMoneda();
  const [pendientes, setPendientes] = useState([]);
  const [cobro, setCobro] = useState(null);
  const [lineas, setLineas] = useState([]);
  const [pago, setPago] = useState({ metodo_pago: 'EFECTIVO', referencia_comprobante: '', doctor_comision_id: '', observaciones: '' });
  const [motivoCierre, setMotivoCierre] = useState('');
  const [cerrando, setCerrando] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');

  const cargar = async () => {
    try {
      const datos = await api.getCobrosCita('?estado=PENDIENTE');
      setPendientes(Array.isArray(datos) ? datos : []);
    } catch (err) {
      onAviso?.(err.message || 'Error cargando los cobros de citas', true);
    }
  };

  useEffect(() => {
    cargar();
  }, [recarga]);

  const abrir = (datos) => {
    setError('');
    setCobro(datos);
    setLineas(lineasDe(datos));
    setPago({ metodo_pago: 'EFECTIVO', referencia_comprobante: '', doctor_comision_id: datos.doctor_id, observaciones: '' });
    setMotivoCierre(Number(datos.total) > 0 ? '' : 'Tratamiento ya cubierto por abonos anteriores');
    setCerrando(false);
  };

  // Enlace directo desde la agenda
  useEffect(() => {
    if (!cobroInicialId) return;
    api.getCobroCita(cobroInicialId)
      .then((datos) => {
        if (datos.estado === 'PENDIENTE') abrir(datos);
        else onAviso?.('Este cobro ya fue cerrado');
      })
      .catch((err) => onAviso?.(err.message || 'No se encontró el cobro', true));
  }, [cobroInicialId]);

  const total = lineas.reduce((suma, l) => suma + (Number(l.monto) || 0), 0);
  const cambiarLinea = (indice, campo, valor) => {
    setLineas(lineas.map((l, i) => (i === indice ? { ...l, [campo]: valor } : l)));
  };
  const lineasParaEnviar = () =>
    lineas.map((l) => ({ ...(l.id ? { id: l.id } : {}), concepto: l.concepto, monto: Number(Number(l.monto).toFixed(2)) }));

  const ejecutar = async (accion, mensaje) => {
    setError('');
    setProcesando(true);
    try {
      const resultado = await accion();
      await cargar();
      if (resultado?.estado !== 'PENDIENTE') {
        setCobro(null);
        onCobroCerrado?.(resultado.paciente_id, mensaje);
      } else {
        abrir(resultado);
        onAviso?.(mensaje);
      }
    } catch (err) {
      setError(err.message || 'No se pudo completar la operación');
    } finally {
      setProcesando(false);
    }
  };

  const guardar = () => ejecutar(() => api.updateCobroCita(cobro.id, { lineas: lineasParaEnviar() }), 'Cuenta actualizada; sigue pendiente de pago');

  const confirmar = (e) => {
    e.preventDefault();
    ejecutar(
      () =>
        api.confirmarCobroCita(cobro.id, {
          lineas: lineasParaEnviar(),
          metodo_pago: pago.metodo_pago,
          referencia_comprobante: pago.referencia_comprobante || null,
          doctor_comision_id: pago.doctor_comision_id || null,
          observaciones: pago.observaciones || null,
        }),
      `Pago de ${moneda(total)} confirmado`
    );
  };

  const cerrarSinPago = () => {
    if (!motivoCierre.trim()) {
      setError('Indica el motivo para cerrar el cobro sin pago');
      return;
    }
    ejecutar(() => api.cerrarCobroCitaSinPago(cobro.id, motivoCierre.trim()), 'Cobro cerrado sin pago');
  };

  return (
    <>
      {pendientes.length > 0 && (
        <section
          aria-label="Cobros de citas pendientes"
          className="bg-white dark:bg-slate-800/60 border border-amber-300/70 dark:border-amber-500/30 rounded-2xl p-5 space-y-3 shadow-sm"
        >
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <CalendarCheck className="w-5 h-5 text-amber-500" />
            Cobros de citas pendientes ({pendientes.length})
          </h2>
          <ul className="divide-y divide-slate-100 dark:divide-slate-700/40">
            {pendientes.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => abrir(c)}
                  className="w-full py-3 flex items-center justify-between gap-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/20 rounded-lg px-2 transition"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-slate-900 dark:text-white truncate">{c.paciente_nombre}</span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">
                      {fechaCorta(c.fecha_cita)} · Dr(a). {c.doctor_nombre} · {c.lineas.map((l) => l.concepto).join(', ')}
                    </span>
                  </span>
                  <span className="flex items-center gap-2 flex-shrink-0">
                    <span className="font-mono font-bold text-slate-900 dark:text-white">{moneda(c.total)}</span>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {cobro && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[92vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Cobro de la cita</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              {cobro.paciente_nombre} · {fechaCorta(cobro.fecha_cita)} · Dr(a). {cobro.doctor_nombre}
            </p>

            <form onSubmit={confirmar} className="space-y-4">
              <ErrorModal mensaje={error} />

              <div className="space-y-2">
                <span className={ETIQUETA}>Detalle de la cuenta</span>
                {lineas.map((linea, i) => {
                  const cubierto = linea.costo_referencia != null && Number(linea.costo_referencia) > Number(linea.monto);
                  return (
                    <div key={linea.id || `nueva-${i}`} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/40 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          required
                          maxLength={255}
                          aria-label={`Concepto ${i + 1}`}
                          value={linea.concepto}
                          onChange={(e) => cambiarLinea(i, 'concepto', e.target.value)}
                          className={`${CAMPO_BASE} flex-1 min-w-0`}
                        />
                        <input
                          type="number"
                          required
                          min="0"
                          step="0.01"
                          aria-label={`Monto ${i + 1}`}
                          value={linea.monto}
                          onChange={(e) => cambiarLinea(i, 'monto', e.target.value)}
                          className={`${CAMPO_BASE} w-28 flex-shrink-0 font-mono font-bold text-right`}
                        />
                        <button
                          type="button"
                          disabled={lineas.length === 1}
                          aria-label={`Quitar ${linea.concepto}`}
                          title="Quitar línea"
                          onClick={() => setLineas(lineas.filter((_, indice) => indice !== i))}
                          className="p-2 rounded-lg text-slate-500 hover:text-rose-600 disabled:opacity-30 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        {linea.aplica_a_plan ? `Abona al plan «${linea.plan_titulo}»` : 'Cobro directo: no afecta el saldo de los planes'}
                        {cubierto && ` · Costo ${moneda(linea.costo_referencia)}; la diferencia ya fue abonada o sigue en el saldo del plan`}
                      </p>
                    </div>
                  );
                })}
                <button
                  type="button"
                  onClick={() => setLineas([...lineas, { concepto: '', monto: '0.00', aplica_a_plan: false }])}
                  className="text-xs font-semibold text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Agregar concepto
                </button>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30">
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Total a cobrar</span>
                <span className="text-xl font-bold font-mono text-emerald-700 dark:text-emerald-400">{moneda(total)}</span>
              </div>

              {total > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="cobro-cita-medio" className={ETIQUETA}>Medio de Pago *</label>
                    <select id="cobro-cita-medio" value={pago.metodo_pago} onChange={(e) => setPago({ ...pago, metodo_pago: e.target.value })} className={CAMPO}>
                      <option value="EFECTIVO">Efectivo (Ingresa a gaveta de caja)</option>
                      <option value="TARJETA_DEBITO">Tarjeta Débito (POS)</option>
                      <option value="TARJETA_CREDITO">Tarjeta Crédito</option>
                      <option value="TRANSFERENCIA">Transferencia Bancaria</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="cobro-cita-doctor" className={ETIQUETA}>Doctor que recibe la comisión</label>
                    <select id="cobro-cita-doctor" value={pago.doctor_comision_id} onChange={(e) => setPago({ ...pago, doctor_comision_id: e.target.value })} className={CAMPO}>
                      <option value="">Sin comisión</option>
                      {doctores.map((d) => (
                        <option key={d.id} value={d.id}>Dr(a). {d.nombre_completo}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="cobro-cita-comprobante" className={ETIQUETA}>Nº Comprobante / Voucher</label>
                    <input id="cobro-cita-comprobante" type="text" value={pago.referencia_comprobante} onChange={(e) => setPago({ ...pago, referencia_comprobante: e.target.value })} className={`${CAMPO} font-mono`} />
                  </div>
                  <div>
                    <label htmlFor="cobro-cita-notas" className={ETIQUETA}>Observaciones</label>
                    <input id="cobro-cita-notas" type="text" value={pago.observaciones} onChange={(e) => setPago({ ...pago, observaciones: e.target.value })} className={CAMPO} />
                  </div>
                </div>
              )}

              {(cerrando || total <= 0) && (
                <div>
                  <label htmlFor="cobro-cita-motivo" className={ETIQUETA}>Motivo para cerrar sin pago *</label>
                  <input
                    id="cobro-cita-motivo"
                    type="text"
                    maxLength={500}
                    placeholder="Cortesía, ya cubierto por abonos..."
                    value={motivoCierre}
                    onChange={(e) => setMotivoCierre(e.target.value)}
                    className={CAMPO}
                  />
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  disabled={procesando}
                  onClick={() => (cerrando || total <= 0 ? cerrarSinPago() : setCerrando(true))}
                  className="px-3 py-2 bg-rose-50 hover:bg-rose-100 dark:bg-rose-500/20 dark:hover:bg-rose-500/30 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-500/30 text-xs font-semibold rounded-xl transition disabled:opacity-50"
                >
                  {cerrando || total <= 0 ? 'Confirmar cierre sin pago' : 'Cerrar sin pago'}
                </button>
                <div className="flex flex-wrap justify-end gap-2">
                  <button type="button" onClick={() => setCobro(null)} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs transition">
                    Volver
                  </button>
                  <button type="button" disabled={procesando} onClick={guardar} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-800 dark:text-slate-200 rounded-xl text-xs font-semibold transition disabled:opacity-50">
                    Guardar cambios
                  </button>
                  {total > 0 && (
                    <button type="submit" disabled={procesando} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-emerald-600/20 disabled:opacity-50">
                      Confirmar pago de {moneda(total)}
                    </button>
                  )}
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

export function EnlaceCobroCita({ cita }) {
  if (cita.cobro_estado === 'PENDIENTE') {
    return (
      <Link
        to={`/cobranzas?cobro=${cita.cobro_id}`}
        onClick={(e) => e.stopPropagation()}
        className="w-full py-1.5 mt-1 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-800 dark:text-amber-300 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1"
      >
        Revisar y cobrar
      </Link>
    );
  }
  if (cita.cobro_estado === 'PAGADO') {
    return <div className="w-full text-center text-[11px] font-semibold text-slate-600 dark:text-slate-400 mt-1">Cobro pagado</div>;
  }
  return null;
}
