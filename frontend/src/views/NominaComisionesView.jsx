import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Award, Plus, User, AlertCircle, CheckCircle2, Receipt, Pencil } from 'lucide-react';

const moneda = (valor) => `$${Number(valor || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}`;
const descuento = (valor) => (Number(valor) > 0 ? `-${moneda(valor)}` : moneda(0));
const ENTRADA = 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';
const OPCION = 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white';

const TIPOS_PAGO = {
  COMISION_TRATAMIENTOS: 'Liquidación de comisiones',
  ADELANTO: 'Adelanto / vale',
  SUELDO_MENSUAL: 'Sueldo mensual',
  QUINCENA: 'Quincena',
  BONO: 'Bono',
};
const TIPOS_CONTRATO = {
  SUELDO_FIJO_MENSUAL: 'Sueldo fijo mensual',
  SUELDO_FIJO_QUINCENAL: 'Sueldo fijo quincenal',
  POR_HORA: 'Por hora',
  PORCENTAJE_COMISION: 'Porcentaje de comisión',
  MIXTO_BASE_MAS_COMISION: 'Sueldo base más comisión',
};
const esSueldo = (tipo) => tipo === 'SUELDO_MENSUAL' || tipo === 'QUINCENA';
const CONTRATOS_CON_COMISION = ['PORCENTAJE_COMISION', 'MIXTO_BASE_MAS_COMISION'];

function Metrica({ titulo, valor, nota, resaltar = false }) {
  const fondo = resaltar
    ? 'bg-primary-50 dark:bg-primary-600/10 border-primary-200 dark:border-primary-500/30'
    : 'bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-700/50';
  return (
    <div className={`p-4 border rounded-xl ${fondo}`}>
      <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">{titulo}</span>
      <div className="text-xl font-bold text-slate-900 dark:text-white font-mono">{valor}</div>
      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">{nota}</div>
    </div>
  );
}

