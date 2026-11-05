import React from 'react';
import { AlertCircle } from 'lucide-react';

// Error dentro de un formulario modal: la alerta de la página queda oculta detrás del modal
export default function ErrorModal({ mensaje }) {
  if (!mensaje) return null;
  return (
    <div
      role="alert"
      className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2"
    >
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      {mensaje}
    </div>
  );
}
