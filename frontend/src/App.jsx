import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';

// Vistas HU-01 a HU-14
import LoginView from './views/LoginView';
import DashboardView from './views/DashboardView';
import UsuariosRolesView from './views/UsuariosRolesView';
import PacientesView from './views/PacientesView';
import OdontogramaView from './views/OdontogramaView';
import CitasAgendaView from './views/CitasAgendaView';
import AsistenciaFichajeView from './views/AsistenciaFichajeView';
import EvolucionClinicaView from './views/EvolucionClinicaView';
import VisorRadiografiasView from './views/VisorRadiografiasView';
import ProtesisLaboratorioView from './views/ProtesisLaboratorioView';
import CajaOperativaView from './views/CajaOperativaView';
import CobranzasView from './views/CobranzasView';
import NominaComisionesView from './views/NominaComisionesView';
import AuditoriaForenseView from './views/AuditoriaForenseView';
import ReportesBIView from './views/ReportesBIView';
import TratamientosCatalogoView from './views/TratamientosCatalogoView';
import { puedeAcceder } from './config/accesos';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white text-sm">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-400">Cargando Clínica Dental Gustavo...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// Sin acceso a una pantalla se vuelve al panel principal; la API también rechaza la operación
function RutaProtegida({ ruta, children }) {
  const auth = useAuth();
  return puedeAcceder(ruta, auth) ? children : <Navigate to="/" replace />;
}

const RUTAS = [
  ['usuarios', UsuariosRolesView],
  ['pacientes', PacientesView],
  ['odontograma', OdontogramaView],
  ['citas', CitasAgendaView],
  ['asistencia', AsistenciaFichajeView],
  ['evolucion', EvolucionClinicaView],
  ['visitas', EvolucionClinicaView],
  ['radiografias', VisorRadiografiasView],
  ['protesis', ProtesisLaboratorioView],
  ['caja', CajaOperativaView],
  ['cobranzas', CobranzasView],
  ['nomina', NominaComisionesView],
  ['auditoria', AuditoriaForenseView],
  ['reportes', ReportesBIView],
  ['tratamientos', TratamientosCatalogoView],
];

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginView />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardView />} />
              {RUTAS.map(([ruta, Vista]) => (
                <Route
                  key={ruta}
                  path={ruta}
                  element={
                    <RutaProtegida ruta={`/${ruta}`}>
                      <Vista />
                    </RutaProtegida>
                  }
                />
              ))}
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
