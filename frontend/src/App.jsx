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
              <Route path="usuarios" element={<UsuariosRolesView />} />
              <Route path="pacientes" element={<PacientesView />} />
              <Route path="odontograma" element={<OdontogramaView />} />
              <Route path="citas" element={<CitasAgendaView />} />
              <Route path="asistencia" element={<AsistenciaFichajeView />} />
              <Route path="evolucion" element={<EvolucionClinicaView />} />
              <Route path="visitas" element={<EvolucionClinicaView />} />
              <Route path="radiografias" element={<VisorRadiografiasView />} />
              <Route path="protesis" element={<ProtesisLaboratorioView />} />
              <Route path="caja" element={<CajaOperativaView />} />
              <Route path="cobranzas" element={<CobranzasView />} />
              <Route path="nomina" element={<NominaComisionesView />} />
              <Route path="auditoria" element={<AuditoriaForenseView />} />
              <Route path="reportes" element={<ReportesBIView />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
