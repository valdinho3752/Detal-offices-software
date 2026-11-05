import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  const formatUser = (raw) => {
    if (!raw) return null;
    const rolStr = typeof raw.rol === 'string' ? raw.rol : raw.rol?.codigo || raw.rol?.nombre || 'USER';
    return {
      ...raw,
      rol_str: rolStr,
      isAdmin: rolStr === 'ADMIN',
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
    localStorage.setItem('token', res.access_token);
    setToken(res.access_token);
    const profile = await api.getMe();
    const formatted = formatUser(profile);
    setUser(formatted);
    localStorage.setItem('user', JSON.stringify(formatted));
    return formatted;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const rol = user?.rol_str || (typeof user?.rol === 'string' ? user?.rol : user?.rol?.codigo) || '';

  const value = {
    user,
    token,
    loading,
    login,
    logout,
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
