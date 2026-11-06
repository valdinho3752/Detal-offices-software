import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import {
  Activity,
  Plus,
  Trash2,
  CheckCircle2,
  Clock,
  Sparkles,
  AlertCircle,
  FileText,
  User,
  Shield,
  RotateCcw,
  Search,
  Calculator,
  Save,
  Filter,
  Ban,
  Brush,
  ChevronRight,
  Info,
  ClipboardList,
  Eye,
  Layers,
  FileSpreadsheet,
} from 'lucide-react';
import { useMoneda } from '../context/MonedaContext';
import PacienteSearchInput from '../components/PacienteSearchInput';

// Cuadrantes FDI Dentición Adulta (Permanente)
// Pantalla Izquierda: LADO DERECHO DEL PACIENTE
const CUADRANTE_1 = [18, 17, 16, 15, 14, 13, 12, 11]; // Superior Derecho
const CUADRANTE_4 = [48, 47, 46, 45, 44, 43, 42, 41]; // Inferior Derecho

// Pantalla Derecha: LADO IZQUIERDO DEL PACIENTE
const CUADRANTE_2 = [21, 22, 23, 24, 25, 26, 27, 28]; // Superior Izquierdo
const CUADRANTE_3 = [31, 32, 33, 34, 35, 36, 37, 38]; // Inferior Izquierdo

// Cuadrantes FDI Dentición Temporal (Niños)
const TEMP_1 = [55, 54, 53, 52, 51];
const TEMP_2 = [61, 62, 63, 64, 65];
const TEMP_4 = [85, 84, 83, 82, 81];
const TEMP_3 = [71, 72, 73, 74, 75];

// Estados Clínicos actualizados según solicitud
const ESTADOS_CLINICOS = [
  {
    id: 'EXISTENTE_PREVIO',
    label: 'Diagnóstico y evaluación inicial',
    shortLabel: 'Diagnóstico Inicial',
    colorHex: '#10B981', // Verde
    badgeClass: 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-500/40',
    dotClass: 'bg-emerald-500',
  },
  {
    id: 'REQUERIDO_PATOLOGIA',
    label: 'Plan de tratamiento',
    shortLabel: 'Plan de Tratamiento',
    colorHex: '#EF4444', // Rojo
    badgeClass: 'bg-rose-500/10 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400 border-rose-500/40',
    dotClass: 'bg-rose-500',
  },
  {
    id: 'REALIZADO_EN_CLINICA',
    label: 'Alta clínica / Control posterior',
    shortLabel: 'Alta / Control',
    colorHex: '#3B82F6', // Azul
    badgeClass: 'bg-blue-500/10 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400 border-blue-500/40',
    dotClass: 'bg-blue-500',
  },
  {
    id: 'PIEZA_INEXISTENTE',
    label: 'Pieza inexistente',
    shortLabel: 'Inexistente',
    colorHex: '#64748B', // Gris
    badgeClass: 'bg-slate-500/10 text-slate-600 dark:bg-slate-500/20 dark:text-slate-300 border-slate-500/40',
    dotClass: 'bg-slate-500',
  },
];

// Caras anatómicas dentales
const SUPERFICIES_LIST = [
  { id: 'OCLUSAL_INCISAL', label: 'Oclusal / Incisal', short: 'Oclusal', desc: 'Cara masticatoria o borde incisal (Centro)' },
  { id: 'VESTIBULAR', label: 'Vestibular', short: 'Vestibular', desc: 'Cara exterior hacia labios / mejilla' },
  { id: 'LINGUAL_PALATINO', label: 'Lingual / Palatino', short: 'Lingual/Pal', desc: 'Cara interior hacia lengua / paladar' },
  { id: 'MESIAL', label: 'Mesial', short: 'Mesial', desc: 'Cara orientada hacia la línea media / dientes centrales' },
  { id: 'DISTAL', label: 'Distal', short: 'Distal', desc: 'Cara orientada hacia distal / posterior' },
  { id: 'RAIZ', label: 'Raíz Dental', short: 'Raíz', desc: 'Conducto radicular, endodoncia, perno' },
  { id: 'GENERAL', label: 'Pieza Completa', short: 'Diente Entero', desc: 'Toda la pieza (corona, implante, extracción)' },
];

// Opciones de Condición / Diagnóstico con las que ingresó el paciente
export const CONDICIONES_INGRESO = [
  { id: 'OBTURACION_RESINA', label: 'Resina Previa', fullLabel: 'Restauración previa de Resina' },
  { id: 'OBTURACION_AMALGAMA', label: 'Amalgama Previa', fullLabel: 'Restauración previa de Amalgama' },
  { id: 'CORONA', label: 'Corona Previa', fullLabel: 'Corona protésica previa' },
  { id: 'ENDODONCIA', label: 'Endodoncia Previa', fullLabel: 'Tratamiento de conducto previo' },
  { id: 'SELLANTE', label: 'Sellante Previo', fullLabel: 'Sellante de fosas previo' },
  { id: 'INCRUSTACION', label: 'Incrustación Previa', fullLabel: 'Incrustación estética previa' },
  { id: 'CARIES', label: 'Caries al Ingreso', fullLabel: 'Caries detectada al ingreso' },
  { id: 'FRACTURA', label: 'Fractura al Ingreso', fullLabel: 'Fractura o fisura dental' },
  { id: 'DESGASTE_EROSION', label: 'Desgaste / Bruxismo', fullLabel: 'Desgaste / Faceta de atrición' },
  { id: 'SANO', label: 'Sano / Normal', fullLabel: 'Diente o cara clínicamente sana' },
];

export const CONDICIONES_LABEL_MAP = {
  SANO: 'Sano / Sin alteración',
  OBTURACION_RESINA: 'Restauración previa de Resina',
  OBTURACION_AMALGAMA: 'Restauración previa de Amalgama',
  CORONA: 'Corona protésica previa',
  ENDODONCIA: 'Tratamiento de conducto previo',
  SELLANTE: 'Sellante de fosas previo',
  INCRUSTACION: 'Incrustación previa',
  CARIES: 'Caries presente al ingreso',
  FRACTURA: 'Fractura / Fisura al ingreso',
  DESGASTE_EROSION: 'Desgaste / Bruxismo al ingreso',
  EXTRAIDO: 'Pieza inexistente / ausente',
};

// Helper: ¿Está en el lado izquierdo del paciente (lado derecho en pantalla)?
// Determina la orientación hacia la línea media
const isRightSideOfArch = (fdi) => {
  const d1 = parseInt(fdi.toString()[0]);
  return d1 === 2 || d1 === 3 || d1 === 6 || d1 === 7;
};

// Helper: Anatomía radicular y orientación
const getToothAnatomy = (fdi) => {
  const isUpper = (fdi >= 11 && fdi <= 28) || (fdi >= 51 && fdi <= 65);
  let rootCount = 1;

  if (isUpper) {
    if ([18, 17, 16, 26, 27, 28, 54, 55, 64, 65].includes(fdi)) {
      rootCount = 3; // Molares superiores: 3 raíces
    } else if ([14, 24].includes(fdi)) {
      rootCount = 2; // Primer premolar superior: 2 raíces
    } else {
      rootCount = 1;
    }
  } else {
    if ([48, 47, 46, 36, 37, 38, 84, 85, 74, 75].includes(fdi)) {
      rootCount = 2; // Molares inferiores: 2 raíces
    } else {
      rootCount = 1;
    }
  }

  return { isUpper, rootCount };
};

// Nombre anatómico para el odontólogo
const getToothName = (fdi) => {
  const str = fdi.toString();
  const d1 = parseInt(str[0]);
  const d2 = parseInt(str[1]);

  let arch = '';
  let side = '';
  let type = '';

  if (d1 === 1) { arch = 'Superior'; side = 'Derecho'; }
  else if (d1 === 2) { arch = 'Superior'; side = 'Izquierdo'; }
  else if (d1 === 3) { arch = 'Inferior'; side = 'Izquierdo'; }
  else if (d1 === 4) { arch = 'Inferior'; side = 'Derecho'; }
  else if (d1 === 5) { arch = 'Temp. Superior'; side = 'Derecho'; }
  else if (d1 === 6) { arch = 'Temp. Superior'; side = 'Izquierdo'; }
  else if (d1 === 7) { arch = 'Temp. Inferior'; side = 'Izquierdo'; }
  else if (d1 === 8) { arch = 'Temp. Inferior'; side = 'Derecho'; }

  if (d1 <= 4) {
    switch (d2) {
      case 1: type = 'Incisivo Central'; break;
      case 2: type = 'Incisivo Lateral'; break;
      case 3: type = 'Canino'; break;
      case 4: type = 'Primer Premolar'; break;
      case 5: type = 'Segundo Premolar'; break;
      case 6: type = 'Primer Molar'; break;
      case 7: type = 'Segundo Molar'; break;
      case 8: type = 'Tercer Molar (Cordal)'; break;
      default: type = 'Pieza Dental';
    }
  } else {
    switch (d2) {
      case 1: type = 'Incisivo Central Deciduo'; break;
      case 2: type = 'Incisivo Lateral Deciduo'; break;
      case 3: type = 'Canino Deciduo'; break;
      case 4: type = 'Primer Molar Deciduo'; break;
      case 5: type = 'Segundo Molar Deciduo'; break;
      default: type = 'Pieza Temporal';
    }
  }
  return `${type} ${arch} ${side}`;
};

