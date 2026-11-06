import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

const CLAVE_ACTIVIDAD = 'ultima_actividad'; // Compartida entre pestañas: usar una mantiene viva la sesión en todas
const AVISO_CIERRE_MS = 30000;
const EVENTOS_ACTIVIDAD = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'wheel', 'scroll'];
export const MENSAJE_INACTIVIDAD = 'sesion_cerrada_por_inactividad';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [segundosParaCierre, setSegundosParaCierre] = useState(null);

  const formatUser = (raw) => {
    if (!raw) return null;
    const rolStr = typeof raw.rol === 'string' ? raw.rol : raw.rol?.codigo || raw.rol?.nombre || 'USER';
    return {
      ...raw,
      rol_str: rolStr,
      isAdmin: rolStr === 'ADMIN',
      // Sin perfil médico propio hay que indicar a qué doctor corresponde cada registro
      puedeElegirDoctor: rolStr === 'ADMIN' || !raw.doctor_id,
      nombre_completo: raw.nombre_completo || `${raw.nombre || ''} ${raw.apellido || ''}`.trim() || raw.username,
    };
  };

  useEffect(() => {
    async function loadUser() {
      if (token) {
        try {
          const profile = await api.getMe();
          const formatted = formatUser(profile);
          setUser(formatted);
          localStorage.setItem('user', JSON.stringify(formatted));
        } catch (e) {
          console.error('Error cargando perfil:', e);
          logout();
        }
      }
      setLoading(false);
    }
    loadUser();
  }, [token]);

  const login = async (username, password) => {
    const res = await api.login(username, password);
    localStorage.setItem(CLAVE_ACTIVIDAD, String(Date.now()));
    localStorage.setItem('token', res.access_token);
    setToken(res.access_token);
    const profile = await api.getMe();
    const formatted = formatUser(profile);
    setUser(formatted);
    localStorage.setItem('user', JSON.stringify(formatted));
    return formatted;
  };

  // Tras cambiar la contraseña, las sesiones anteriores dejan de servir: esta sigue con el token nuevo
  const actualizarSesion = async (nuevoToken) => {
    localStorage.setItem('token', nuevoToken);
    const formatted = formatUser(await api.getMe());
    setUser(formatted);
    localStorage.setItem('user', JSON.stringify(formatted));
    setToken(nuevoToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem(CLAVE_ACTIVIDAD);
    setSegundosParaCierre(null);
    setToken(null);
    setUser(null);
  };

  const actualizarTiempoSesion = async (minutos) => {
    await api.actualizarTiempoSesion(minutos);
    const formatted = formatUser({ ...user, minutos_inactividad: minutos });
    setUser(formatted);
    localStorage.setItem('user', JSON.stringify(formatted));
  };

  // Evita que alguien use una sesión ajena en un equipo que quedó desatendido
  const minutosInactividad = user?.minutos_inactividad;
  useEffect(() => {
    if (!token || !minutosInactividad) return undefined;
    const limite = minutosInactividad * 60000;
    if (!localStorage.getItem(CLAVE_ACTIVIDAD)) localStorage.setItem(CLAVE_ACTIVIDAD, String(Date.now()));

    const revisar = () => {
      if (!localStorage.getItem('token')) {
        logout();
        return;
      }
      const restante = limite - (Date.now() - Number(localStorage.getItem(CLAVE_ACTIVIDAD) || Date.now()));
      if (restante <= 0) {
        sessionStorage.setItem(MENSAJE_INACTIVIDAD, '1');
        logout();
      } else {
        setSegundosParaCierre(restante <= AVISO_CIERRE_MS ? Math.ceil(restante / 1000) : null);
      }
    };
    let ultimoRegistro = 0;
    const registrarActividad = () => {
      const ahora = Date.now();
      if (ahora - ultimoRegistro < 1000) return;
      // Un equipo que despierta tras la hora límite ya no reabre la sesión: primero se revisa
      revisar();
      if (!localStorage.getItem('token')) return;
      ultimoRegistro = ahora;
      localStorage.setItem(CLAVE_ACTIVIDAD, String(ahora));
      setSegundosParaCierre(null);
    };

    revisar();
    const intervalo = setInterval(revisar, 1000);
    EVENTOS_ACTIVIDAD.forEach((evento) => window.addEventListener(evento, registrarActividad, { passive: true, capture: true }));
    document.addEventListener('visibilitychange', revisar);
    return () => {
      clearInterval(intervalo);
      EVENTOS_ACTIVIDAD.forEach((evento) => window.removeEventListener(evento, registrarActividad, { capture: true }));
      document.removeEventListener('visibilitychange', revisar);
    };
  }, [token, minutosInactividad]);

  const rol = user?.rol_str || (typeof user?.rol === 'string' ? user?.rol : user?.rol?.codigo) || '';

  const permisos = user?.permisos || [];
  const tienePermiso = (codigo) => rol === 'ADMIN' || permisos.includes(codigo);

  const value = {
    user,
    tienePermiso,
    token,
    loading,
    login,
    logout,
    actualizarSesion,
    actualizarTiempoSesion,
    segundosParaCierre,
    isAuthenticated: !!token,
    isAdmin: rol === 'ADMIN',
    isDoctor: rol === 'DOCTOR',
    isRecepcion: rol === 'RECEPCION',
    isAsistente: rol === 'ASISTENTE',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe ser usado dentro de AuthProvider');
  return ctx;
}
