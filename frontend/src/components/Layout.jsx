import React, { useState, useEffect } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import {
  Activity,
  Users,
  Calendar,
  Clock,
  ClipboardList,
  Image,
  ShieldCheck,
  Banknote,
  Wallet,
  FileText,
  BarChart3,
  UserCog,
  LogOut,
  CheckCircle2,
  AlertCircle,
  Menu,
  X,
  Sparkles,
  Stethoscope,
  ChevronRight,
  Bell,
  Sun,
  Moon,
  BookOpen,
  Armchair,
  Settings,
} from 'lucide-react';
import { puedeAcceder } from '../config/accesos';
import CajaBloqueoBarrier from './CajaBloqueoBarrier';
import { useMoneda } from '../context/MonedaContext';

// Estas pantallas aprovechan todo el ancho disponible
const PANTALLAS_ANCHAS = ['/odontograma', '/citas'];

export default function Layout({ children }) {
  const { moneda } = useMoneda();
  const auth = useAuth();
  const { user, logout, tienePermiso } = auth;
  const puedeFichar = tienePermiso('ASISTENCIA_FICHAR');
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [cajaEstado, setCajaEstado] = useState(null);
  const [fichajeModal, setFichajeModal] = useState(false);
  const [fichajeTipo, setFichajeTipo] = useState('ENTRADA');
  const [fichajeObs, setFichajeObs] = useState('');
  const [fichajeSuccess, setFichajeSuccess] = useState('');

  const refreshCaja = async () => {
    try {
      const est = await api.getEstadoCaja();
      setCajaEstado(est);
    } catch (e) {
      // Ignorar si no está autenticado
    }
  };

  useEffect(() => {
    refreshCaja();
    const interval = setInterval(refreshCaja, 15000);
    return () => clearInterval(interval);
  }, [location.pathname]);

  const handleFichar = async (e) => {
    e.preventDefault();
    try {
      await api.fichar(fichajeTipo, fichajeObs);
      setFichajeSuccess(`¡Marcaje de ${fichajeTipo} registrado exitosamente!`);
      setTimeout(() => {
        setFichajeSuccess('');
        setFichajeModal(false);
        setFichajeObs('');
      }, 1500);
    } catch (err) {
      alert(`Error al fichar: ${err.message}`);
    }
  };

  const todasLasOpciones = [
    { path: '/', label: 'Panel Principal', icon: Activity, badge: null },
    { path: '/pacientes', label: 'Pacientes & Ficha', icon: Users, badge: 'HU-03' },
    { path: '/odontograma', label: 'Odontograma FDI & Planes', icon: Sparkles, badge: 'HU-04' },
    { path: '/citas', label: 'Agenda & Sillón', icon: Calendar, badge: 'HU-05' },
    { path: '/asistencia', label: 'Control Asistencia', icon: Clock, badge: 'HU-06' },
    { path: '/evolucion', label: 'Evolución & Recetas', icon: ClipboardList, badge: 'HU-07' },
    { path: '/radiografias', label: 'Visor Radiográfico', icon: Image, badge: 'HU-08' },
    { path: '/protesis', label: 'Prótesis & Laboratorio', icon: Stethoscope, badge: 'HU-09' },
    { path: '/caja', label: 'Caja Operativa Diaria', icon: Wallet, badge: 'HU-10' },
    { path: '/cobranzas', label: 'Cobranzas & Pagos', icon: Banknote, badge: 'HU-11' },
    { path: '/nomina', label: 'Nómina & Comisiones', icon: FileText, badge: 'HU-12' },
    { path: '/auditoria', label: 'Auditoría Forense', icon: ShieldCheck, badge: 'HU-13' },
    { path: '/reportes', label: 'Inteligencia de Negocio', icon: BarChart3, badge: 'HU-14' },
    { path: '/tratamientos', label: 'Catálogo de Tratamientos', icon: BookOpen, badge: 'Admin' },
    { path: '/sillones', label: 'Sillones', icon: Armchair, badge: 'Admin' },
    { path: '/configuracion', label: 'Configuración', icon: Settings, badge: 'Admin' },
    { path: '/usuarios', label: 'Usuarios & Roles RBAC', icon: UserCog, badge: 'HU-01/02' },
  ];
  const menuItems = todasLasOpciones.filter((item) => puedeAcceder(item.path, auth));

  return (
    <div className="flex h-screen bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-100 overflow-hidden font-sans">
      {/* Daily Cash Register Gatekeeper Barrier (HU-10) */}
      <CajaBloqueoBarrier cajaEstado={cajaEstado} onCajaUpdated={refreshCaja} />

      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-100 flex flex-col transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="p-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary-600 to-teal-500 flex items-center justify-center text-white shadow-lg shadow-primary-600/30 text-xl font-bold">
              🦷
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-tight text-slate-900 dark:text-white">Clínica Gustavo</h1>
              <p className="text-[11px] text-primary-600 dark:text-primary-400 font-medium">Software Odontológico</p>
            </div>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User Card */}
        <div className="p-3 mx-3 my-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/50 flex items-center justify-between">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/40 text-primary-600 dark:text-primary-300 flex items-center justify-center font-bold text-xs uppercase">
              {user?.username?.[0] || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{user?.nombre_completo || user?.username}</p>
              <span className="inline-block px-1.5 py-0.2 rounded text-[9px] font-bold bg-primary-500/20 text-primary-700 dark:text-primary-300 uppercase">
                {user?.rol_nombre || user?.rol_str}
              </span>
            </div>
          </div>
          <button
            hidden={!puedeFichar}
            onClick={() => setFichajeModal(true)}
            title="Registrar Fichaje Laboral (HU-06)"
            className="p-1.5 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-colors"
          >
            <Clock className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-primary-600 text-white shadow-md shadow-primary-600/30 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'}`} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700/50'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout Footer */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800">
          <button
            onClick={logout}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-xl text-xs font-semibold text-rose-500 dark:text-rose-400 hover:text-white hover:bg-rose-500/90 dark:hover:bg-rose-500/20 transition-all border border-rose-500/20"
          >
            <LogOut className="w-4 h-4" />
            <span>Cerrar Sesión</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50 dark:bg-slate-900">
        {/* Top Navbar */}
        <header className="h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between shadow-sm z-30">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="hidden sm:block">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                {menuItems.find((m) => m.path === location.pathname)?.label || 'Clínica Dental Gustavo'}
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">PostgreSQL Backend · Verificado HU-01 a HU-14</p>
            </div>
          </div>

          {/* Quick status badges & Theme toggle */}
          <div className="flex items-center space-x-3">
            {/* Theme Toggle Button (Claro / Oscuro) */}
            <button
              onClick={toggleTheme}
              title={isDark ? "Cambiar a Modo Claro" : "Cambiar a Modo Oscuro"}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold transition shadow-sm"
            >
              {isDark ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400" />
                  <span className="hidden sm:inline">Modo Claro</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-slate-700" />
                  <span className="hidden sm:inline">Modo Oscuro</span>
                </>
              )}
            </button>

            {/* Caja status pill (HU-10) */}
            <Link
              to="/caja"
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                cajaEstado?.tipo_bloqueo === 'CIERRE_PENDIENTE_ANTERIOR'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
                  : cajaEstado?.caja_abierta && cajaEstado?.es_del_dia
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20'
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  cajaEstado?.tipo_bloqueo === 'CIERRE_PENDIENTE_ANTERIOR'
                    ? 'bg-amber-400 animate-pulse'
                    : cajaEstado?.caja_abierta && cajaEstado?.es_del_dia
                    ? 'bg-emerald-400 animate-pulse'
                    : 'bg-rose-400'
                }`}
              />
              <span>
                {cajaEstado?.tipo_bloqueo === 'CIERRE_PENDIENTE_ANTERIOR'
                  ? 'Caja Anterior sin Cerrar'
                  : cajaEstado?.caja_abierta && cajaEstado?.es_del_dia
                  ? cajaEstado.saldo_en_gaveta === undefined
                    ? 'Caja Abierta'
                    : `Gaveta: ${moneda(cajaEstado.saldo_en_gaveta)}`
                  : 'Caja de Hoy sin Abrir'}
              </span>
            </Link>

            {/* Quick clock button */}
            <button
              hidden={!puedeFichar}
              onClick={() => setFichajeModal(true)}
              className={`${puedeFichar ? 'flex' : 'hidden'} items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold transition`}
            >
              <Clock className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
              <span className="hidden sm:inline">Fichar Turno</span>
            </button>
          </div>
        </header>

        {/* View Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-slate-50/70 dark:bg-slate-900/50">
          <div className={PANTALLAS_ANCHAS.includes(location.pathname) ? 'w-full' : 'max-w-7xl mx-auto'}>{children || <Outlet />}</div>
        </main>
      </div>

      {/* Fichaje Modal (HU-06) */}
      {fichajeModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl shadow-2xl max-w-md w-full p-6 border border-slate-700">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Clock className="w-5 h-5 text-primary-400" />
                <h3 className="text-base font-bold text-white">Fichaje Horario Rápido (HU-06)</h3>
              </div>
              <button
                onClick={() => setFichajeModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {fichajeSuccess ? (
              <div className="py-6 flex flex-col items-center justify-center text-center space-y-2 text-emerald-400">
                <CheckCircle2 className="w-12 h-12" />
                <p className="text-sm font-semibold">{fichajeSuccess}</p>
              </div>
            ) : (
              <form onSubmit={handleFichar} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Tipo de Evento</label>
                  <select
                    value={fichajeTipo}
                    onChange={(e) => setFichajeTipo(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs font-semibold"
                  >
                    <option value="ENTRADA">Inicio de Jornada (ENTRADA)</option>
                    <option value="INICIO_DESCANSO">Salida a Colación / Descanso</option>
                    <option value="FIN_DESCANSO">Retorno de Colación / Descanso</option>
                    <option value="SALIDA">Fin de Jornada (SALIDA)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Nota u Observación (Opcional)</label>
                  <input
                    type="text"
                    value={fichajeObs}
                    onChange={(e) => setFichajeObs(e.target.value)}
                    placeholder="ej. Turno tarde / Box 1"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setFichajeModal(false)}
                    className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-xs hover:text-white transition"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-primary-600/30 transition"
                  >
                    Registrar Marcaje
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
