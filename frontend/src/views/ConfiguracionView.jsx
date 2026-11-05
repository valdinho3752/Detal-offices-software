import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Banknote, Building2, CheckCircle2, Moon, Sun, Trash2, Upload } from 'lucide-react';
import LogoClinica from '../components/LogoClinica';
import { useClinica } from '../context/ClinicaContext';
import { formatearMoneda, useMoneda } from '../context/MonedaContext';
import { useTheme } from '../context/ThemeContext';

const MONEDAS = [
  { simbolo: 'Bs.', nombre: 'Boliviano' },
  { simbolo: '$', nombre: 'Peso o dólar' },
  { simbolo: 'US$', nombre: 'Dólar estadounidense' },
  { simbolo: 'S/', nombre: 'Sol peruano' },
  { simbolo: '€', nombre: 'Euro' },
];
const TEMAS = [
  { id: 'oscuro', nombre: 'Oscuro', Icono: Moon },
  { id: 'claro', nombre: 'Claro', Icono: Sun },
];
const LARGO_SIMBOLO = 8;
const LARGO_NOMBRE = 120;
const MONTO_EJEMPLO = 1500;
const LOGO_MAXIMO = 1024 * 1024;
const TIPOS_LOGO = ['image/png', 'image/jpeg', 'image/webp'];

const TARJETA = 'bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-5 shadow-sm';
const CAMPO = 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500';
const ETIQUETA = 'block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1';
const BOTON = 'px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-semibold';
const BOTON_SECUNDARIO = 'px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

const claseOpcion = (activa) => `p-3 rounded-xl border text-left transition ${
  activa
    ? 'border-primary-600 bg-primary-50 dark:bg-primary-600/20 ring-1 ring-primary-600'
    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:border-slate-400 dark:hover:border-slate-500'
}`;