export default function OdontogramaView() {
  const { moneda, simbolo } = useMoneda();
  const { user } = useAuth();
  const { isDark } = useTheme();
  const [searchParams] = useSearchParams();
  const pacienteIdParam = searchParams.get('paciente_id');

  // Estado general de Pacientes y Doctores
  const [pacientes, setPacientes] = useState([]);
  const [selectedPacienteId, setSelectedPacienteId] = useState(pacienteIdParam || '');
  const [doctores, setDoctores] = useState([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [denticion, setDenticion] = useState('ADULTA'); // 'ADULTA' | 'TEMPORAL'

  // Un solo odontograma por paciente
  const [odontograma, setOdontograma] = useState(null);
  const [piezasMap, setPiezasMap] = useState({});

  // Paleta de estados
  const [estadoClinicoActivo, setEstadoClinicoActivo] = useState('REQUERIDO_PATOLOGIA');

  // Pieza y cara seleccionada
  const [selectedPiezaFdi, setSelectedPiezaFdi] = useState(16);
  const [superficieSeleccionada, setSuperficieSeleccionada] = useState('OCLUSAL_INCISAL');
  const [observacionHallazgo, setObservacionHallazgo] = useState('');

  // Diagnóstico y Evaluación Inicial (Estado de Ingreso)
  const [condicionInicial, setCondicionInicial] = useState('OBTURACION_RESINA');
  const [detalleInicial, setDetalleInicial] = useState('');
  const [seccionTab, setSeccionTab] = useState('TODOS'); // 'TODOS' | 'DIAGNOSTICO_INICIAL' | 'PRESUPUESTO'

  // Catálogo de tratamientos
  const [catalogo, setCatalogo] = useState([]);
  const [catalogoSearch, setCatalogoSearch] = useState('');
  const [catalogoCategoria, setCatalogoCategoria] = useState('TODAS');

  // Planes de tratamiento y presupuesto
  const [planes, setPlanes] = useState([]);
  const [activePlan, setActivePlan] = useState(null);
  const [draftItems, setDraftItems] = useState([]);

  // Notificaciones y loaders
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Carga inicial de datos maestros
  useEffect(() => {
    const init = async () => {
      try {
        const [pacRes, catRes, docRes] = await Promise.all([
          api.getPacientes('', 0, 100),
          api.getCatalogoTratamientos(),
          api.getDoctores(),
        ]);
        setPacientes(Array.isArray(pacRes) ? pacRes : []);
        setCatalogo(Array.isArray(catRes) ? catRes : []);
        const docs = Array.isArray(docRes) ? docRes : [];
        setDoctores(docs);

        let initialDocId = '';
        if (user?.doctor_id) {
          initialDocId = user.doctor_id;
        } else if (docs.length > 0) {
          const myDoc = docs.find((d) => d.usuario_id === user?.id);
          initialDocId = myDoc ? myDoc.id : docs[0].id;
        }
        setSelectedDoctorId(initialDocId);

        if (pacienteIdParam) {
          setSelectedPacienteId(pacienteIdParam);
        } else if (pacRes?.length > 0) {
          setSelectedPacienteId(pacRes[0].id);
        }
      } catch (err) {
        console.error('Error inicializando datos maestros:', err);
      }
    };
    init();
  }, []);

  // Reasignación de Doctor (Admin)
  const handleDoctorChange = async (newDocId) => {
    setSelectedDoctorId(newDocId);
    if (user?.isAdmin && odontograma?.id && odontograma.doctor_id !== newDocId) {
      try {
        await api.updateOdontograma(odontograma.id, { doctor_id: newDocId });
        setSuccess('Doctor asignado al odontograma actualizado correctamente');
        setTimeout(() => setSuccess(''), 2500);
      } catch (err) {
        setError(err.message || 'Error al reasignar doctor');
      }
    }
  };

  // Carga del Odontograma único del paciente y planes
  const loadPacienteOdonto = async () => {
    if (!selectedPacienteId) return;
    setLoading(true);
    setError('');
    try {
      const listaOdontos = await api.getOdontogramas(selectedPacienteId);
      let actualOdonto = null;

      if (listaOdontos && listaOdontos.length > 0) {
        actualOdonto = await api.getOdontograma(listaOdontos[0].id);
      } else {
        // Crear el odontograma del paciente
        const nuevo = await api.createOdontograma({
          paciente_id: selectedPacienteId,
          doctor_id: selectedDoctorId || user?.doctor_id,
          tipo_denticion: denticion === 'ADULTA' ? 'ADULTA_PERMANENTE' : 'INFANTIL_DECIDUA',
          tipo_registro: 'INICIAL_INGRESO',
          observaciones_generales: 'Odontograma Clínico Integral',
        });
        actualOdonto = await api.getOdontograma(nuevo.id);
      }

      setOdontograma(actualOdonto);

      // Mapear piezas dentales por número FDI
      const map = {};
      if (actualOdonto?.piezas) {
        actualOdonto.piezas.forEach((p) => {
          map[p.numero_fdi] = p;
        });
      }
      setPiezasMap(map);

      // Cargar planes de tratamiento
      const listaPlanes = await api.getPlanes(selectedPacienteId);
      const planesArr = Array.isArray(listaPlanes) ? listaPlanes : [];
      setPlanes(planesArr);
      const activeP = planesArr.find((p) => p.estado !== 'COMPLETADO' && p.estado !== 'CANCELADO') || planesArr[0] || null;
      setActivePlan(activeP);

      if (activeP?.items) {
        setDraftItems(
          activeP.items.map((it) => ({
            id: it.id,
            plan_id: it.plan_id,
            pieza_fdi: it.pieza_fdi,
            superficie: it.superficie || (it.observaciones?.startsWith('Superficie: ') ? it.observaciones.replace('Superficie: ', '') : 'GENERAL'),
            tratamiento_id: it.tratamiento_id,
            nombre_tratamiento: it.tratamiento?.nombre || 'Procedimiento Dental',
            categoria: it.tratamiento?.categoria || 'RESTAURADORA',
            precio_unitario: Number(it.precio_unitario ?? it.costo_acordado ?? 0),
            descuento: Number(it.descuento ?? 0),
            costo_acordado: Number(it.costo_acordado ?? 0),
            es_proxima_sesion: Boolean(it.es_proxima_sesion || it.estado === 'PROXIMA_SESION'),
            estado: it.estado || 'PENDIENTE',
          }))
        );
      } else {
        setDraftItems([]);
      }
    } catch (err) {
      setError(err.message || 'Error cargando odontograma del paciente');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPacienteOdonto();
  }, [selectedPacienteId, denticion]);

  // Selección de diente
  const handleSelectTooth = (fdi) => {
    setSelectedPiezaFdi(fdi);
  };

  // Obtener color clínico de una superficie
  const getSurfaceColor = (fdi, surfaceName) => {
    const piezaData = piezasMap[fdi];
    const hallazgos = piezaData?.hallazgos || [];

    // Si la pieza está marcada como inexistente (GENERAL con gris o EXTRAIDO)
    const isInexistente = piezaData?.estado_general === 'EXTRAIDO' || hallazgos.some((x) => x.color_hex === '#64748B' && x.superficie === 'GENERAL');
    if (isInexistente) {
      return '#64748B'; // Gris
    }

    // Comprobar si el plan de tratamiento tiene esta pieza/superficie en ALTA MÉDICA (COMPLETADO)
    const isCompletedInPlan = draftItems.some((it) => {
      if (Number(it.pieza_fdi) !== Number(fdi) || it.estado !== 'COMPLETADO') return false;
      const itSup = (it.superficie || '').toUpperCase();
      if (!itSup || itSup === 'GENERAL' || itSup === surfaceName) return true;
      if (surfaceName === 'OCLUSAL_INCISAL' && (itSup === 'OCLUSAL' || itSup === 'OCLUSAL_INCISAL')) return true;
      if (surfaceName === 'LINGUAL_PALATINO' && (itSup === 'LINGUAL' || itSup === 'PALATINO' || itSup === 'LINGUAL_PALATINO')) return true;
      if (surfaceName === 'RAIZ' && itSup === 'RAIZ') return true;
      return false;
    });

    if (isCompletedInPlan) {
      return '#3B82F6'; // Azul: Alta Médica / Realizado en Clínica
    }

    // 1. Hallazgo específico en la cara
    const matchingHallazgos = hallazgos.filter((x) => {
      if (x.superficie === surfaceName) return true;
      if (surfaceName === 'OCLUSAL_INCISAL' && (x.superficie === 'OCLUSAL' || x.superficie === 'OCLUSAL_INCISAL')) return true;
      if (surfaceName === 'LINGUAL_PALATINO' && (x.superficie === 'LINGUAL' || x.superficie === 'PALATINO' || x.superficie === 'LINGUAL_PALATINO')) return true;
      if (surfaceName === 'RAIZ' && x.superficie === 'RAIZ') return true;
      return false;
    });

    if (matchingHallazgos.length > 0) {
      // Prioridad 1: Realizado en clínica / Alta médica (Azul)
      const blueH = matchingHallazgos.find(
        (x) => x.color_hex === '#3B82F6' || x.estado_clinico === 'REALIZADO_EN_CLINICA'
      );
      if (blueH) return '#3B82F6';

      // Prioridad 2: Existente previo (Verde)
      const greenH = matchingHallazgos.find(
        (x) => x.color_hex === '#10B981' || x.estado_clinico === 'EXISTENTE_PREVIO'
      );
      if (greenH) return '#10B981';

      // Prioridad 3: Requerido / Patología (Rojo)
      const redH = matchingHallazgos.find(
        (x) => x.color_hex === '#EF4444' || x.estado_clinico === 'REQUERIDO_PATOLOGIA'
      );
      if (redH) return '#EF4444';

      return matchingHallazgos[matchingHallazgos.length - 1].color_hex || '#EF4444';
    }

    // 2. Hallazgo de pieza GENERAL
    const genH = hallazgos.filter((x) => x.superficie === 'GENERAL');
    if (genH.length > 0 && surfaceName !== 'RAIZ') {
      const blueGen = genH.find((x) => x.color_hex === '#3B82F6' || x.estado_clinico === 'REALIZADO_EN_CLINICA');
      if (blueGen) return '#3B82F6';
      const greenGen = genH.find((x) => x.color_hex === '#10B981' || x.estado_clinico === 'EXISTENTE_PREVIO');
      if (greenGen) return '#10B981';
      return genH[genH.length - 1].color_hex || '#EF4444';
    }

    // Sin hallazgo / Diente sano (adaptado a modo claro y oscuro)
    if (surfaceName === 'RAIZ') {
      return isDark ? '#334155' : '#CBD5E1';
    }
    return isDark ? '#1E293B' : '#F1F5F9';
  };

  // Listado consolidado de todos los hallazgos de Diagnóstico y Evaluación Inicial (Ingreso del Paciente)
  const hallazgosIniciales = useMemo(() => {
    if (!odontograma?.piezas) return [];
    const lista = [];
    odontograma.piezas.forEach((pieza) => {
      const fdi = pieza.numero_fdi;
      const esInexistente = pieza.estado_general === 'EXTRAIDO';

      (pieza.hallazgos || []).forEach((h) => {
        const esVerde = h.color_hex === '#10B981' || h.estado_clinico === 'EXISTENTE_PREVIO';
        const esGris = h.color_hex === '#64748B' || (h.superficie === 'GENERAL' && esInexistente);

        if (esVerde || esGris) {
          lista.push({
            id: h.id,
            pieza_id: pieza.id,
            pieza_fdi: fdi,
            nombre_diente: getToothName(fdi),
            superficie: h.superficie || 'GENERAL',
            condicion: h.condicion || (esGris ? 'EXTRAIDO' : 'SANO'),
            estado_clinico: h.estado_clinico,
            color_hex: h.color_hex,
            es_inexistente: esGris,
            detalle: h.detalle || (esGris ? 'Pieza ausente / extraída al ingreso' : 'Evaluación clínica inicial'),
            created_at: h.created_at || odontograma.fecha_registro,
          });
        }
      });
    });

    return lista.sort((a, b) => a.pieza_fdi - b.pieza_fdi);
  }, [odontograma]);

  // Eliminar un hallazgo de diagnóstico inicial
  const handleEliminarHallazgoInicial = async (item) => {
    if (!item?.id) return;
    try {
      await api.deleteHallazgo(item.id);
      if (item.es_inexistente && item.pieza_id) {
        await api.updatePieza(item.pieza_id, { estado_general: 'PRESENTE' });
      }
      setSuccess(`✓ Registro de ingreso de la pieza #${item.pieza_fdi} eliminado`);
      setTimeout(() => setSuccess(''), 2500);
      const updated = await api.getOdontograma(odontograma.id);
      setOdontograma(updated);
      const map = {};
      updated.piezas?.forEach((p) => {
        map[p.numero_fdi] = p;
      });
      setPiezasMap(map);
    } catch (err) {
      setError(err.message || 'Error al eliminar registro de diagnóstico inicial');
    }
  };

  // Pintar cara con idempotencia silenciosa
  const handlePintarCara = async (
    superficieTarget = null,
    overrideEstado = null,
    overrideCondicion = null,
    overrideDetalle = null
  ) => {
    if (!odontograma || !selectedPiezaFdi) return;
    const cara = superficieTarget || superficieSeleccionada;
    const estado = overrideEstado || estadoClinicoActivo;
    const estadoObj = ESTADOS_CLINICOS.find((e) => e.id === estado);
    const colorHex = estadoObj ? estadoObj.colorHex : '#EF4444';

    // Si es Pieza Inexistente, marcar toda la pieza
    if (estado === 'PIEZA_INEXISTENTE') {
      await handleMarcarPiezaInexistente(selectedPiezaFdi);
      return;
    }

    let condicionFinal = 'SANO';
    if (estado === 'EXISTENTE_PREVIO') {
      condicionFinal = overrideCondicion || condicionInicial || (cara === 'RAIZ' ? 'ENDODONCIA' : 'OBTURACION_RESINA');
    } else {
      condicionFinal = overrideCondicion || (cara === 'RAIZ' ? 'ENDODONCIA' : 'CARIES');
    }

    const detalleFinal =
      overrideDetalle ||
      detalleInicial ||
      observacionHallazgo ||
      (estado === 'EXISTENTE_PREVIO'
        ? `Ingreso: ${CONDICIONES_LABEL_MAP[condicionFinal] || condicionFinal}`
        : `Cara ${cara} (${estadoObj?.label})`);

    const piezaData = piezasMap[selectedPiezaFdi];
    const existingH = piezaData?.hallazgos?.find((x) => x.superficie === cara);
    if (
      existingH &&
      existingH.color_hex === colorHex &&
      existingH.condicion === condicionFinal &&
      existingH.detalle === detalleFinal
    ) {
      return;
    }

    try {
      await api.createHallazgo({
        odontograma_id: odontograma.id,
        pieza_fdi: selectedPiezaFdi,
        superficie: cara,
        condicion: condicionFinal,
        color_hex: colorHex,
        estado_clinico: estado,
        detalle: detalleFinal,
      });

      const updated = await api.getOdontograma(odontograma.id);
      setOdontograma(updated);
      const map = {};
      updated.piezas?.forEach((p) => {
        map[p.numero_fdi] = p;
      });
      setPiezasMap(map);

      // Sincronizar estado del ítem del plan si existe en esta pieza/cara
      if (estado === 'REALIZADO_EN_CLINICA') {
        const matchingDraft = draftItems.find(
          (it) => it.pieza_fdi === selectedPiezaFdi && (it.superficie === cara || it.superficie === 'GENERAL')
        );
        if (matchingDraft?.id) {
          try {
            await api.updateItemPlan(matchingDraft.id, { estado: 'COMPLETADO' });
            setDraftItems((prev) =>
              prev.map((it) => (it.id === matchingDraft.id ? { ...it, estado: 'COMPLETADO' } : it))
            );
          } catch (_) {}
        }
      } else if (estado === 'REQUERIDO_PATOLOGIA') {
        const matchingDraft = draftItems.find(
          (it) => it.pieza_fdi === selectedPiezaFdi && (it.superficie === cara || it.superficie === 'GENERAL')
        );
        if (matchingDraft?.id) {
          try {
            await api.updateItemPlan(matchingDraft.id, { estado: 'PENDIENTE' });
            setDraftItems((prev) =>
              prev.map((it) => (it.id === matchingDraft.id ? { ...it, estado: 'PENDIENTE' } : it))
            );
          } catch (_) {}
        }
      }

      setSuccess(`✓ Registrado en #${selectedPiezaFdi} (${cara}): ${CONDICIONES_LABEL_MAP[condicionFinal] || condicionFinal}`);
      setTimeout(() => setSuccess(''), 2500);
    } catch (err) {
      setError(err.message || 'Error al registrar hallazgo');
    }
  };

  // Marcar Pieza Inexistente (Gris)
  const handleMarcarPiezaInexistente = async (fdi = null) => {
    const targetFdi = fdi || selectedPiezaFdi;
    if (!odontograma || !targetFdi) return;

    const piezaData = piezasMap[targetFdi];
    const yaInexistente = piezaData?.estado_general === 'EXTRAIDO' || piezaData?.hallazgos?.some((h) => h.color_hex === '#64748B' && h.superficie === 'GENERAL');
    if (yaInexistente) return; // Silencioso

    try {
      await api.createHallazgo({
        odontograma_id: odontograma.id,
        pieza_fdi: targetFdi,
        superficie: 'GENERAL',
        condicion: 'SANO',
        color_hex: '#64748B',
        estado_clinico: 'EXISTENTE_PREVIO',
        detalle: 'Pieza inexistente / ausente',
      });

      if (piezaData?.id) {
        await api.updatePieza(piezaData.id, { estado_general: 'EXTRAIDO' });
      }

      const updated = await api.getOdontograma(odontograma.id);
      setOdontograma(updated);
      const map = {};
      updated.piezas?.forEach((p) => {
        map[p.numero_fdi] = p;
      });
      setPiezasMap(map);

      setSuccess(`Pieza #${targetFdi} marcada como Inexistente`);
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError(err.message || 'Error al marcar pieza');
    }
  };

  // Limpiar solo la cara seleccionada
  const handleLimpiarCara = async (superficieTarget = null) => {
    if (!odontograma || !selectedPiezaFdi) return;
    const cara = superficieTarget || superficieSeleccionada;
    const piezaData = piezasMap[selectedPiezaFdi];
    const h = piezaData?.hallazgos?.find((x) => x.superficie === cara);

    if (!h) {
      return; // Silencioso si ya está limpio
    }

    try {
      await api.deleteHallazgo(h.id);
      const updated = await api.getOdontograma(odontograma.id);
      setOdontograma(updated);
      const map = {};
      updated.piezas?.forEach((p) => {
        map[p.numero_fdi] = p;
      });
      setPiezasMap(map);

      setSuccess(`Cara ${cara} de la pieza #${selectedPiezaFdi} limpiada`);
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError(err.message || 'Error al limpiar cara');
    }
  };

  // Limpiar el DIENTE COMPLETO (todas las caras y restaurar a presente/sano)
  const handleLimpiarDienteCompleto = async () => {
    if (!odontograma || !selectedPiezaFdi) return;
    const piezaData = piezasMap[selectedPiezaFdi];
    const hallazgos = piezaData?.hallazgos || [];

    if (hallazgos.length === 0 && piezaData?.estado_general === 'PRESENTE') {
      return; // Ya está limpio
    }

    try {
      for (const h of hallazgos) {
        await api.deleteHallazgo(h.id);
      }
      if (piezaData?.id && piezaData.estado_general !== 'PRESENTE') {
        await api.updatePieza(piezaData.id, { estado_general: 'PRESENTE' });
      }

      const updated = await api.getOdontograma(odontograma.id);
      setOdontograma(updated);
      const map = {};
      updated.piezas?.forEach((p) => {
        map[p.numero_fdi] = p;
      });
      setPiezasMap(map);

      setSuccess(`Diente #${selectedPiezaFdi} restaurado completamente a sano`);
      setTimeout(() => setSuccess(''), 2500);
    } catch (err) {
      setError(err.message || 'Error al limpiar diente');
    }
  };

  // Asignar Tratamiento a la Cara seleccionada
  const handleAsignarTratamientoACara = async (itemCat) => {
    if (!selectedPacienteId || !selectedPiezaFdi) return;
    setActionLoading(true);
    setError('');

    const precioBase = Number(itemCat.costo_base ?? itemCat.precio_base ?? 0);
    const caraActual = superficieSeleccionada;
    const fdiActual = selectedPiezaFdi;

    try {
      // 1. Asegurar o crear Plan de Tratamiento
      let targetPlan = activePlan;
      if (!targetPlan) {
        targetPlan = await api.createPlan({
          paciente_id: selectedPacienteId,
          doctor_id: selectedDoctorId || user?.doctor_id,
          titulo: 'Plan de Tratamiento Integral y Presupuesto',
          costo_total: precioBase,
        });
        setActivePlan(targetPlan);
      }

      // 2. Registrar el ítem en el Plan
      const resItem = await api.createItemPlan({
        plan_id: targetPlan.id,
        tratamiento_id: itemCat.id,
        pieza_fdi: fdiActual,
        superficie: caraActual,
        precio_unitario: precioBase,
        descuento: 0,
        costo_acordado: precioBase,
        observaciones: `Superficie: ${caraActual}`,
        estado: 'PENDIENTE',
        es_proxima_sesion: false,
      });

      // 3. Pintar automáticamente la cara en el Odontograma como 'Plan de tratamiento' (Rojo)
      if (odontograma) {
        await api.createHallazgo({
          odontograma_id: odontograma.id,
          pieza_fdi: fdiActual,
          superficie: caraActual,
          condicion: caraActual === 'RAIZ' ? 'ENDODONCIA' : 'CARIES',
          color_hex: '#EF4444',
          estado_clinico: 'REQUERIDO_PATOLOGIA',
          detalle: `Tratamiento asignado: ${itemCat.nombre}`,
        });

        const updated = await api.getOdontograma(odontograma.id);
        setOdontograma(updated);
        const map = {};
        updated.piezas?.forEach((p) => {
          map[p.numero_fdi] = p;
        });
        setPiezasMap(map);
      }

      // 4. Actualizar lista de ítems del presupuesto
      const newItemEntry = {
        id: resItem.id,
        plan_id: targetPlan.id,
        pieza_fdi: fdiActual,
        superficie: caraActual,
        tratamiento_id: itemCat.id,
        nombre_tratamiento: itemCat.nombre,
        categoria: itemCat.categoria,
        precio_unitario: precioBase,
        descuento: 0,
        costo_acordado: precioBase,
        es_proxima_sesion: false,
        estado: 'PENDIENTE',
      };

      setDraftItems((prev) => [...prev, newItemEntry]);

      // Recargar planes del paciente
      const pl = await api.getPlanes(selectedPacienteId);
      setPlanes(Array.isArray(pl) ? pl : []);
      const upPlan = (pl || []).find((p) => p.id === targetPlan.id) || targetPlan;
      setActivePlan(upPlan);

      setSuccess(`✓ Asignado: "${itemCat.nombre}" a #${fdiActual} (${caraActual})`);
      setTimeout(() => setSuccess(''), 2500);
    } catch (err) {
      setError(err.message || 'Error al asignar tratamiento a la cara dental');
    } finally {
      setActionLoading(false);
    }
  };

  // Cálculo del presupuesto en vivo
  const totalesCalculados = useMemo(() => {
    let subtotal = 0;
    let totalDescuentos = 0;
    let totalPresupuesto = 0;

    draftItems.forEach((it) => {
      const pUnit = Number(it.precio_unitario || 0);
      const desc = Number(it.descuento || 0);
      const neto = Math.max(0, pUnit - desc);

      subtotal += pUnit;
      totalDescuentos += desc;
      totalPresupuesto += neto;
    });

    return {
      subtotal,
      totalDescuentos,
      totalPresupuesto,
      cantidad: draftItems.length,
    };
  }, [draftItems]);

  // Actualizar descuento de un ítem en borrador
  const handleUpdateItemDescuento = (idx, valorDescuento) => {
    const val = Math.max(0, parseFloat(valorDescuento) || 0);
    setDraftItems((prev) => {
      const copy = [...prev];
      const target = copy[idx];
      target.descuento = val;
      target.costo_acordado = Math.max(0, Number(target.precio_unitario || 0) - val);
      return copy;
    });
  };

  // Marcar / Desmarcar Alta Médica (Procedimiento Realizado - Azul en Odontograma)
  const handleToggleAltaMedica = async (item, idx) => {
    const yaRealizado = item.estado === 'COMPLETADO';
    const nuevoEstado = yaRealizado ? 'PENDIENTE' : 'COMPLETADO';

    setDraftItems((prev) => {
      const copy = [...prev];
      copy[idx].estado = nuevoEstado;
      copy[idx].es_proxima_sesion = false;
      return copy;
    });

    if (item.id) {
      try {
        await api.updateItemPlan(item.id, {
          estado: nuevoEstado,
          es_proxima_sesion: false,
        });
      } catch (e) {
        console.error('Error al actualizar estado del ítem en plan:', e);
      }
    }

    // Actualizar color en el odontograma: Azul (#3B82F6) si es Alta Médica, Rojo (#EF4444) si regresa a Pendiente
    if (odontograma && item.pieza_fdi) {
      let cara = item.superficie;
      if (!cara || cara === 'GENERAL') {
        if (item.observaciones?.includes('Superficie: ')) {
          cara = item.observaciones.split('Superficie: ')[1].split(' |')[0].trim();
        }
      }
      if (!cara) cara = 'CORONA';

      const colorHex = nuevoEstado === 'COMPLETADO' ? '#3B82F6' : '#EF4444';
      const estadoClinico = nuevoEstado === 'COMPLETADO' ? 'REALIZADO_EN_CLINICA' : 'REQUERIDO_PATOLOGIA';
      const detalle = nuevoEstado === 'COMPLETADO'
        ? `Alta médica: ${item.nombre_tratamiento || 'Tratamiento Realizado'}`
        : `Requerido: ${item.nombre_tratamiento || 'Plan de tratamiento'}`;

      try {
        await api.createHallazgo({
          odontograma_id: odontograma.id,
          pieza_fdi: item.pieza_fdi,
          superficie: cara,
          condicion: 'OBTURACION_RESINA',
          color_hex: colorHex,
          estado_clinico: estadoClinico,
          detalle: detalle,
        });

        const updated = await api.getOdontograma(odontograma.id);
        setOdontograma(updated);
        const map = {};
        updated.piezas?.forEach((p) => {
          map[p.numero_fdi] = p;
        });
        setPiezasMap(map);
      } catch (err) {
        console.error('Error sincronizando odontograma con alta médica:', err);
      }
    }

    setSuccess(
      nuevoEstado === 'COMPLETADO'
        ? `✓ Pieza #${item.pieza_fdi || 'Gral'} dada de Alta Médica (marcada en azul en odontograma)`
        : `Pieza #${item.pieza_fdi || 'Gral'} regresada a estado pendiente (marcada en rojo)`
    );
    setTimeout(() => setSuccess(''), 2500);
  };

  // Eliminar ítem del plan
  const handleEliminarItemPlan = async (item, idx) => {
    try {
      if (item.id) {
        await api.deleteItemPlan(item.id);
      }
      setDraftItems((prev) => prev.filter((_, i) => i !== idx));

      const pl = await api.getPlanes(selectedPacienteId);
      setPlanes(Array.isArray(pl) ? pl : []);
      if (activePlan) {
        const upPlan = (pl || []).find((p) => p.id === activePlan.id);
        if (upPlan) setActivePlan(upPlan);
      }
      setSuccess('Procedimiento retirado del presupuesto');
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError(err.message || 'Error al eliminar ítem');
    }
  };

  // Guardar Plan de Tratamiento y Presupuesto
  const handleGuardarPlanTratamiento = async (forzarEstado = null) => {
    if (!activePlan) return;
    setActionLoading(true);
    setError('');
    try {
      for (const it of draftItems) {
        if (it.id) {
          await api.updateItemPlan(it.id, {
            descuento: it.descuento,
            costo_acordado: it.costo_acordado,
            es_proxima_sesion: it.es_proxima_sesion,
            estado: it.estado || (it.es_proxima_sesion ? 'PROXIMA_SESION' : 'PENDIENTE'),
          });
        }
      }

      const estadoFinal = forzarEstado || activePlan.estado || 'APROBADO';

      await api.updatePlan(activePlan.id, {
        costo_total: totalesCalculados.totalPresupuesto,
        estado: estadoFinal,
      });

      const pl = await api.getPlanes(selectedPacienteId);
      setPlanes(Array.isArray(pl) ? pl : []);
      const up = (pl || []).find((p) => p.id === activePlan.id);
      if (up) setActivePlan(up);

      setSuccess(`¡Plan de Tratamiento guardado (${estadoFinal}) exitosamente!`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Error al guardar el plan de tratamiento');
    } finally {
      setActionLoading(false);
    }
  };

  // Filtrado de tratamientos en catálogo
  const catalogoFiltrado = useMemo(() => {
    return catalogo.filter((c) => {
      const matchSearch =
        c.nombre.toLowerCase().includes(catalogoSearch.toLowerCase()) ||
        c.codigo.toLowerCase().includes(catalogoSearch.toLowerCase());
      const matchCat = catalogoCategoria === 'TODAS' || c.categoria === catalogoCategoria;
      return matchSearch && matchCat;
    });
  }, [catalogo, catalogoSearch, catalogoCategoria]);

  const categoriasCatalogo = useMemo(() => {
    const setCats = new Set(catalogo.map((c) => c.categoria).filter(Boolean));
    return ['TODAS', ...Array.from(setCats)];
  }, [catalogo]);

  // Renderizador SVG de Diente con Raíces y Orientación Mesial hacia el Centro
  const renderTooth = (fdi) => {
    const isSelected = selectedPiezaFdi === fdi;
    const { isUpper, rootCount } = getToothAnatomy(fdi);
    const piezaData = piezasMap[fdi];
    const hallazgos = piezaData?.hallazgos || [];
    const isInexistente = piezaData?.estado_general === 'EXTRAIDO' || hallazgos.some((x) => x.color_hex === '#64748B' && x.superficie === 'GENERAL');

    const rootColor = getSurfaceColor(fdi, 'RAIZ');
    const isRootSelected = isSelected && superficieSeleccionada === 'RAIZ';

    // Regla Anatómica: Las caras mesiales SIEMPRE van hacia los dientes centrales (línea media)
    // isRightSideOfArch = cuadrantes 2 y 3 (lado derecho en pantalla) -> mesial está a la IZQUIERDA
    // !isRightSideOfArch = cuadrantes 1 y 4 (lado izquierdo en pantalla) -> mesial está a la DERECHA
    const rightSide = isRightSideOfArch(fdi);
    const leftSurfaceName = rightSide ? 'MESIAL' : 'DISTAL';
    const rightSurfaceName = rightSide ? 'DISTAL' : 'MESIAL';

    const strokeDefault = isDark ? '#475569' : '#94A3B8';
    const strokeSelected = '#0284c7';

    return (
      <div
        key={fdi}
        onClick={() => handleSelectTooth(fdi)}
        className={`min-w-0 flex flex-col items-center p-1 rounded-2xl cursor-pointer transition select-none ${
          isSelected
            ? 'bg-dental-50 dark:bg-primary-600/25 border-2 border-dental-500 dark:border-primary-500 shadow-md'
            : 'bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-700/60 hover:border-slate-400 dark:hover:border-slate-500'
        } ${isInexistente ? 'opacity-70 saturate-50' : ''}`}
        title={`#${fdi} - ${getToothName(fdi)}${isInexistente ? ' (Inexistente)' : ''}`}
      >
        {/* Número FDI de la Pieza */}
        <span
          className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded-md mb-1 ${
            isSelected
              ? 'bg-dental-600 dark:bg-primary-600 text-white shadow'
              : 'text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800'
          }`}
        >
          {fdi}
        </span>

        {/* SVG Anatómico con Raíces (viewBox: 0 0 70 110) */}
        <svg viewBox="0 0 70 110" className="w-full h-auto max-h-44 drop-shadow-sm">
          {/* ==================== DIENTE SUPERIOR (Raíces hacia ARRIBA) ==================== */}
          {isUpper ? (
            <g>
              {/* Raíces Superiores (y: 4 a 48) */}
              <g
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelectTooth(fdi);
                  setSuperficieSeleccionada('RAIZ');
                }}
                className="cursor-pointer"
              >
                {rootCount === 1 && (
                  <g>
                    <polygon
                      points="23,48 31,6 39,6 47,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <line x1="35" y1="12" x2="35" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  </g>
                )}

                {rootCount === 2 && (
                  <g>
                    <polygon
                      points="12,48 18,8 26,8 30,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <polygon
                      points="40,48 44,8 52,8 58,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <line x1="22" y1="14" x2="22" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="48" y1="14" x2="48" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  </g>
                )}

                {rootCount === 3 && (
                  <g>
                    <polygon
                      points="8,48 12,8 20,8 24,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <polygon
                      points="27,48 31,4 39,4 43,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <polygon
                      points="46,48 50,8 58,8 62,48"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <line x1="16" y1="14" x2="16" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="35" y1="10" x2="35" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="54" y1="14" x2="54" y2="44" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  </g>
                )}
              </g>

              {/* Corona Superior (y: 48 a 102) */}
              <g>
                {/* Vestibular (Arriba de la corona) */}
                <polygon
                  points="8,48 62,48 48,62 22,62"
                  fill={getSurfaceColor(fdi, 'VESTIBULAR')}
                  stroke={isSelected && superficieSeleccionada === 'VESTIBULAR' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'VESTIBULAR' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('VESTIBULAR');
                  }}
                >
                  <title>Vestibular</title>
                </polygon>

                {/* Palatino (Abajo de la corona) */}
                <polygon
                  points="22,88 48,88 62,102 8,102"
                  fill={getSurfaceColor(fdi, 'LINGUAL_PALATINO')}
                  stroke={isSelected && superficieSeleccionada === 'LINGUAL_PALATINO' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'LINGUAL_PALATINO' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('LINGUAL_PALATINO');
                  }}
                >
                  <title>Palatino</title>
                </polygon>

                {/* Cara Izquierda del Polígono */}
                <polygon
                  points="8,48 22,62 22,88 8,102"
                  fill={getSurfaceColor(fdi, leftSurfaceName)}
                  stroke={isSelected && superficieSeleccionada === leftSurfaceName ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === leftSurfaceName ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada(leftSurfaceName);
                  }}
                >
                  <title>{leftSurfaceName === 'MESIAL' ? 'Mesial (hacia centro)' : 'Distal'}</title>
                </polygon>

                {/* Cara Derecha del Polígono */}
                <polygon
                  points="62,48 48,62 48,88 62,102"
                  fill={getSurfaceColor(fdi, rightSurfaceName)}
                  stroke={isSelected && superficieSeleccionada === rightSurfaceName ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === rightSurfaceName ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada(rightSurfaceName);
                  }}
                >
                  <title>{rightSurfaceName === 'MESIAL' ? 'Mesial (hacia centro)' : 'Distal'}</title>
                </polygon>

                {/* Oclusal / Incisal (Centro) */}
                <polygon
                  points="22,62 48,62 48,88 22,88"
                  fill={getSurfaceColor(fdi, 'OCLUSAL_INCISAL')}
                  stroke={isSelected && superficieSeleccionada === 'OCLUSAL_INCISAL' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'OCLUSAL_INCISAL' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('OCLUSAL_INCISAL');
                  }}
                >
                  <title>Oclusal / Incisal</title>
                </polygon>
              </g>
            </g>
          ) : (
            /* ==================== DIENTE INFERIOR (Raíces hacia ABAJO) ==================== */
            <g>
              {/* Corona Inferior (y: 8 a 62) */}
              <g>
                {/* Vestibular (Arriba de la corona) */}
                <polygon
                  points="8,8 62,8 48,22 22,22"
                  fill={getSurfaceColor(fdi, 'VESTIBULAR')}
                  stroke={isSelected && superficieSeleccionada === 'VESTIBULAR' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'VESTIBULAR' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('VESTIBULAR');
                  }}
                >
                  <title>Vestibular</title>
                </polygon>

                {/* Lingual (Abajo de la corona) */}
                <polygon
                  points="22,48 48,48 62,62 8,62"
                  fill={getSurfaceColor(fdi, 'LINGUAL_PALATINO')}
                  stroke={isSelected && superficieSeleccionada === 'LINGUAL_PALATINO' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'LINGUAL_PALATINO' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('LINGUAL_PALATINO');
                  }}
                >
                  <title>Lingual</title>
                </polygon>

                {/* Cara Izquierda del Polígono */}
                <polygon
                  points="8,8 22,22 22,48 8,62"
                  fill={getSurfaceColor(fdi, leftSurfaceName)}
                  stroke={isSelected && superficieSeleccionada === leftSurfaceName ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === leftSurfaceName ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada(leftSurfaceName);
                  }}
                >
                  <title>{leftSurfaceName === 'MESIAL' ? 'Mesial (hacia centro)' : 'Distal'}</title>
                </polygon>

                {/* Cara Derecha del Polígono */}
                <polygon
                  points="62,8 48,22 48,48 62,62"
                  fill={getSurfaceColor(fdi, rightSurfaceName)}
                  stroke={isSelected && superficieSeleccionada === rightSurfaceName ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === rightSurfaceName ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada(rightSurfaceName);
                  }}
                >
                  <title>{rightSurfaceName === 'MESIAL' ? 'Mesial (hacia centro)' : 'Distal'}</title>
                </polygon>

                {/* Oclusal / Incisal (Centro) */}
                <polygon
                  points="22,22 48,22 48,48 22,48"
                  fill={getSurfaceColor(fdi, 'OCLUSAL_INCISAL')}
                  stroke={isSelected && superficieSeleccionada === 'OCLUSAL_INCISAL' ? strokeSelected : strokeDefault}
                  strokeWidth={isSelected && superficieSeleccionada === 'OCLUSAL_INCISAL' ? '2.5' : '1.5'}
                  className="hover:opacity-85 transition cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTooth(fdi);
                    setSuperficieSeleccionada('OCLUSAL_INCISAL');
                  }}
                >
                  <title>Oclusal / Incisal</title>
                </polygon>
              </g>

              {/* Raíces Inferiores (y: 62 a 106) */}
              <g
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelectTooth(fdi);
                  setSuperficieSeleccionada('RAIZ');
                }}
                className="cursor-pointer"
              >
                {rootCount === 1 && (
                  <g>
                    <polygon
                      points="23,62 31,104 39,104 47,62"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <line x1="35" y1="66" x2="35" y2="98" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  </g>
                )}

                {rootCount === 2 && (
                  <g>
                    <polygon
                      points="10,62 16,104 25,104 30,62"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <polygon
                      points="40,62 45,104 54,104 60,62"
                      fill={rootColor}
                      stroke={isRootSelected ? strokeSelected : strokeDefault}
                      strokeWidth={isRootSelected ? '2.5' : '1.5'}
                      className="transition hover:opacity-85"
                    />
                    <line x1="20" y1="66" x2="20" y2="98" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="50" y1="66" x2="50" y2="98" stroke="#94A3B8" strokeWidth="1" strokeDasharray="2,2" />
                  </g>
                )}
              </g>
            </g>
          )}

          {/* Gráfico de Pieza Inexistente (Cruz de ausencia) */}
          {isInexistente && (
            <g stroke="#EF4444" strokeWidth="3" strokeLinecap="round" opacity="0.85">
              <line x1="8" y1="8" x2="62" y2="102" />
              <line x1="62" y1="8" x2="8" y2="102" />
            </g>
          )}
        </svg>

        {/* Indicador de hallazgos activos o estado */}
        <div className="h-3 flex items-center justify-center mt-1">
          {isInexistente ? (
            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-tight">Ausente</span>
          ) : hallazgos.length > 0 ? (
            <span
              className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"
              title={`${hallazgos.length} hallazgo(s) registrados`}
            />
          ) : null}
        </div>
      </div>
    );
  };

  // Cada mitad reparte el ancho entre sus dientes, con la línea media entre ambas
  const renderArcada = (izquierda, derecha, etiquetaMedial) => (
    <div
      className="grid items-stretch gap-1"
      style={{ gridTemplateColumns: `repeat(${izquierda.length}, minmax(0, 1fr)) auto repeat(${derecha.length}, minmax(0, 1fr))` }}
    >
      {izquierda.map((fdi) => renderTooth(fdi))}
      <div className="relative w-0.5 mx-1.5 sm:mx-3 bg-dental-500/40 dark:bg-primary-500/40">
        {etiquetaMedial && (
          <span className={`absolute left-1/2 -translate-x-1/2 ${etiquetaMedial === 'arriba' ? '-top-3' : '-bottom-3'} text-[9px] font-bold font-mono text-dental-600 dark:text-primary-400 bg-white dark:bg-slate-800 px-1 rounded`}>
            MEDIAL
          </span>
        )}
      </div>
      {derecha.map((fdi) => renderTooth(fdi))}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header Principal con Selectores de Paciente y Doctor */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-dental-600 dark:text-primary-400" />
            Odontograma Dental Clínico FDI
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs sm:text-sm">
            Mapeo gráfico por caras anatómicas, raíces dentales, diagnóstico y presupuestos en vivo
          </p>
        </div>

        {/* Selectores de Paciente y Doctor */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Selector de Paciente */}
          <PacienteSearchInput
            pacientes={pacientes}
            selectedPacienteId={selectedPacienteId}
            onSelectPaciente={(id) => setSelectedPacienteId(id)}
            placeholder="Buscar paciente por nombre o CI..."
            className="w-80 max-w-full"
          />

          {/* Selector de Doctor Asignado */}
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 px-3 py-1.5 rounded-xl shadow-sm min-w-0 max-w-full">
            <Shield className={`w-4 h-4 ${user?.puedeElegirDoctor ? 'text-emerald-500' : 'text-slate-400'}`} />
            <div className="flex flex-col min-w-0">
              <span className="text-[10px] text-slate-500 dark:text-slate-400 leading-none">
                {user?.puedeElegirDoctor ? 'Doctor Tratante (Elegir)' : 'Doctor Tratante'}
              </span>
              {user?.puedeElegirDoctor ? (
                <select
                  value={selectedDoctorId}
                  onChange={(e) => handleDoctorChange(e.target.value)}
                  className="min-w-0 max-w-full bg-transparent text-slate-800 dark:text-white text-xs font-semibold focus:outline-none cursor-pointer"
                >
                  {doctores.map((doc) => (
                    <option key={doc.id} value={doc.id} className="bg-white dark:bg-slate-900 text-slate-800 dark:text-white">
                      Dr. {doc.usuario?.nombre} {doc.usuario?.apellido} ({doc.especialidad})
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-xs font-semibold text-slate-800 dark:text-white">
                  {doctores.find((d) => d.id === selectedDoctorId)
                    ? `Dr. ${doctores.find((d) => d.id === selectedDoctorId).usuario?.nombre} ${
                        doctores.find((d) => d.id === selectedDoctorId).usuario?.apellido
                      }`
                    : 'Dr. Asignado'}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Alertas */}
      {success && (
        <div className="p-3.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center gap-2 shadow-sm">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}
      {error && (
        <div className="p-3.5 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 rounded-xl text-rose-700 dark:text-rose-400 text-xs flex items-center gap-2 shadow-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Guía Visual: Aclaración de lados Izquierdo y Derecho (Perspectiva Odontológica) */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 flex flex-col md:flex-row items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
          <Info className="w-4 h-4 text-dental-600 dark:text-primary-400 shrink-0" />
          <span>
            <strong className="text-slate-900 dark:text-white">Vista Clínica Frontal:</strong> El lado izquierdo de la pantalla corresponde al <strong>Lado Derecho del Paciente</strong> (Cuadrantes 1 y 4), y el lado derecho de la pantalla al <strong>Lado Izquierdo del Paciente</strong> (Cuadrantes 2 y 3).
          </span>
        </div>
        <div className="text-[11px] px-2.5 py-1 rounded-lg bg-dental-50 dark:bg-primary-950/60 text-dental-700 dark:text-primary-300 font-semibold border border-dental-200 dark:border-primary-800 shrink-0">
          Caras Mesiales orientadas hacia la Línea Media Central
        </div>
      </div>

      {/* Odontograma Gráfico Principal */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-5 shadow-sm">
        {/* Controles de Dentición y Paleta de Estados */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-700/60">
          {/* Selector de Dentición */}
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-700/60">
            <button
              onClick={() => setDenticion('ADULTA')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                denticion === 'ADULTA'
                  ? 'bg-dental-600 dark:bg-primary-600 text-white shadow'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Dentición Adulta (32)
            </button>
            <button
              onClick={() => setDenticion('TEMPORAL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                denticion === 'TEMPORAL'
                  ? 'bg-dental-600 dark:bg-primary-600 text-white shadow'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Dentición Temporal / Niños (20)
            </button>
          </div>

          {/* Paleta de los 4 Estados Clínicos */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Estado Activo:</span>
            {ESTADOS_CLINICOS.map((est) => {
              const isActive = estadoClinicoActivo === est.id;
              return (
                <button
                  key={est.id}
                  onClick={() => setEstadoClinicoActivo(est.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition flex items-center gap-2 ${
                    isActive
                      ? `${est.badgeClass} ring-2 ring-dental-500 dark:ring-white/50 scale-105 shadow-sm`
                      : 'bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <span className={`w-2.5 h-2.5 rounded-full ${est.dotClass}`} />
                  <span>{est.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tablero Gráfico de Dientes */}
        {denticion === 'ADULTA' ? (
          <div className="overflow-x-auto pb-2">
          <div className="space-y-6 min-w-[820px] pt-1">
            {/* Indicadores de Cuadrante Superior */}
            <div className="grid grid-cols-2 text-center text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-1 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center justify-center gap-1.5 text-dental-600 dark:text-primary-400">
                <span>DERECHA DEL PACIENTE (Cuadrante 1: 18 - 11)</span>
              </div>
              <div className="flex items-center justify-center gap-1.5 text-teal-600 dark:text-teal-400">
                <span>IZQUIERDA DEL PACIENTE (Cuadrante 2: 21 - 28)</span>
              </div>
            </div>

            {/* Arcada Superior (Maxilar) - Raíces hacia arriba */}
            <div>
              <div className="text-[11px] font-bold text-slate-400 text-center uppercase tracking-widest mb-4">
                Arcada Superior (Maxilar)
              </div>
              {renderArcada(CUADRANTE_1, CUADRANTE_2, 'arriba')}
            </div>

            <div className="border-t border-slate-200 dark:border-slate-700/60 my-2" />

            {/* Arcada Inferior (Mandíbula) - Raíces hacia abajo */}
            <div>
              {renderArcada(CUADRANTE_4, CUADRANTE_3, 'abajo')}
              <div className="text-[11px] font-bold text-slate-400 text-center uppercase tracking-widest mt-4">
                Arcada Inferior (Mandíbula)
              </div>
            </div>

            {/* Indicadores de Cuadrante Inferior */}
            <div className="grid grid-cols-2 text-center text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800">
              <div className="flex items-center justify-center gap-1.5 text-dental-600 dark:text-primary-400">
                <span>DERECHA DEL PACIENTE (Cuadrante 4: 48 - 41)</span>
              </div>
              <div className="flex items-center justify-center gap-1.5 text-teal-600 dark:text-teal-400">
                <span>IZQUIERDA DEL PACIENTE (Cuadrante 3: 31 - 38)</span>
              </div>
            </div>
          </div>
          </div>
        ) : (
          /* Dentición Temporal */
          <div className="overflow-x-auto pb-2">
          <div className="space-y-6 min-w-[520px] pt-1">
            <div className="grid grid-cols-2 text-center text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-1 border-b border-slate-200 dark:border-slate-800">
              <span>DERECHA DEL PACIENTE (Temporal Sup. 55-51)</span>
              <span>IZQUIERDA DEL PACIENTE (Temporal Sup. 61-65)</span>
            </div>

            {renderArcada(TEMP_1, TEMP_2)}
            <div className="border-t border-slate-200 dark:border-slate-700/60 my-2" />
            {renderArcada(TEMP_4, TEMP_3)}

            <div className="grid grid-cols-2 text-center text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800">
              <span>DERECHA DEL PACIENTE (Temporal Inf. 85-81)</span>
              <span>IZQUIERDA DEL PACIENTE (Temporal Inf. 71-75)</span>
            </div>
          </div>
          </div>
        )}

        {/* Panel de Inspección de la Pieza Seleccionada */}
        {selectedPiezaFdi && (
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-800">
              {/* Información Anatómica */}
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-dental-50 dark:bg-primary-600/20 border border-dental-200 dark:border-primary-500/40 text-dental-700 dark:text-primary-400 rounded-xl font-mono text-xl font-bold flex items-center justify-center shadow-xs">
                  #{selectedPiezaFdi}
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>{getToothName(selectedPiezaFdi)}</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {piezasMap[selectedPiezaFdi]?.hallazgos?.length || 0} hallazgo(s) registrados ·{' '}
                    {isRightSideOfArch(selectedPiezaFdi) ? 'Lado Izquierdo del Paciente' : 'Lado Derecho del Paciente'}
                  </div>
                </div>
              </div>

              {/* Botones de Acción Rápida: Pintar Cara, Limpiar Cara, Limpiar Diente Completo */}
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => handlePintarCara()}
                  disabled={actionLoading}
                  className="px-3.5 py-1.5 bg-dental-600 hover:bg-dental-500 dark:bg-primary-600 dark:hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition shadow-xs flex items-center gap-1.5"
                >
                  <Brush className="w-3.5 h-3.5" />
                  <span>Marcar Cara Activa</span>
                </button>

                <button
                  onClick={() => handleMarcarPiezaInexistente()}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl border border-slate-300 dark:border-slate-700 transition flex items-center gap-1.5"
                  title="Marcar como inexistente / ausente"
                >
                  <Ban className="w-3.5 h-3.5 text-slate-500" />
                  <span>Marcar Inexistente</span>
                </button>

                <button
                  onClick={() => handleLimpiarCara()}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl border border-slate-300 dark:border-slate-700 transition flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                  <span>Limpiar Cara</span>
                </button>

                {/* Opción de Limpiar el Diente Completo */}
                <button
                  onClick={() => handleLimpiarDienteCompleto()}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 dark:bg-rose-500/10 dark:hover:bg-rose-500/20 text-rose-700 dark:text-rose-400 text-xs font-semibold rounded-xl border border-rose-200 dark:border-rose-500/30 transition flex items-center gap-1.5"
                  title="Eliminar todos los hallazgos de todas las caras de esta pieza"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Limpiar Diente Completo</span>
                </button>
              </div>
            </div>

            {/* Selector de Caras Dentales con Mesial / Distal aclarados */}
            <div>
              <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Seleccionar Cara Anatómica a Intervenir:
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                {SUPERFICIES_LIST.map((sup) => {
                  const isActive = superficieSeleccionada === sup.id;
                  const colorActual = getSurfaceColor(selectedPiezaFdi, sup.id);
                  const tieneColor = colorActual !== (isDark ? '#1E293B' : '#F1F5F9') && colorActual !== (isDark ? '#334155' : '#CBD5E1');

                  return (
                    <button
                      key={sup.id}
                      onClick={() => setSuperficieSeleccionada(sup.id)}
                      className={`p-2 rounded-xl text-left border transition flex flex-col justify-between ${
                        isActive
                          ? 'bg-dental-50 dark:bg-primary-600/30 border-dental-500 dark:border-primary-500 ring-2 ring-dental-500/40'
                          : 'bg-white dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">{sup.short}</span>
                        {tieneColor && (
                          <span
                            className="w-2.5 h-2.5 rounded-full border border-black/30"
                            style={{ backgroundColor: colorActual }}
                          />
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight line-clamp-1">
                        {sup.id === 'MESIAL' ? 'Hacia línea media' : sup.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Panel Condicional: Diagnóstico Inicial de Ingreso vs Catálogo de Tratamientos del Presupuesto */}
            {estadoClinicoActivo === 'EXISTENTE_PREVIO' ? (
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ClipboardList className="w-3.5 h-3.5" />
                      Registrar Condición de Ingreso en Cara [
                      {SUPERFICIES_LIST.find((s) => s.id === superficieSeleccionada)?.label || superficieSeleccionada}] de la Pieza #{selectedPiezaFdi}
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Selecciona la condición preexistente con la que llegó el paciente y haz clic en "Guardar Diagnóstico Inicial".
                    </p>
                  </div>

                  <button
                    onClick={() => handlePintarCara()}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl transition shadow-xs flex items-center gap-1.5 cursor-pointer shrink-0"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Guardar Diagnóstico Inicial</span>
                  </button>
                </div>

                {/* Selector de Condición de Ingreso */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Condición Preexistente / Diagnóstico de Ingreso:
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                    {CONDICIONES_INGRESO.map((cond) => {
                      const isSelected = condicionInicial === cond.id;
                      return (
                        <button
                          key={cond.id}
                          type="button"
                          onClick={() => setCondicionInicial(cond.id)}
                          className={`p-2 rounded-xl text-left border transition flex flex-col justify-between ${
                            isSelected
                              ? 'bg-emerald-50 dark:bg-emerald-500/20 border-emerald-500 dark:border-emerald-500 text-emerald-800 dark:text-emerald-300 ring-2 ring-emerald-500/30'
                              : 'bg-white dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600'
                          }`}
                        >
                          <span className="text-xs font-bold leading-tight">{cond.label}</span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">{cond.fullLabel}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Detalle u Observación Clínica opcional */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Detalle u Observación Clínica de la Condición:
                  </label>
                  <input
                    type="text"
                    placeholder="ej. Resina oclusal antigua en buen estado, borde mesial intacto..."
                    value={detalleInicial}
                    onChange={(e) => setDetalleInicial(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs placeholder-slate-400 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            ) : (
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                      Asignar Tratamiento a la Cara [
                      {SUPERFICIES_LIST.find((s) => s.id === superficieSeleccionada)?.label || superficieSeleccionada}] de la Pieza #{selectedPiezaFdi}
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Haz clic en "+ Asignar" para registrar el procedimiento directamente en la cara seleccionada y en el presupuesto.
                    </p>
                  </div>

                  {/* Filtro por Categoría */}
                  <div className="flex items-center gap-2">
                    <Filter className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                    <select
                      value={catalogoCategoria}
                      onChange={(e) => setCatalogoCategoria(e.target.value)}
                      className="px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg text-xs"
                    >
                      {categoriasCatalogo.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat === 'TODAS' ? 'Todas las Categorías' : cat}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Buscador de Tratamientos */}
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Buscar tratamiento por nombre o código (ej. Resina, Endodoncia, Corona, Limpieza, Extracción)..."
                    value={catalogoSearch}
                    onChange={(e) => setCatalogoSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs placeholder-slate-400 focus:outline-none focus:border-dental-500 dark:focus:border-primary-500"
                  />
                </div>

                {/* Grid de Tratamientos del Catálogo */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 max-h-56 overflow-y-auto pr-1">
                  {catalogoFiltrado.length === 0 ? (
                    <div className="col-span-full py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                      No se encontraron tratamientos que coincidan con la búsqueda.
                    </div>
                  ) : (
                    catalogoFiltrado.map((cat) => (
                      <div
                        key={cat.id}
                        className="p-2.5 bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 rounded-xl flex items-center justify-between gap-2 hover:border-slate-300 dark:hover:border-slate-500 transition shadow-xs"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-slate-900 dark:text-white truncate" title={cat.nombre}>
                            {cat.nombre}
                          </div>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-slate-400">
                            <span className="font-mono text-dental-600 dark:text-primary-400 font-bold">
                              {moneda(cat.costo_base ?? cat.precio_base ?? 0)}
                            </span>
                            <span>•</span>
                            <span className="truncate">{cat.categoria}</span>
                          </div>
                        </div>

                        <button
                          onClick={() => handleAsignarTratamientoACara(cat)}
                          disabled={actionLoading}
                          className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold rounded-lg transition shadow-xs shrink-0 flex items-center gap-1"
                        >
                          <Plus className="w-3 h-3" />
                          <span>Asignar</span>
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Selector de Espacios Clínicos: Diagnóstico Inicial vs Presupuesto */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setSeccionTab('TODOS')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              seccionTab === 'TODOS'
                ? 'bg-dental-600 dark:bg-primary-600 text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Ver Ambos Espacios</span>
          </button>

          <button
            type="button"
            onClick={() => setSeccionTab('DIAGNOSTICO_INICIAL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              seccionTab === 'DIAGNOSTICO_INICIAL'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800/60'
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>1. Diagnóstico y Evaluación Inicial ({hallazgosIniciales.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setSeccionTab('PRESUPUESTO')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              seccionTab === 'PRESUPUESTO'
                ? 'bg-dental-600 dark:bg-primary-600 text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>2. Presupuesto & Plan de Tratamiento ({draftItems.length})</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span>Estado de Ingreso Inicial</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
            <span>Tratamientos a Realizar</span>
          </span>
        </div>
      </div>

      {/* ESPACIO 1: Diagnóstico y Evaluación Inicial (Estado de Ingreso del Paciente) */}
      {(seccionTab === 'TODOS' || seccionTab === 'DIAGNOSTICO_INICIAL') && (
        <div className="bg-white dark:bg-slate-800/60 border border-emerald-500/20 dark:border-emerald-500/30 rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-700/60">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 uppercase tracking-wide">
                  Anamnesis e Ingreso
                </span>
                <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <ClipboardList className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  Diagnóstico y Evaluación Inicial (¿Cómo llegó el paciente?)
                </h2>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Registro histórico y clínico de las piezas dentales, restauraciones previas, ausencias y patologías que el paciente ya presentaba al momento de ingresar a la clínica. No genera cargos de cobro.
              </p>
            </div>

            {/* Métricas de Ingreso */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700/60 text-right">
                <span className="block text-[10px] text-slate-400 uppercase font-semibold">Total Ingreso</span>
                <span className="text-sm font-bold text-slate-800 dark:text-white">{hallazgosIniciales.length}</span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 text-right">
                <span className="block text-[10px] text-emerald-600 dark:text-emerald-400 uppercase font-semibold">Condiciones Previas</span>
                <span className="text-sm font-bold text-emerald-700 dark:text-emerald-300">
                  {hallazgosIniciales.filter((h) => !h.es_inexistente).length}
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-right">
                <span className="block text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Piezas Ausentes</span>
                <span className="text-sm font-bold text-slate-600 dark:text-slate-300">
                  {hallazgosIniciales.filter((h) => h.es_inexistente).length}
                </span>
              </div>
            </div>
          </div>

          {/* Tabla de Hallazgos de Ingreso */}
          {hallazgosIniciales.length === 0 ? (
            <div className="py-8 px-4 text-center border-2 border-dashed border-slate-200 dark:border-slate-700/60 rounded-xl space-y-2">
              <FileSpreadsheet className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto" />
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                No hay hallazgos de ingreso registrados aún
              </div>
              <p className="text-[11px] text-slate-400 max-w-md mx-auto">
                Selecciona una pieza en el odontograma con el estado verde <span className="text-emerald-600 dark:text-emerald-400 font-semibold">"Diagnóstico y evaluación inicial"</span> o gris <span className="text-slate-500 font-semibold">"Pieza inexistente"</span> para documentar el estado exacto con el que llegó el paciente.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-emerald-50/70 dark:bg-slate-900/80 text-emerald-900 dark:text-emerald-300 uppercase tracking-wider font-semibold border-b border-emerald-200 dark:border-slate-700/60">
                  <tr>
                    <th className="py-2.5 px-3">Pieza FDI</th>
                    <th className="py-2.5 px-3">Nombre Anatómico</th>
                    <th className="py-2.5 px-3">Superficie / Cara</th>
                    <th className="py-2.5 px-3">Diagnóstico / Condición de Ingreso</th>
                    <th className="py-2.5 px-3">Observación Clínica Registrada</th>
                    <th className="py-2.5 px-3 text-center">Fecha Registro</th>
                    <th className="py-2.5 px-3 text-center">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                  {hallazgosIniciales.map((item) => (
                    <tr
                      key={`${item.id || item.pieza_fdi}-${item.superficie}`}
                      className="hover:bg-emerald-50/40 dark:hover:bg-slate-700/30 transition"
                    >
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-900 dark:text-white">
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          #{item.pieza_fdi}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                        {item.nombre_diente}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                          {SUPERFICIES_LIST.find((s) => s.id === item.superficie)?.label || item.superficie}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        {item.es_inexistente ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-300 border border-slate-500/30">
                            <span className="w-2 h-2 rounded-full bg-slate-500" />
                            Pieza Ausente / Inexistente
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            {CONDICIONES_LABEL_MAP[item.condicion] || item.condicion}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400 max-w-xs truncate" title={item.detalle}>
                        {item.detalle || '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Ingreso inicial'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <button
                          type="button"
                          onClick={() => handleEliminarHallazgoInicial(item)}
                          className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition cursor-pointer"
                          title="Eliminar registro de ingreso"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ESPACIO 2: Presupuesto Dental & Plan de Tratamiento */}
      {(seccionTab === 'TODOS' || seccionTab === 'PRESUPUESTO') && (
        <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-700/60">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              Presupuesto Dental & Plan de Tratamiento
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Tratamientos formulados por cara/pieza. Calcula montos, ajusta descuentos y guarda el plan clínico.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleGuardarPlanTratamiento}
              disabled={actionLoading || draftItems.length === 0}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5"
            >
              <Save className="w-4 h-4" />
              <span>Guardar Plan de Tratamiento</span>
            </button>
          </div>
        </div>

        {/* Tabla de Prestaciones Presupuestadas */}
        {draftItems.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            Aún no se han asignado tratamientos para este paciente. Selecciona una cara o raíz del odontograma y haz clic en "+ Asignar".
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700/60">
                  <tr>
                    <th className="py-2.5 px-3">Pieza FDI</th>
                    <th className="py-2.5 px-3">Cara / Superficie</th>
                    <th className="py-2.5 px-3">Tratamiento Asignado</th>
                    <th className="py-2.5 px-3 text-right">Precio Unit. ({simbolo})</th>
                    <th className="py-2.5 px-3 text-right">Descuento ({simbolo})</th>
                    <th className="py-2.5 px-3 text-right">Subtotal ({simbolo})</th>
                    <th className="py-2.5 px-3 text-center">Alta Médica</th>
                    <th className="py-2.5 px-3 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40 text-slate-700 dark:text-slate-300">
                  {draftItems.map((item, idx) => {
                    const pUnit = Number(item.precio_unitario || 0);
                    const desc = Number(item.descuento || 0);
                    const total = Math.max(0, pUnit - desc);

                    return (
                      <tr key={item.id || idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/20 transition">
                        <td className="py-2.5 px-3 font-mono font-bold text-dental-600 dark:text-primary-400">
                          {item.pieza_fdi ? `#${item.pieza_fdi}` : 'Boca completa'}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-300 font-semibold text-[11px] border border-slate-200 dark:border-slate-700">
                            {item.superficie || 'GENERAL'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">
                          <div>{item.nombre_tratamiento}</div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400">{item.categoria}</div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          {moneda(pUnit)}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={item.descuento}
                            onChange={(e) => handleUpdateItemDescuento(idx, e.target.value)}
                            className="w-20 px-2 py-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-right text-xs font-mono text-amber-600 dark:text-amber-400 focus:outline-none focus:border-amber-500"
                          />
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                          {moneda(total)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => handleToggleAltaMedica(item, idx)}
                            className={`px-3 py-1 rounded-lg text-[11px] font-bold border transition flex items-center justify-center gap-1.5 mx-auto ${
                              item.estado === 'COMPLETADO'
                                ? 'bg-blue-50 dark:bg-blue-500/20 border-blue-400 dark:border-blue-500 text-blue-700 dark:text-blue-300 shadow-xs'
                                : 'bg-slate-100 dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:border-blue-300'
                            }`}
                            title={item.estado === 'COMPLETADO' ? 'Tratamiento completado / Alta médica' : 'Dar alta médica al procedimiento'}
                          >
                            {item.estado === 'COMPLETADO' ? (
                              <>
                                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                <span>Alta Médica</span>
                              </>
                            ) : (
                              <span>Dar Alta</span>
                            )}
                          </button>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            onClick={() => handleEliminarItemPlan(item, idx)}
                            className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition"
                            title="Eliminar del presupuesto"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Resumen Financiero del Presupuesto */}
            <div className="bg-slate-50 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4 text-xs">
                <div>
                  <span className="text-slate-500 dark:text-slate-400">Total Procedimientos: </span>
                  <span className="font-bold text-slate-900 dark:text-white font-mono">{totalesCalculados.cantidad}</span>
                </div>
                <div className="w-px h-4 bg-slate-300 dark:bg-slate-700" />
                <div>
                  <span className="text-slate-500 dark:text-slate-400">Subtotal Bruto: </span>
                  <span className="font-bold text-slate-800 dark:text-slate-200 font-mono">
                    {moneda(totalesCalculados.subtotal)}
                  </span>
                </div>
                <div className="w-px h-4 bg-slate-300 dark:bg-slate-700" />
                <div>
                  <span className="text-slate-500 dark:text-slate-400">Descuentos Totales: </span>
                  <span className="font-bold text-amber-600 dark:text-amber-400 font-mono">
                    -{moneda(totalesCalculados.totalDescuentos)}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-wrap justify-end">
                <div className="text-right">
                  <div className="flex items-center justify-end gap-1.5 mb-0.5">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">TOTAL PRESUPUESTADO</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      activePlan?.estado === 'APROBADO' || activePlan?.estado === 'EN_CURSO'
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                    }`}>
                      {activePlan?.estado || 'PROPUESTO'}
                    </span>
                  </div>
                  <div className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {moneda(totalesCalculados.totalPresupuesto)}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleGuardarPlanTratamiento('PROPUESTO')}
                    disabled={actionLoading || draftItems.length === 0}
                    className="px-3 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl transition flex items-center gap-1.5 cursor-pointer"
                    title="Guardar como presupuesto o propuesta preliminar"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Guardar Propuesta</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleGuardarPlanTratamiento('APROBADO')}
                    disabled={actionLoading || draftItems.length === 0}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl transition shadow-xs flex items-center gap-1.5 cursor-pointer"
                    title="Aprobar plan e imputar formalmente el cobro a la cuenta del paciente"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Aprobar y Cargar a Cuenta</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    )}
  </div>
  );
}
