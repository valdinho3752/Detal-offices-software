import React, { useState } from 'react';
import { Timer, AlertTriangle } from 'lucide-react';
import ErrorModal from './ErrorModal';
import { useAuth } from '../context/AuthContext';

const OPCIONES = [
  [5, '5 minutos (recomendado)'],
  [10, '10 minutos'],
  [15, '15 minutos'],
  [30, '30 minutos'],
  [60, '1 hora'],
  [120, '2 horas'],
  [480, '8 horas (máximo)'],
];
const RECOMENDADO = 5;

export default function TiempoSesionModal({ onCerrar }) {
  const { user, actualizarTiempoSesion } = useAuth();
  const [minutos, setMinutos] = useState(user?.minutos_inactividad || RECOMENDADO);
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    setGuardando(true);
    try {
      await actualizarTiempoSesion(minutos);
      onCerrar();
    } catch (err) {
      setError(err.message || 'No se pudo guardar el tiempo de sesión');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div role="dialog" aria-label="Cierre de sesión por inactividad" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <Timer className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          Cierre de Sesión por Inactividad
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">Tu sesión se cierra sola si el equipo queda sin usar durante este tiempo. Solo se aplica a tu usuario.</p>
        <form onSubmit={guardar} className="space-y-4">
          <ErrorModal mensaje={error} />
          <div>
            <label htmlFor="minutos-inactividad" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Cerrar mi sesión tras</label>
            <select id="minutos-inactividad" value={minutos} onChange={(e) => setMinutos(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs">
              {OPCIONES.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
            </select>
          </div>
          {minutos > RECOMENDADO && (
            <div role="status" className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-300 text-xs flex gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Bajo tu propia responsabilidad: durante este tiempo, cualquiera que use el equipo podría hacer cambios a tu nombre.</span>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
            <button type="button" onClick={onCerrar} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
            <button type="submit" disabled={guardando} className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold">{guardando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
