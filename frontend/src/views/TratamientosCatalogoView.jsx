import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock,
  Edit3,
  Plus,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';
import ErrorModal from '../components/ErrorModal';
import { useMoneda } from '../context/MonedaContext';

const CATEGORIAS = {
  PREVENCION: 'Prevención',
  RESTAURADORA: 'Restauradora',
  ENDODONCIA: 'Endodoncia',
  CIRUGIA_PERIODONCIA: 'Cirugía / Periodoncia',
  REHABILITACION_PROTESIS: 'Rehabilitación / Prótesis',
  ORTODONCIA: 'Ortodoncia',
  ESTETICA_DENTAL: 'Estética Dental',
  IMPLANTOLOGIA: 'Implantología',
};

const FORM_VACIO = {
  codigo: '',
  categoria: 'PREVENCION',
  nombre: '',
  descripcion: '',
  costo_base: '',
  duracion_estimada_min: '30',
};

const CAMPO =
  'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';

export default function TratamientosCatalogoView() {
  const { moneda, simbolo } = useMoneda();
  const [tratamientos, setTratamientos] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [categoria, setCategoria] = useState('');
  const [mostrarInactivos, setMostrarInactivos] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modalAbierto, setModalAbierto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_VACIO);

  const temporizadorAviso = useRef(null);

  const avisar = (mensaje) => {
    setSuccess(mensaje);
    clearTimeout(temporizadorAviso.current);
    temporizadorAviso.current = setTimeout(() => setSuccess(''), 5000);
  };

  useEffect(() => () => clearTimeout(temporizadorAviso.current), []);

  const cargar = async () => {
    setLoading(true);
    try {
      const datos = await api.getCatalogoCompleto();
      setTratamientos(Array.isArray(datos) ? datos : []);
    } catch (err) {
      setError(err.message || 'Error cargando el catálogo');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return tratamientos.filter(
      (t) =>
        (mostrarInactivos || t.activo) &&
        (!categoria || t.categoria === categoria) &&
        (!q || t.nombre.toLowerCase().includes(q) || t.codigo.toLowerCase().includes(q))
    );
  }, [tratamientos, busqueda, categoria, mostrarInactivos]);

  const abrirNuevo = () => {
    setError('');
    setEditando(null);
    setForm(FORM_VACIO);
    setModalAbierto(true);
  };

  const abrirEdicion = (t) => {
    setError('');
    setEditando(t);
    setForm({
      codigo: t.codigo,
      categoria: t.categoria,
      nombre: t.nombre,
      descripcion: t.descripcion || '',
      costo_base: String(t.costo_base),
      duracion_estimada_min: String(t.duracion_estimada_min),
    });
    setModalAbierto(true);
  };

  const guardar = async (e) => {
    e.preventDefault();
    setError('');
    const datos = {
      ...form,
      descripcion: form.descripcion || null,
      costo_base: Number(form.costo_base),
      duracion_estimada_min: Number(form.duracion_estimada_min),
    };
    try {
      if (editando) {
        await api.updateTratamiento(editando.id, datos);
        avisar('Tratamiento actualizado. Los presupuestos ya creados conservan su precio.');
      } else {
        await api.createTratamiento(datos);
        avisar('Tratamiento agregado al catálogo');
      }
      setModalAbierto(false);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al guardar el tratamiento');
    }
  };

  const eliminar = async (t) => {
    if (!window.confirm(`¿Eliminar "${t.nombre}" del catálogo?`)) return;
    setError('');
    try {
      const respuesta = await api.deleteTratamiento(t.id);
      avisar(respuesta.mensaje);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al eliminar el tratamiento');
    }
  };

  const reactivar = async (t) => {
    setError('');
    try {
      await api.updateTratamiento(t.id, { activo: true });
      avisar(`"${t.nombre}" vuelve a estar disponible`);
      cargar();
    } catch (err) {
      setError(err.message || 'Error al reactivar el tratamiento');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Catálogo de Tratamientos</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Procedimientos, precios base y duración que se ofrecen en planes y citas
          </p>
        </div>
        <button
          onClick={abrirNuevo}
          className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
        >
          <Plus className="w-4 h-4" />
          Nuevo Tratamiento
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

      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-4 flex flex-col md:flex-row md:items-center gap-3 shadow-sm">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="search"
            aria-label="Buscar tratamiento"
            placeholder="Buscar por nombre o código..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className={`${CAMPO} pl-9`}
          />
        </div>
        <select aria-label="Filtrar por categoría" value={categoria} onChange={(e) => setCategoria(e.target.value)} className={`${CAMPO} md:w-56`}>
          <option value="">Todas las categorías</option>
          {Object.entries(CATEGORIAS).map(([valor, nombre]) => (
            <option key={valor} value={valor}>{nombre}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300 whitespace-nowrap cursor-pointer">
          <input
            type="checkbox"
            checked={mostrarInactivos}
            onChange={(e) => setMostrarInactivos(e.target.checked)}
            className="rounded border-slate-300 dark:border-slate-700 text-primary-500 focus:ring-0"
          />
          Mostrar desactivados
        </label>
      </div>

      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs">Cargando catálogo...</div>
        ) : visibles.length === 0 ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400">
            <BookOpen className="w-10 h-10 text-slate-400 dark:text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">No hay tratamientos para mostrar</p>
            <p className="text-xs mt-1">Cambia los filtros o agrega un tratamiento nuevo.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">Código</th>
                  <th className="py-3 px-4">Tratamiento</th>
                  <th className="py-3 px-4">Categoría</th>
                  <th className="py-3 px-4 text-right">Precio base</th>
                  <th className="py-3 px-4 text-right">Duración</th>
                  <th className="py-3 px-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                {visibles.map((t) => (
                  <tr key={t.id} className={`hover:bg-slate-50 dark:hover:bg-slate-700/20 transition ${t.activo ? '' : 'opacity-60'}`}>
                    <td className="py-3 px-4 font-mono font-semibold whitespace-nowrap">{t.codigo}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        {t.nombre}
                        {!t.activo && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-stone-200 text-stone-700 dark:bg-stone-700/40 dark:text-stone-300">
                            Desactivado
                          </span>
                        )}
                      </div>
                      {t.descripcion && <div className="text-slate-500 dark:text-slate-400 mt-0.5">{t.descripcion}</div>}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">{CATEGORIAS[t.categoria] || t.categoria}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white whitespace-nowrap">
                      {moneda(t.costo_base)}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-slate-400" /> {t.duracion_estimada_min} min</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => abrirEdicion(t)}
                          aria-label={`Editar ${t.nombre}`}
                          title="Editar"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-primary-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        {t.activo ? (
                          <button
                            onClick={() => eliminar(t)}
                            aria-label={`Eliminar ${t.nombre}`}
                            title="Eliminar"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => reactivar(t)}
                            aria-label={`Reactivar ${t.nombre}`}
                            title="Reactivar"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalAbierto && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">
              {editando ? 'Editar Tratamiento' : 'Nuevo Tratamiento'}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              {editando ? 'El nuevo precio solo aplica a presupuestos futuros.' : 'Quedará disponible en planes y citas.'}
            </p>

            <form onSubmit={guardar} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="trat-codigo" className={ETIQUETA}>Código *</label>
                  <input id="trat-codigo" type="text" required maxLength={30} placeholder="ej. END-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} className={`${CAMPO} font-mono`} />
                </div>
                <div>
                  <label htmlFor="trat-categoria" className={ETIQUETA}>Categoría *</label>
                  <select id="trat-categoria" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className={CAMPO}>
                    {Object.entries(CATEGORIAS).map(([valor, nombre]) => (
                      <option key={valor} value={valor}>{nombre}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label htmlFor="trat-nombre" className={ETIQUETA}>Nombre *</label>
                <input id="trat-nombre" type="text" required maxLength={200} placeholder="ej. Endodoncia unirradicular" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className={CAMPO} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="trat-precio" className={ETIQUETA}>Precio base ({simbolo}) *</label>
                  <input id="trat-precio" type="number" required min="0" step="0.01" placeholder="0.00" value={form.costo_base} onChange={(e) => setForm({ ...form, costo_base: e.target.value })} className={`${CAMPO} font-mono`} />
                </div>
                <div>
                  <label htmlFor="trat-duracion" className={ETIQUETA}>Duración (minutos) *</label>
                  <input id="trat-duracion" type="number" required min="1" step="1" value={form.duracion_estimada_min} onChange={(e) => setForm({ ...form, duracion_estimada_min: e.target.value })} className={`${CAMPO} font-mono`} />
                </div>
              </div>
              <div>
                <label htmlFor="trat-descripcion" className={ETIQUETA}>Descripción</label>
                <textarea id="trat-descripcion" rows="2" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} className={CAMPO} />
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs transition">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition">
                  {editando ? 'Guardar Cambios' : 'Agregar Tratamiento'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
