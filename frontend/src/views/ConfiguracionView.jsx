import React, { useState } from 'react';
import { AlertCircle, Banknote, CheckCircle2 } from 'lucide-react';
import { formatearMoneda, useMoneda } from '../context/MonedaContext';

const OPCIONES = [
  { simbolo: 'Bs.', nombre: 'Boliviano' },
  { simbolo: '$', nombre: 'Peso o dólar' },
  { simbolo: 'US$', nombre: 'Dólar estadounidense' },
  { simbolo: 'S/', nombre: 'Sol peruano' },
  { simbolo: '€', nombre: 'Euro' },
];
const LARGO_MAXIMO = 8;
const MONTO_EJEMPLO = 1500;

export default function ConfiguracionView() {
  const { simbolo, cambiarSimbolo } = useMoneda();
  const [elegido, setElegido] = useState(simbolo);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');

  const limpio = elegido.trim();
  const esOpcion = OPCIONES.some((o) => o.simbolo === limpio);

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    setExito('');
    setGuardando(true);
    try {
      await cambiarSimbolo(limpio);
      setExito(`Moneda guardada. Los montos se muestran como ${formatearMoneda(MONTO_EJEMPLO, limpio)}`);
    } catch (err) {
      setError(err.message || 'No se pudo guardar la moneda');
    } finally {
      setGuardando(false);
    }
  };

  const claseOpcion = (activa) => `p-3 rounded-xl border text-left transition ${
    activa
      ? 'border-primary-600 bg-primary-50 dark:bg-primary-600/20 ring-1 ring-primary-600'
      : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:border-slate-400 dark:hover:border-slate-500'
  }`;

  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Configuración</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Ajustes generales de la clínica</p>
      </div>

      <form onSubmit={guardar} className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-5 shadow-sm max-w-3xl">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Banknote className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            Moneda
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Se aplica a todas las pantallas y a todos los usuarios.</p>
        </div>

        {error && (
          <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}
        {exito && (
          <div role="status" className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            {exito}
          </div>
        )}

        <div role="group" aria-label="Moneda de la clínica" className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {OPCIONES.map((opcion) => (
            <button
              key={opcion.simbolo}
              type="button"
              aria-pressed={limpio === opcion.simbolo}
              onClick={() => setElegido(opcion.simbolo)}
              className={claseOpcion(limpio === opcion.simbolo)}
            >
              <span className="block text-sm font-bold text-slate-900 dark:text-white">{opcion.simbolo}</span>
              <span className="block text-[11px] text-slate-500 dark:text-slate-400">{opcion.nombre}</span>
            </button>
          ))}
        </div>

        <div className="max-w-xs">
          <label htmlFor="moneda-otra" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Otra moneda
          </label>
          <input
            id="moneda-otra"
            type="text"
            maxLength={LARGO_MAXIMO}
            value={esOpcion ? '' : elegido}
            onChange={(e) => setElegido(e.target.value)}
            placeholder="Ej. COP"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="p-3 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
          <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Vista previa</span>
          <span data-testid="vista-previa-moneda" className="text-xl font-bold font-mono text-slate-900 dark:text-white">
            {formatearMoneda(MONTO_EJEMPLO, limpio || simbolo)}
          </span>
        </div>

        <p className="text-xs text-amber-700 dark:text-amber-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Solo cambia el símbolo que se muestra: los montos no se convierten. Un monto de 100 sigue siendo 100 con el símbolo nuevo.
        </p>

        <div className="flex justify-end pt-3 border-t border-slate-200 dark:border-slate-700/60">
          <button
            type="submit"
            disabled={guardando || !limpio || limpio === simbolo}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-semibold"
          >
            {guardando ? 'Guardando...' : 'Guardar Moneda'}
          </button>
        </div>
      </form>
    </div>
  );
}
