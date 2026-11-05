import React, { useState } from 'react';
import { KeyRound } from 'lucide-react';
import ErrorModal from './ErrorModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

const CAMPO = 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';

// Con obligatorio no se puede cerrar: la contraseña la conoce quien creó o restableció la cuenta
export default function CambiarContrasenaModal({ obligatorio = false, onCerrar }) {
  const { actualizarSesion } = useAuth();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    if (nueva !== repetida) {
      setError('Las contraseñas nuevas no coinciden');
      return;
    }
    setGuardando(true);
    try {
      const { access_token: token } = await api.cambiarContrasena({ actual, nueva });
      await actualizarSesion(token);
      onCerrar?.();
    } catch (err) {
      setError(err.message || 'No se pudo cambiar la contraseña');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div role="dialog" aria-label="Cambiar contraseña" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <KeyRound className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          Cambiar Contraseña
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          {obligatorio
            ? 'Por seguridad, elige una contraseña que solo tú conozcas antes de continuar.'
            : 'Tus demás sesiones abiertas se cerrarán.'}
        </p>
        <form onSubmit={guardar} className="space-y-4">
          <ErrorModal mensaje={error} />
          <div>
            <label htmlFor="clave-actual" className={ETIQUETA}>Contraseña actual *</label>
            <input id="clave-actual" type="password" required autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} className={CAMPO} />
          </div>
          <div>
            <label htmlFor="clave-nueva" className={ETIQUETA}>Contraseña nueva *</label>
            <input id="clave-nueva" type="password" required minLength={8} autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} className={CAMPO} />
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Al menos 8 caracteres, con letras y números.</p>
          </div>
          <div>
            <label htmlFor="clave-repetida" className={ETIQUETA}>Repite la contraseña nueva *</label>
            <input id="clave-repetida" type="password" required autoComplete="new-password" value={repetida} onChange={(e) => setRepetida(e.target.value)} className={CAMPO} />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
            {!obligatorio && (
              <button type="button" onClick={onCerrar} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs">Cancelar</button>
            )}
            <button type="submit" disabled={guardando} className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold">
              {guardando ? 'Guardando...' : 'Guardar Contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