export default function NominaComisionesView() {
  const { isAdmin, tienePermiso } = useAuth();
  const [personal, setPersonal] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [liquidacion, setLiquidacion] = useState(null);
  const [pagos, setPagos] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formPago, setFormPago] = useState(null);
  const [formContrato, setFormContrato] = useState(null);

  const empleado = personal.find((p) => p.usuario_id === selectedId);
  const contrato = empleado?.contrato;
  const tieneComision = Boolean(empleado?.doctor_id)
    || CONTRATOS_CON_COMISION.includes(contrato?.tipo_remuneracion)
    || Number(liquidacion?.porcentaje_pactado) > 0;
  const tieneSueldo = !tieneComision || Number(liquidacion?.salario_base) > 0;
  const saldoComision = Number(liquidacion?.saldo_comision_por_pagar || 0);
  const adelantosPendientes = Number(liquidacion?.total_anticipos || 0);
  const salarioBase = Number(liquidacion?.salario_base || 0);

  const cargarPersonal = async () => {
    try {
      const lista = await api.getPersonalNomina();
      setPersonal(Array.isArray(lista) ? lista : []);
      setSelectedId((actual) => actual || lista[0]?.usuario_id || '');
    } catch (err) {
      setError(err.message || 'Error cargando el personal');
    }
  };

  const cargarEmpleado = async () => {
    if (!selectedId) return;
    setError('');
    try {
      const [liq, historial] = await Promise.all([api.getLiquidacion(selectedId), api.getPagosEmpleados(selectedId)]);
      setLiquidacion(liq);
      setPagos(Array.isArray(historial) ? historial : []);
    } catch (err) {
      setError(err.message || 'Error cargando la liquidación');
    }
  };

  useEffect(() => { cargarPersonal(); }, []);
  useEffect(() => { cargarEmpleado(); }, [selectedId]);

  const valoresDeTipo = (tipo) => {
    if (tipo === 'COMISION_TRATAMIENTOS') return { monto: saldoComision > 0 ? saldoComision.toFixed(2) : '', base: '', descuento: '' };
    if (esSueldo(tipo)) {
      const base = tipo === 'QUINCENA' ? salarioBase / 2 : salarioBase;
      return { monto: '', base: base > 0 ? base.toFixed(2) : '', descuento: Math.min(adelantosPendientes, base).toFixed(2) };
    }
    return { monto: '', base: '', descuento: '' };
  };

  const abrirPago = () => {
    const tipo = tieneComision ? 'COMISION_TRATAMIENTOS' : 'SUELDO_MENSUAL';
    setError('');
    setFormPago({ tipo_pago: tipo, descontar_de_caja: true, observaciones: '', ...valoresDeTipo(tipo) });
  };

  const netoDeSueldo = formPago ? Number(formPago.base || 0) - Number(formPago.descuento || 0) : 0;

  const avisar = (mensaje) => {
    setSuccess(mensaje);
    setTimeout(() => setSuccess(''), 3000);
  };

  const registrarPago = async (e) => {
    e.preventDefault();
    setError('');
    const sueldo = esSueldo(formPago.tipo_pago);
    try {
      await api.registrarPagoEmpleado({
        usuario_empleado_id: selectedId,
        tipo_pago: formPago.tipo_pago,
        monto_base: sueldo ? Number(formPago.base || 0) : 0,
        deducciones_descuentos: sueldo ? Number(formPago.descuento || 0) : 0,
        monto_neto_pagado: sueldo ? Number(netoDeSueldo.toFixed(2)) : Number(formPago.monto),
        metodo_pago: formPago.descontar_de_caja ? 'EFECTIVO_CAJA' : 'TRANSFERENCIA',
        observaciones: formPago.observaciones,
      });
      setFormPago(null);
      avisar('Pago registrado correctamente');
      cargarEmpleado();
    } catch (err) {
      setError(err.message || 'Error al registrar el pago');
    }
  };

  const abrirContrato = () => {
    setError('');
    setFormContrato({
      tipo_remuneracion: contrato?.tipo_remuneracion || 'SUELDO_FIJO_MENSUAL',
      salario_base: contrato?.salario_base ?? 0,
      porcentaje_comision: contrato?.porcentaje_comision ?? 0,
      valor_hora: contrato?.valor_hora ?? 0,
    });
  };

  const guardarContrato = async (e) => {
    e.preventDefault();
    setError('');
    const datos = {
      tipo_remuneracion: formContrato.tipo_remuneracion,
      salario_base: Number(formContrato.salario_base || 0),
      porcentaje_comision: Number(formContrato.porcentaje_comision || 0),
      valor_hora: Number(formContrato.valor_hora || 0),
    };
    try {
      if (contrato) await api.actualizarContrato(contrato.id, datos);
      else await api.crearContrato({ usuario_id: selectedId, ...datos });
      setFormContrato(null);
      avisar('Contrato guardado correctamente');
      await cargarPersonal();
      cargarEmpleado();
    } catch (err) {
      setError(err.message || 'Error al guardar el contrato');
    }
  };

  const modalAbierto = formPago || formContrato;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Nómina & Comisiones</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sueldos, adelantos y comisiones de todo el personal (HU-12)</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2 rounded-xl shadow-sm">
            <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            <select
              aria-label="Empleado"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="bg-transparent text-slate-900 dark:text-white text-xs font-semibold focus:outline-none cursor-pointer"
            >
              {personal.map((p) => (
                <option key={p.usuario_id} value={p.usuario_id} className={OPCION}>
                  {p.nombre_completo} ({p.rol})
                </option>
              ))}
            </select>
          </div>

          {tienePermiso('EMPLEADOS_PAGOS') && (
            <button
              type="button"
              onClick={abrirPago}
              className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              Registrar Pago / Adelanto
            </button>
          )}
        </div>
      </div>

      {error && !modalAbierto && (
        <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-500 dark:text-rose-400 text-xs flex items-center gap-2">
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

      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-6 space-y-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-700/60 gap-4">
          <div>
            <span className="text-xs font-bold text-teal-600 dark:text-teal-400 uppercase tracking-wider flex items-center gap-1">
              <Award className="w-4 h-4" /> Contrato
            </span>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">{empleado?.nombre_completo}</h2>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {empleado?.rol}
              {empleado?.especialidad ? ` · ${empleado.especialidad}` : ''}
              {' · '}
              {contrato ? TIPOS_CONTRATO[contrato.tipo_remuneracion] : 'Sin contrato registrado'}
            </div>
          </div>
          {isAdmin && (
            <button
              type="button"
              onClick={abrirContrato}
              className="self-start sm:self-auto px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <Pencil className="w-3.5 h-3.5" />
              {contrato ? 'Editar contrato' : 'Registrar contrato'}
            </button>
          )}
        </div>

        {tieneSueldo && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Metrica titulo="Sueldo pactado" valor={moneda(salarioBase)} nota={contrato ? 'Según su contrato' : 'Registra un contrato para calcularlo'} />
            <Metrica titulo="Adelantos pendientes" valor={moneda(adelantosPendientes)} nota="Se descuentan al pagar el sueldo" />
            <Metrica titulo="Próximo sueldo a pagar" valor={moneda(Math.max(salarioBase - adelantosPendientes, 0))} nota="Sueldo menos adelantos pendientes" resaltar />
          </div>
        )}

        {tieneComision && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <Metrica titulo="Total cobrado" valor={moneda(liquidacion?.total_cobrado_por_sus_tratamientos)} nota="Tratamientos pagados por pacientes" />
              <Metrica titulo="Comisión generada" valor={moneda(liquidacion?.comision_bruta_generada)} nota={`${Number(liquidacion?.porcentaje_pactado || 0)}% de lo cobrado`} />
              <Metrica titulo="Comisiones liquidadas" valor={descuento(liquidacion?.comisiones_ya_liquidadas)} nota="Ya pagadas" />
              <Metrica titulo="Adelantos pendientes" valor={descuento(adelantosPendientes)} nota="Se descuentan de la comisión" />
              {saldoComision < 0 ? (
                <Metrica titulo="Pagado de más" valor={moneda(-saldoComision)} nota="Se compensa con sus próximas comisiones" resaltar />
              ) : (
                <Metrica titulo="Saldo por pagar" valor={moneda(saldoComision)} nota="Máximo que se puede liquidar" resaltar />
              )}
            </div>
            {saldoComision < 0 && (
              <div role="status" className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-700 dark:text-amber-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                Se pagó más comisión de la generada, normalmente porque se anuló un cobro ya liquidado. No se podrá liquidar más hasta compensar {moneda(-saldoComision)}.
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2 pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <Receipt className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          Historial de Pagos
        </h3>

        {pagos.length === 0 ? (
          <div className="py-8 text-center text-slate-500 dark:text-slate-400 text-xs">No hay pagos registrados a esta persona.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Fecha / Hora</th>
                  <th className="py-3 px-4">Tipo</th>
                  <th className="py-3 px-4 text-center">De caja</th>
                  <th className="py-3 px-4">Observaciones</th>
                  <th className="py-3 px-4 text-right">Adelanto descontado</th>
                  <th className="py-3 px-4 text-right">Monto pagado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {pagos.map((pago) => (
                  <tr key={pago.id}>
                    <td className="py-3 px-4 font-mono text-slate-500 dark:text-slate-400">{new Date(pago.fecha_hora_pago).toLocaleString()}</td>
                    <td className="py-3 px-4">{TIPOS_PAGO[pago.tipo_pago] || pago.tipo_pago}</td>
                    <td className="py-3 px-4 text-center">{pago.metodo_pago === 'EFECTIVO_CAJA' && Number(pago.monto_neto_pagado) > 0 ? 'Sí' : 'No'}</td>
                    <td className="py-3 px-4 text-slate-500 dark:text-slate-400">{pago.observaciones || '-'}</td>
                    <td className="py-3 px-4 text-right font-mono">{Number(pago.deducciones_descuentos) > 0 ? moneda(pago.deducciones_descuentos) : '-'}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">{moneda(pago.monto_neto_pagado)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {formPago && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div role="dialog" aria-label="Registrar pago" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Registrar Pago</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{empleado?.nombre_completo}</p>

            <form onSubmit={registrarPago} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label htmlFor="tipo-pago" className={ETIQUETA}>Tipo de pago *</label>
                <select
                  id="tipo-pago"
                  value={formPago.tipo_pago}
                  onChange={(e) => setFormPago({ ...formPago, tipo_pago: e.target.value, ...valoresDeTipo(e.target.value) })}
                  className={ENTRADA}
                >
                  {Object.entries(TIPOS_PAGO)
                    .filter(([tipo]) => tipo !== 'COMISION_TRATAMIENTOS' || tieneComision)
                    .map(([tipo, texto]) => <option key={tipo} value={tipo} className={OPCION}>{texto}</option>)}
                </select>
              </div>

              {esSueldo(formPago.tipo_pago) ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="monto-base" className={ETIQUETA}>Sueldo ($) *</label>
                      <input id="monto-base" type="number" step="0.01" min="0" required value={formPago.base} onChange={(e) => setFormPago({ ...formPago, base: e.target.value })} className={ENTRADA} />
                    </div>
                    <div>
                      <label htmlFor="descuento" className={ETIQUETA}>Descontar adelantos ($)</label>
                      <input id="descuento" type="number" step="0.01" min="0" max={adelantosPendientes} value={formPago.descuento} onChange={(e) => setFormPago({ ...formPago, descuento: e.target.value })} className={ENTRADA} />
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Adelantos pendientes: {moneda(adelantosPendientes)}</div>
                  <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Monto a entregar</span>
                    <span data-testid="neto-sueldo" className="text-base font-mono font-bold text-slate-900 dark:text-white">{moneda(netoDeSueldo)}</span>
                  </div>
                </div>
              ) : (
                <div>
                  <label htmlFor="monto-pago" className={ETIQUETA}>Monto a pagar ($) *</label>
                  <input id="monto-pago" type="number" step="0.01" min="0.01" required value={formPago.monto} onChange={(e) => setFormPago({ ...formPago, monto: e.target.value })} className={ENTRADA} />
                  {formPago.tipo_pago === 'COMISION_TRATAMIENTOS' && (
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Saldo disponible: {moneda(Math.max(saldoComision, 0))}</div>
                  )}
                </div>
              )}

              <label className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-between gap-3 cursor-pointer">
                <span>
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">Pagar en efectivo de la caja</span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400">Resta el monto de la gaveta abierta</span>
                </span>
                <input type="checkbox" checked={formPago.descontar_de_caja} onChange={(e) => setFormPago({ ...formPago, descontar_de_caja: e.target.checked })} className="w-4 h-4 cursor-pointer" />
              </label>

              <div>
                <label htmlFor="obs-pago" className={ETIQUETA}>Observaciones</label>
                <textarea id="obs-pago" rows="2" value={formPago.observaciones} onChange={(e) => setFormPago({ ...formPago, observaciones: e.target.value })} className={ENTRADA} />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => { setFormPago(null); setError(''); }} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold">Confirmar Pago</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {formContrato && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div role="dialog" aria-label="Contrato" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Contrato</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{empleado?.nombre_completo}</p>

            <form onSubmit={guardarContrato} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label htmlFor="tipo-contrato" className={ETIQUETA}>Tipo de remuneración *</label>
                <select id="tipo-contrato" value={formContrato.tipo_remuneracion} onChange={(e) => setFormContrato({ ...formContrato, tipo_remuneracion: e.target.value })} className={ENTRADA}>
                  {Object.entries(TIPOS_CONTRATO).map(([tipo, texto]) => <option key={tipo} value={tipo} className={OPCION}>{texto}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="salario" className={ETIQUETA}>Sueldo mensual</label>
                  <input id="salario" type="number" step="0.01" min="0" value={formContrato.salario_base} onChange={(e) => setFormContrato({ ...formContrato, salario_base: e.target.value })} className={ENTRADA} />
                </div>
                <div>
                  <label htmlFor="porcentaje" className={ETIQUETA}>% comisión</label>
                  <input id="porcentaje" type="number" step="0.01" min="0" max="100" value={formContrato.porcentaje_comision} onChange={(e) => setFormContrato({ ...formContrato, porcentaje_comision: e.target.value })} className={ENTRADA} />
                </div>
                <div>
                  <label htmlFor="valor-hora" className={ETIQUETA}>Valor hora</label>
                  <input id="valor-hora" type="number" step="0.01" min="0" value={formContrato.valor_hora} onChange={(e) => setFormContrato({ ...formContrato, valor_hora: e.target.value })} className={ENTRADA} />
                </div>
              </div>
              <p className="text-[11px] text-amber-700 dark:text-amber-300">
                Cambiar el porcentaje recalcula toda la comisión de esta persona, también la de cobros anteriores.
              </p>
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => { setFormContrato(null); setError(''); }} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold">Guardar Contrato</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
