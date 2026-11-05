import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { aFechaLocal } from '../utils/fechas';
import {
  Camera,
  User,
  Plus,
  ZoomIn,
  Eye,
  Trash2,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Sliders,
  FileText,
} from 'lucide-react';
import PacienteSearchInput from '../components/PacienteSearchInput';


// Valores aceptados por la API (TipoEstudioImagenEnum) y su nombre en pantalla
const TIPOS_ESTUDIO = {
  PERIAPICAL: 'Periapical',
  PANORAMICA: 'Panorámica (Ortopanto)',
  ALETA_MORDIDA: 'Bitewing (Aleta)',
  OCLUSAL: 'Oclusal',
  CEFALOMETRICA: 'Cefalométrica',
  CONE_BEAM_CBCT: 'CBCT Tomografía 3D',
  FOTOGRAFIA_CLINICA: 'Fotografía Clínica',
};

export default function VisorRadiografiasView() {
  const [searchParams] = useSearchParams();
  const pacienteIdParam = searchParams.get('paciente_id');

  const [pacientes, setPacientes] = useState([]);
  const [selectedPacienteId, setSelectedPacienteId] = useState(pacienteIdParam || '');
  const [radiografias, setRadiografias] = useState([]);
  const [piezaFdiFiltro, setPiezaFdiFiltro] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Visor modal
  const [selectedRx, setSelectedRx] = useState(null);
  const [invertColors, setInvertColors] = useState(false);

  // Subir / Registrar nueva RX
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [rxForm, setRxForm] = useState({
    tipo: 'PERIAPICAL',
    pieza_fdi: '',
    url_archivo: '',
    informe_diagnostico: '',
    fecha_toma: aFechaLocal(),
  });

  useEffect(() => {
    const loadPacientes = async () => {
      try {
        const pRes = await api.getPacientes('', 0, 100);
        setPacientes(Array.isArray(pRes) ? pRes : []);
        if (pacienteIdParam) {
          setSelectedPacienteId(pacienteIdParam);
        } else if (pRes?.length > 0) {
          setSelectedPacienteId(pRes[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadPacientes();
  }, []);

  const loadRadiografias = async () => {
    if (!selectedPacienteId) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.getRadiografias(
        selectedPacienteId,
        piezaFdiFiltro ? parseInt(piezaFdiFiltro) : null
      );
      setRadiografias(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Error cargando radiografías');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRadiografias();
  }, [selectedPacienteId, piezaFdiFiltro]);

  const handleSaveRx = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.createRadiografia({
        paciente_id: selectedPacienteId,
        tipo_estudio: rxForm.tipo,
        titulo: rxForm.pieza_fdi
          ? `${TIPOS_ESTUDIO[rxForm.tipo]} - Pieza ${rxForm.pieza_fdi}`
          : TIPOS_ESTUDIO[rxForm.tipo],
        pieza_fdi: rxForm.pieza_fdi ? parseInt(rxForm.pieza_fdi) : null,
        archivo_url: rxForm.url_archivo.trim(),
        informe_diagnostico: rxForm.informe_diagnostico,
        fecha_toma: rxForm.fecha_toma,
      });

      setSuccess('Radiografía registrada con éxito');
      setShowUploadModal(false);
      setRxForm({
        tipo: 'PERIAPICAL',
        pieza_fdi: '',
        url_archivo: '',
        informe_diagnostico: '',
        fecha_toma: aFechaLocal(),
      });
      setTimeout(() => setSuccess(''), 3000);
      loadRadiografias();
    } catch (err) {
      setError(err.message || 'Error al guardar radiografía');
    }
  };

  const handleDeleteRx = async (id) => {
    if (!window.confirm('¿Seguro que deseas eliminar esta radiografía?')) return;
    try {
      await api.deleteRadiografia(id);
      setSuccess('Radiografía eliminada');
      setTimeout(() => setSuccess(''), 3000);
      loadRadiografias();
    } catch (err) {
      setError(err.message || 'Error al eliminar');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Visor Radiográfico & Diagnóstico por Imagen</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Gestión de radiografías digitales periapicales, panorámicas y tomografías por pieza FDI
          </p>
        </div>

        {/* Selector de Paciente y Botón Cargar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="w-full sm:w-72">
            <PacienteSearchInput
              pacientes={pacientes}
              selectedPacienteId={selectedPacienteId}
              onSelectPaciente={(id) => setSelectedPacienteId(id)}
              placeholder="Buscar paciente por nombre o CI..."
            />
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-primary-600/20 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Subir Radiografía
          </button>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-500 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Filtro por Pieza FDI */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-4 flex flex-wrap items-center gap-4 shadow-sm">
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Filtrar por Pieza Dental FDI:</span>
        <input
          type="number"
          placeholder="ej. 16, 21, 46 (dejar vacío para ver todas)"
          value={piezaFdiFiltro}
          onChange={(e) => setPiezaFdiFiltro(e.target.value)}
          className="px-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs w-56 font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        {piezaFdiFiltro && (
          <button
            onClick={() => setPiezaFdiFiltro('')}
            className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-semibold"
          >
            Limpiar filtro
          </button>
        )}
      </div>

      {/* Galería de Radiografías */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Cargando estudios radiológicos...</div>
        ) : radiografias.length === 0 ? (
          <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-12 text-center text-slate-500 dark:text-slate-400 shadow-sm">
            <Camera className="w-12 h-12 text-slate-400 dark:text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">No hay radiografías registradas</h3>
            <p className="text-xs text-slate-500 mt-1">
              Sube la primera imagen radiográfica con su informe de diagnóstico.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {radiografias.map((rx) => {
              const fechaStr = rx.fecha_toma ? rx.fecha_toma.slice(0, 10) : 'Fecha N/D';

              return (
                <div
                  key={rx.id}
                  className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl overflow-hidden shadow-sm flex flex-col justify-between group hover:border-primary-500/50 transition"
                >
                  {/* Vista Previa Imagen */}
                  <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden cursor-pointer"
                    onClick={() => {
                      setSelectedRx(rx);
                      setInvertColors(false);
                    }}
                  >
                    <img
                      src={rx.archivo_url}
                      alt={rx.titulo}
                      className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                    />
                    <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-2">
                      <span className="p-2 bg-slate-900/80 rounded-full text-white">
                        <Eye className="w-5 h-5" />
                      </span>
                    </div>

                    <div className="absolute top-2 left-2 px-2 py-0.5 bg-slate-950/80 backdrop-blur rounded text-[10px] font-bold text-white uppercase border border-slate-700">
                      {TIPOS_ESTUDIO[rx.tipo_estudio] || rx.tipo_estudio}
                    </div>

                    {rx.pieza_fdi && (
                      <div className="absolute top-2 right-2 px-2 py-0.5 bg-primary-600/90 text-white rounded text-[10px] font-mono font-bold">
                        Pieza #{rx.pieza_fdi}
                      </div>
                    )}
                  </div>

                  {/* Diagnóstico y Detalles */}
                  <div className="p-4 space-y-2 flex-1 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                        <span className="flex items-center gap-1 font-mono">
                          <Calendar className="w-3.5 h-3.5 text-primary-500" /> {fechaStr}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-200 line-clamp-2">
                        {rx.informe_diagnostico || 'Sin informe diagnóstico registrado.'}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
                      <button
                        onClick={() => {
                          setSelectedRx(rx);
                          setInvertColors(false);
                        }}
                        className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-semibold flex items-center gap-1"
                      >
                        <ZoomIn className="w-3.5 h-3.5" /> Abrir Visor
                      </button>

                      <button
                        onClick={() => handleDeleteRx(rx.id)}
                        className="p-1 text-slate-400 hover:text-rose-500 transition"
                        title="Eliminar radiografía"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal Visor Clínico de Gran Formato */}
      {selectedRx && (
        <div className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-4xl p-6 shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-slate-900 dark:text-white uppercase">{TIPOS_ESTUDIO[selectedRx.tipo_estudio] || selectedRx.tipo_estudio}</span>
                {selectedRx.pieza_fdi && (
                  <span className="px-2 py-0.5 bg-primary-600 text-white rounded text-xs font-mono font-bold">
                    Pieza FDI #{selectedRx.pieza_fdi}
                  </span>
                )}
                <span className="text-xs text-slate-500 dark:text-slate-400">Fecha: {selectedRx.fecha_toma?.slice(0, 10)}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setInvertColors(!invertColors)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${
                    invertColors
                      ? 'bg-amber-500/20 border-amber-500 text-amber-600 dark:text-amber-300'
                      : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5" /> Invertir Negativo
                </button>
                <button
                  onClick={() => setSelectedRx(null)}
                  className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-white rounded-lg text-xs font-bold transition"
                >
                  Cerrar
                </button>
              </div>
            </div>

            {/* Imagen Ampliada */}
            <div className="flex-1 min-h-[350px] bg-black rounded-xl overflow-hidden flex items-center justify-center my-4 relative">
              <img
                src={selectedRx.archivo_url}
                alt="Radiografía Dental"
                className={`max-h-[500px] w-auto object-contain transition duration-200 ${
                  invertColors ? 'filter invert contrast-125' : ''
                }`}
              />
            </div>

            {/* Informe Diagnóstico */}
            <div className="p-3.5 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
              <span className="text-xs font-bold text-primary-600 dark:text-primary-400 uppercase tracking-wider block mb-1">
                Informe Diagnóstico Radiológico:
              </span>
              <p className="text-xs text-slate-700 dark:text-slate-200">
                {selectedRx.informe_diagnostico || 'Sin hallazgos patológicos descritos.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Modal Subir Radiografía */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Registrar Estudio Radiológico</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Asocia la imagen a una pieza dental y redacta el informe diagnóstico.
            </p>

            <form onSubmit={handleSaveRx} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo de Estudio *</label>
                  <select
                    value={rxForm.tipo}
                    onChange={(e) => setRxForm({ ...rxForm, tipo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {Object.entries(TIPOS_ESTUDIO).map(([valor, nombre]) => (
                      <option key={valor} value={valor} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">{nombre}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Pieza FDI Asociada</label>
                  <input
                    type="number"
                    placeholder="ej. 16, 21 (vacío = general)"
                    value={rxForm.pieza_fdi}
                    onChange={(e) => setRxForm({ ...rxForm, pieza_fdi: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">URL de la Imagen *</label>
                <input
                  type="url"
                  required
                  placeholder="https://..."
                  value={rxForm.url_archivo}
                  onChange={(e) => setRxForm({ ...rxForm, url_archivo: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Fecha de Toma</label>
                <input
                  type="date"
                  value={rxForm.fecha_toma}
                  onChange={(e) => setRxForm({ ...rxForm, fecha_toma: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Informe Diagnóstico Radiológico</label>
                <textarea
                  rows="3"
                  placeholder="Zona radiolúcida periapical compatible con granuloma, ensanchamiento del ligamento periodontal..."
                  value={rxForm.informe_diagnostico}
                  onChange={(e) => setRxForm({ ...rxForm, informe_diagnostico: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Guardar Radiografía
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
