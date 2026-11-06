import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MENSAJE_INACTIVIDAD, useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useClinica } from '../context/ClinicaContext';
import LogoClinica from '../components/LogoClinica';
import { Lock, User, AlertCircle, Sun, Moon } from 'lucide-react';

export default function LoginView() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [porInactividad] = useState(() => {
    const cerrada = sessionStorage.getItem(MENSAJE_INACTIVIDAD) === '1';
    sessionStorage.removeItem(MENSAJE_INACTIVIDAD);
    return cerrada;
  });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { nombreClinica } = useClinica();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900 flex flex-col justify-center items-center p-4 relative overflow-hidden transition-colors duration-200">
      {/* Botón Theme Toggle en esquina superior */}
      <div className="absolute top-5 right-5 z-20">
        <button
          onClick={toggleTheme}
          title={isDark ? "Cambiar a Modo Claro" : "Cambiar a Modo Oscuro"}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold shadow-sm transition"
        >
          {isDark ? (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span className="text-[11px]">Modo Claro</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-slate-700" />
              <span className="text-[11px]">Modo Oscuro</span>
            </>
          )}
        </button>
      </div>

      {/* Background accents */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-teal-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex mb-4">
            <LogoClinica clase="w-16 h-16" claseIcono="text-3xl" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight break-words">{nombreClinica}</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">Sistema Integral Odontológico & Gestión Clínica</p>
        </div>

        <div className="bg-white/95 dark:bg-slate-800/90 backdrop-blur-xl border border-slate-200 dark:border-slate-700/60 rounded-2xl shadow-xl dark:shadow-2xl p-6 sm:p-8">
          {porInactividad && !error && (
            <div role="status" className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-300 text-xs">
              Tu sesión se cerró por inactividad. Vuelve a entrar para continuar.
            </div>
          )}
          {error && (
            <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-3 text-rose-600 dark:text-rose-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2">
                Usuario o Correo
              </label>
              <div className="relative">
                <User className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Tu usuario"
                  className="w-full pl-11 pr-4 py-2.5 bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-4 py-2.5 bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-primary-600 hover:bg-primary-500 text-white font-semibold rounded-xl shadow-lg shadow-primary-600/30 transition duration-150 disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                'Iniciar Sesión'
              )}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
