import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const CLAVE_LOCAL = 'clinica_publica';
const POR_DEFECTO = { nombre_clinica: 'Clínica Dental', tema_por_defecto: 'oscuro', logo_url: null };

const ClinicaContext = createContext(null);

function leerLocal() {
  try {
    return { ...POR_DEFECTO, ...JSON.parse(localStorage.getItem(CLAVE_LOCAL) || '{}') };
  } catch {
    return POR_DEFECTO;
  }
}

function guardarLocal(datos) {
  try {
    localStorage.setItem(CLAVE_LOCAL, JSON.stringify(datos));
  } catch {
    // Solo evita un parpadeo al abrir: sin almacenamiento también funciona
  }
}

export function ClinicaProvider({ children }) {
  const [clinica, setClinica] = useState(leerLocal);

  const aplicar = useCallback((datos) => {
    const publica = {
      nombre_clinica: datos.nombre_clinica,
      tema_por_defecto: datos.tema_por_defecto,
      logo_url: datos.logo_url,
    };
    setClinica(publica);
    guardarLocal(publica);
  }, []);

  useEffect(() => {
    api.getConfiguracionPublica().then(aplicar).catch(() => {});
  }, [aplicar]);

  useEffect(() => {
    document.title = clinica.nombre_clinica;
    const icono = document.querySelector('link[rel="icon"]');
    if (!icono) return;
    if (!icono.dataset.original) icono.dataset.original = icono.href;
    icono.href = clinica.logo_url || icono.dataset.original;
  }, [clinica.nombre_clinica, clinica.logo_url]);

  const valor = useMemo(() => ({
    nombreClinica: clinica.nombre_clinica,
    logoUrl: clinica.logo_url,
    temaPorDefecto: clinica.tema_por_defecto,
    guardarClinica: async (datos) => aplicar(await api.updateConfiguracion(datos)),
    subirLogo: async (archivo) => aplicar(await api.subirLogo(archivo)),
    quitarLogo: async () => aplicar(await api.quitarLogo()),
  }), [clinica, aplicar]);

  return <ClinicaContext.Provider value={valor}>{children}</ClinicaContext.Provider>;
}

export function useClinica() {
  const contexto = useContext(ClinicaContext);
  if (!contexto) throw new Error('useClinica debe usarse dentro de ClinicaProvider');
  return contexto;
}
