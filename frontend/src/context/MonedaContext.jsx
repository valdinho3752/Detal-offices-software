import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

const CLAVE_LOCAL = 'moneda_simbolo';
const POR_DEFECTO = '$';

const MonedaContext = createContext(null);

function leerLocal() {
  try {
    return localStorage.getItem(CLAVE_LOCAL) || POR_DEFECTO;
  } catch {
    return POR_DEFECTO;
  }
}

function guardarLocal(simbolo) {
  try {
    localStorage.setItem(CLAVE_LOCAL, simbolo);
  } catch {
    // Solo evita un parpadeo al abrir: sin almacenamiento también funciona
  }
}

// Ejemplos: $1.500,00 · Bs. 1.500,00 · -S/ 20,00. El backend usa el mismo formato en sus mensajes.
export function formatearMoneda(valor, simbolo) {
  const numero = Number(valor) || 0;
  const cifras = Math.abs(numero).toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${numero < 0 ? '-' : ''}${simbolo}${simbolo.length > 1 ? ' ' : ''}${cifras}`;
}

export function MonedaProvider({ children }) {
  const { token } = useAuth();
  const [simbolo, setSimbolo] = useState(leerLocal);

  useEffect(() => {
    if (!token) return undefined;
    let vigente = true;
    api.getConfiguracion()
      .then((datos) => {
        if (!vigente) return;
        setSimbolo(datos.moneda_simbolo);
        guardarLocal(datos.moneda_simbolo);
      })
      .catch(() => {});
    return () => { vigente = false; };
  }, [token]);

  const cambiarSimbolo = useCallback(async (nuevo) => {
    const datos = await api.updateConfiguracion({ moneda_simbolo: nuevo });
    setSimbolo(datos.moneda_simbolo);
    guardarLocal(datos.moneda_simbolo);
  }, []);

  const valor = useMemo(() => ({
    simbolo,
    moneda: (monto) => formatearMoneda(monto, simbolo),
    cambiarSimbolo,
  }), [simbolo, cambiarSimbolo]);

  return <MonedaContext.Provider value={valor}>{children}</MonedaContext.Provider>;
}

export function useMoneda() {
  const contexto = useContext(MonedaContext);
  if (!contexto) throw new Error('useMoneda debe usarse dentro de MonedaProvider');
  return contexto;
}
