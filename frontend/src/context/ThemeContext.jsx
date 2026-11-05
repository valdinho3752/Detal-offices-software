import React, { createContext, useContext, useEffect, useState } from 'react';
import { useClinica } from './ClinicaContext';

const CLAVE_PREFERENCIA = 'tema_preferido';

const ThemeContext = createContext();

function leerPreferencia() {
  try {
    return localStorage.getItem(CLAVE_PREFERENCIA);
  } catch {
    return null;
  }
}

function guardarPreferencia(tema) {
  try {
    localStorage.setItem(CLAVE_PREFERENCIA, tema);
  } catch {
    // Sin almacenamiento, la elección dura hasta cerrar la página
  }
}

export function ThemeProvider({ children }) {
  const { temaPorDefecto } = useClinica();
  const [preferencia, setPreferencia] = useState(leerPreferencia);
  // Quien no eligió un tema sigue el de la clínica; quien lo eligió conserva el suyo en este equipo
  const theme = preferencia || (temaPorDefecto === 'claro' ? 'light' : 'dark');

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', theme === 'dark');
    root.classList.toggle('light', theme !== 'dark');
  }, [theme]);

  const toggleTheme = () => {
    const nuevo = theme === 'dark' ? 'light' : 'dark';
    guardarPreferencia(nuevo);
    setPreferencia(nuevo);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, isDark: theme === 'dark', tienePreferencia: Boolean(preferencia) }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme debe ser usado dentro de un ThemeProvider');
  }
  return context;
}
