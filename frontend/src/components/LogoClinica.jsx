import React from 'react';
import { useClinica } from '../context/ClinicaContext';

// Sin logo propio se muestra el diente, para que la marca nunca quede vacía
export default function LogoClinica({ clase = 'w-10 h-10', claseIcono = 'text-xl' }) {
  const { logoUrl, nombreClinica } = useClinica();

  if (logoUrl) {
    return <img src={logoUrl} alt={`Logo de ${nombreClinica}`} className={`${clase} rounded-xl object-contain flex-shrink-0`} />;
  }
  return (
    <div
      aria-hidden="true"
      className={`${clase} ${claseIcono} rounded-xl bg-gradient-to-tr from-primary-600 to-teal-500 flex items-center justify-center text-white shadow-lg shadow-primary-600/30 font-bold flex-shrink-0`}
    >
      🦷
    </div>
  );
}
