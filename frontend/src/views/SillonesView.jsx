import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Armchair, CheckCircle2, Edit3, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import ErrorModal from '../components/ErrorModal';

const CAMPO =
  'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';

export default function SillonesView() {
  const [sillones, setSillones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modalAbierto, setModalAbierto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ nombre: '', especialidad: '' });
  const temporizador = useRef(null);

  const avisar = (mensaje) => {
    setSuccess(mensaje);
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setSuccess(''), 5000);
  };

  const cargar = async () => {
    try {
      const datos = await api.getSillones();
      setSillones(Array.isArray(datos) ? datos : []);
    } catch (err) {
      setError(err.message || 'Error cargando los sillones');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
    return () => clearTimeout(temporizador.current);
  }, []);

  const activos = sillones.filter((s) => s.activo).length;
  const siguienteNumero = Math.max(0, ...sillones.map((s) => s.numero)) + 1;

  const abrir = (sillon = null) => {
    setError('');
    setEditando(sillon);
    setForm({ nombre: sillon?.nombre || '', especialidad: sillon?.especialidad || '' });
    setModalAbierto(true);
  };

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editando) {
        await api.updateSillon(editando.id, { nombre: form.nombre, especialidad: form.especialidad });
        avisar('Sillón actualizado');
      } else {
        await api.createSillon({ nombre: form.nombre.trim() || null, especialidad: form.especialidad.trim() || null });
        avisar('Sillón agregado: ya aparece en la agenda');
      }
      setModalAbierto(false);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al guardar el sillón');
    }
  };

  const eliminar = async (sillon) => {
    if (!window.confirm(`¿Quitar ${sillon.nombre} de la agenda?`)) return;
    setError('');
    try {
      const respuesta = await api.deleteSillon(sillon.id);
      avisar(respuesta.mensaje);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al quitar el sillón');
    }
  };

  const reactivar = async (sillon) => {
    setError('');
    try {
      await api.updateSillon(sillon.id, { activo: true });
      avisar(`${sillon.nombre} vuelve a estar en la agenda`);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al reactivar el sillón');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Sillones de la Clínica</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            {activos} {activos === 1 ? 'sillón activo' : 'sillones activos'} en la matriz de la agenda
          </p>
        </div>
        <button
          onClick={() => abrir()}
          className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
        >
          <Plus className="w-4 h-4" />
          Agregar Sillón
        </button>
      </div>

      {error && !modalAbierto && (
        <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
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

      {loading ? (
        <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs">Cargando sillones...</div>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sillones.map((s) => (
            <li
              key={s.id}
              className={`p-4 bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl shadow-sm flex items-center justify-between gap-3 ${s.activo ? '' : 'opacity-60'}`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2.5 bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 rounded-xl flex-shrink-0">
                  <Armchair className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-bold text-slate-900 dark:text-white truncate">{s.nombre}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {s.especialidad || 'Sin especialidad'}
                    {!s.activo && ' · Desactivado'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button onClick={() => abrir(s)} aria-label={`Editar ${s.nombre}`} title="Editar" className="p-1.5 rounded-lg text-slate-500 hover:text-primary-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition">
                  <Edit3 className="w-4 h-4" />
                </button>
                {s.activo ? (
                  <button onClick={() => eliminar(s)} aria-label={`Quitar ${s.nombre}`} title="Quitar de la agenda" className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition">
                    <Trash2 className="w-4 h-4" />
                  </button>
                ) : (
                  <button onClick={() => reactivar(s)} aria-label={`Reactivar ${s.nombre}`} title="Reactivar" className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition">
                    <RotateCcw className="w-4 h-4" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {modalAbierto && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">{editando ? `Editar ${editando.nombre}` : 'Agregar Sillón'}</h3>
            <form onSubmit={guardar} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label htmlFor="sillon-nombre" className={ETIQUETA}>Nombre{editando ? ' *' : ''}</label>
                <input
                  id="sillon-nombre"
                  type="text"
                  required={Boolean(editando)}
                  maxLength={100}
                  placeholder={editando ? '' : `Box ${siguienteNumero}`}
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className={CAMPO}
                />
              </div>
              <div>
                <label htmlFor="sillon-especialidad" className={ETIQUETA}>Especialidad</label>
                <input
                  id="sillon-especialidad"
                  type="text"
                  maxLength={100}
                  placeholder="General, Cirugía, Ortodoncia..."
                  value={form.especialidad}
                  onChange={(e) => setForm({ ...form, especialidad: e.target.value })}
                  className={CAMPO}
                />
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs transition">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition">
                  {editando ? 'Guardar Cambios' : 'Agregar Sillón'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
