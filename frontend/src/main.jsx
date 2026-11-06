import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '@fontsource-variable/inter';
import './index.css';
import { cargarZonaClinica } from './utils/fechas';

// Las primeras fechas que se dibujan ya deben estar en la zona de la clínica
cargarZonaClinica().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});