function Aviso({ tipo, children }) {
  if (!children) return null;
  const esError = tipo === 'error';
  const Icono = esError ? AlertCircle : CheckCircle2;
  return (
    <div
      role={esError ? 'alert' : 'status'}
      className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
        esError
          ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
          : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
      }`}
    >
      <Icono className="w-4 h-4 flex-shrink-0" />
      {children}
    </div>
  );
}

function Encabezado({ Icono, titulo, descripcion }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
        <Icono className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        {titulo}
      </h2>
      <p className="text-xs text-slate-500 dark:text-slate-400">{descripcion}</p>
    </div>
  );
}

function SeccionClinica() {
  const { nombreClinica, logoUrl, guardarClinica, subirLogo, quitarLogo } = useClinica();
  const [nombre, setNombre] = useState(nombreClinica);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');
  const entradaArchivo = useRef(null);
  const limpio = nombre.trim();

  useEffect(() => { setNombre(nombreClinica); }, [nombreClinica]);

  const ejecutar = async (accion, mensaje) => {
    setError('');
    setExito('');
    setOcupado(true);
    try {
      await accion();
      setExito(mensaje);
    } catch (err) {
      setError(err.message || 'No se pudo guardar');
    } finally {
      setOcupado(false);
    }
  };

  const elegirLogo = (e) => {
    const archivo = e.target.files?.[0];
    e.target.value = '';
    if (!archivo) return;
    setExito('');
    if (!TIPOS_LOGO.includes(archivo.type)) {
      setError('El logo debe ser una imagen PNG, JPG o WEBP');
      return;
    }
    if (archivo.size > LOGO_MAXIMO) {
      setError('El logo no puede superar 1 MB');
      return;
    }
    ejecutar(() => subirLogo(archivo), 'Logo actualizado');
  };

  return (
    <section className={TARJETA}>
      <Encabezado Icono={Building2} titulo="Clínica" descripcion="El nombre y el logo aparecen en el menú, en la pantalla de acceso y en la pestaña del navegador." />
      <Aviso tipo="error">{error}</Aviso>
      <Aviso tipo="exito">{exito}</Aviso>

      <form
        onSubmit={(e) => { e.preventDefault(); ejecutar(() => guardarClinica({ nombre_clinica: limpio }), 'Nombre guardado'); }}
        className="flex flex-col sm:flex-row sm:items-end gap-3"
      >
        <div className="flex-1 min-w-0">
          <label htmlFor="nombre-clinica" className={ETIQUETA}>Nombre de la clínica *</label>
          <input id="nombre-clinica" type="text" required maxLength={LARGO_NOMBRE} value={nombre} onChange={(e) => setNombre(e.target.value)} className={CAMPO} />
        </div>
        <button type="submit" disabled={ocupado || !limpio || limpio === nombreClinica} className={BOTON}>Guardar Nombre</button>
      </form>

      <div className="flex flex-wrap items-center gap-4">
        <LogoClinica clase="w-16 h-16" claseIcono="text-3xl" />
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={ocupado} onClick={() => entradaArchivo.current?.click()} className={BOTON_SECUNDARIO}>
              <Upload className="w-3.5 h-3.5" />
              {logoUrl ? 'Cambiar logo' : 'Subir logo'}
            </button>
            {logoUrl && (
              <button type="button" disabled={ocupado} onClick={() => ejecutar(quitarLogo, 'Logo quitado')} className={BOTON_SECUNDARIO}>
                <Trash2 className="w-3.5 h-3.5" />
                Quitar logo
              </button>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">PNG, JPG o WEBP de hasta 1 MB. Se ve mejor si es cuadrado.</p>
          <input ref={entradaArchivo} data-testid="archivo-logo" type="file" accept={TIPOS_LOGO.join(',')} onChange={elegirLogo} style={{ display: 'none' }} />
        </div>
      </div>
    </section>
  );
}

function SeccionTema() {
  const { temaPorDefecto, guardarClinica } = useClinica();
  const { tienePreferencia } = useTheme();
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const elegir = async (tema) => {
    if (tema === temaPorDefecto) return;
    setError('');
    setExito('');
    setOcupado(true);
    try {
      await guardarClinica({ tema_por_defecto: tema });
      setExito('Tema por defecto guardado');
    } catch (err) {
      setError(err.message || 'No se pudo guardar el tema');
    } finally {
      setOcupado(false);
    }
  };

  return (
    <section className={TARJETA}>
      <Encabezado
        Icono={Sun}
        titulo="Tema por defecto"
        descripcion="Es el que ve quien abre el sistema por primera vez. Cada persona puede cambiar el suyo con el botón de la barra superior, y se recuerda en su equipo."
      />
      <Aviso tipo="error">{error}</Aviso>
      <Aviso tipo="exito">{exito}</Aviso>
      <div role="group" aria-label="Tema por defecto" className="grid grid-cols-2 gap-2 max-w-md">
        {TEMAS.map(({ id, nombre, Icono }) => (
          <button key={id} type="button" disabled={ocupado} aria-pressed={temaPorDefecto === id} onClick={() => elegir(id)} className={`${claseOpcion(temaPorDefecto === id)} flex items-center gap-2`}>
            <Icono className="w-4 h-4 text-slate-600 dark:text-slate-300" />
            <span className="text-sm font-bold text-slate-900 dark:text-white">{nombre}</span>
          </button>
        ))}
      </div>
      {tienePreferencia && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400">
          En este equipo ya elegiste un tema con el botón de la barra superior, y se mantiene aunque cambies este ajuste.
        </p>
      )}
    </section>
  );
}

function SeccionMoneda() {
  const { simbolo, cambiarSimbolo } = useMoneda();
  const [elegido, setElegido] = useState(simbolo);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');

  useEffect(() => { setElegido(simbolo); }, [simbolo]);

  const limpio = elegido.trim();
  const esOpcion = MONEDAS.some((o) => o.simbolo === limpio);

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

  return (
    <form onSubmit={guardar} className={TARJETA}>
      <Encabezado Icono={Banknote} titulo="Moneda" descripcion="Se aplica a todas las pantallas y a todos los usuarios." />
      <Aviso tipo="error">{error}</Aviso>
      <Aviso tipo="exito">{exito}</Aviso>

      <div role="group" aria-label="Moneda de la clínica" className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {MONEDAS.map((opcion) => (
          <button key={opcion.simbolo} type="button" aria-pressed={limpio === opcion.simbolo} onClick={() => setElegido(opcion.simbolo)} className={claseOpcion(limpio === opcion.simbolo)}>
            <span className="block text-sm font-bold text-slate-900 dark:text-white">{opcion.simbolo}</span>
            <span className="block text-[11px] text-slate-500 dark:text-slate-400">{opcion.nombre}</span>
          </button>
        ))}
      </div>

      <div className="max-w-xs">
        <label htmlFor="moneda-otra" className={ETIQUETA}>Otra moneda</label>
        <input id="moneda-otra" type="text" maxLength={LARGO_SIMBOLO} value={esOpcion ? '' : elegido} onChange={(e) => setElegido(e.target.value)} placeholder="Ej. COP" className={CAMPO} />
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
        <button type="submit" disabled={guardando || !limpio || limpio === simbolo} className={BOTON}>
          {guardando ? 'Guardando...' : 'Guardar Moneda'}
        </button>
      </div>
    </form>
  );
}

export default function ConfiguracionView() {
  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Configuración</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Ajustes generales de la clínica</p>
      </div>
      <div className="space-y-6 max-w-3xl">
        <SeccionClinica />
        <SeccionTema />
        <SeccionMoneda />
      </div>
    </div>
  );
}
