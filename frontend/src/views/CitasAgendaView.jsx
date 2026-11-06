import React, { useState, useEffect, useMemo } from 'react';
import ErrorModal from '../components/ErrorModal';
import { puedeModificarCita } from '../config/accesos';
import { EnlaceCobroCita } from '../components/CobrosCitaPanel';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { aPeriodoApi } from '../utils/fechas';
import { useAuth } from '../context/AuthContext';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Clock,
  Plus,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  User,
  Users,
  Grid,
  CalendarDays,
  LayoutGrid,
  Shield,
  Stethoscope,
  Trash2,
  Edit3,
  CalendarCheck,
  SlidersHorizontal,
  Sparkles,
  BookOpen,
  Layers,
  ListChecks,
} from 'lucide-react';
import PacienteSearchInput from '../components/PacienteSearchInput';
import { useMoneda } from '../context/MonedaContext';

const LIMITE_LISTADO = 5000; // Máximo que devuelve la API en una consulta

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

// Configuración de colores e identificación por Categoría de Tratamiento
export const getTratamientoConfig = (cita) => {
  if (!cita) {
    return {
      nombre: 'Consulta General',
      colorBadge: 'bg-teal-100 text-teal-800 border-teal-300 dark:bg-teal-500/20 dark:text-teal-300 dark:border-teal-500/40',
      borderLeft: 'border-l-teal-500',
      bgCard: 'bg-teal-50/40 hover:bg-teal-50/70 dark:bg-teal-950/20 dark:hover:bg-teal-950/30 border-teal-200 dark:border-teal-800/60',
      iconColor: 'text-teal-600 dark:text-teal-400',
    };
  }

  // 1. Tomar directamente de la relación con catalogo_tratamientos si existe
  const cat = cita.tratamiento?.categoria || cita.item_plan?.tratamiento?.categoria || cita.categoria_tratamiento;
  const motivo = (cita.tratamiento?.nombre || cita.motivo_consulta || cita.motivo || '').toLowerCase();

  if (cat === 'CIRUGIA_PERIODONCIA' || /cirug|extrac|cordal|molar|quirurg|periodon|frenil|biops/i.test(motivo)) {
    return {
      nombre: 'Cirugía / Perio',
      colorBadge: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-500/20 dark:text-rose-300 dark:border-rose-500/40',
      borderLeft: 'border-l-rose-500',
      bgCard: 'bg-rose-50/60 hover:bg-rose-50 dark:bg-rose-950/20 dark:hover:bg-rose-950/30 border-rose-200 dark:border-rose-800/60',
      iconColor: 'text-rose-600 dark:text-rose-400',
    };
  }
  if (cat === 'ENDODONCIA' || /endo|conducto|pulpo|necros|apic/i.test(motivo)) {
    return {
      nombre: 'Endodoncia',
      colorBadge: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/40',
      borderLeft: 'border-l-amber-500',
      bgCard: 'bg-amber-50/60 hover:bg-amber-50 dark:bg-amber-950/20 dark:hover:bg-amber-950/30 border-amber-200 dark:border-amber-800/60',
      iconColor: 'text-amber-600 dark:text-amber-400',
    };
  }
  if (cat === 'ORTODONCIA' || /ortod|bracket|arco|frenillo|alinead/i.test(motivo)) {
    return {
      nombre: 'Ortodoncia',
      colorBadge: 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-500/20 dark:text-purple-300 dark:border-purple-500/40',
      borderLeft: 'border-l-purple-500',
      bgCard: 'bg-purple-50/60 hover:bg-purple-50 dark:bg-purple-950/20 dark:hover:bg-purple-950/30 border-purple-200 dark:border-purple-800/60',
      iconColor: 'text-purple-600 dark:text-purple-400',
    };
  }
  if (cat === 'RESTAURADORA' || /resina|obturac|curac|caries|amalgam|inlay|onlay/i.test(motivo)) {
    return {
      nombre: 'Operatoria / Resina',
      colorBadge: 'bg-sky-100 text-sky-800 border-sky-300 dark:bg-sky-500/20 dark:text-sky-300 dark:border-sky-500/40',
      borderLeft: 'border-l-sky-500',
      bgCard: 'bg-sky-50/60 hover:bg-sky-50 dark:bg-sky-950/20 dark:hover:bg-sky-950/30 border-sky-200 dark:border-sky-800/60',
      iconColor: 'text-sky-600 dark:text-sky-400',
    };
  }
  if (cat === 'PREVENCION' || /profilax|limpiez|destartraje|tartar|fluor|sellant/i.test(motivo)) {
    return {
      nombre: 'Prevención / Limpieza',
      colorBadge: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/40',
      borderLeft: 'border-l-emerald-500',
      bgCard: 'bg-emerald-50/60 hover:bg-emerald-50 dark:bg-emerald-950/20 dark:hover:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/60',
      iconColor: 'text-emerald-600 dark:text-emerald-400',
    };
  }
  if (cat === 'REHABILITACION_PROTESIS' || /protes|corona|puente|remov|fija/i.test(motivo)) {
    return {
      nombre: 'Prótesis / Corona',
      colorBadge: 'bg-indigo-100 text-indigo-800 border-indigo-300 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-500/40',
      borderLeft: 'border-l-indigo-500',
      bgCard: 'bg-indigo-50/60 hover:bg-indigo-50 dark:bg-indigo-950/20 dark:hover:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800/60',
      iconColor: 'text-indigo-600 dark:text-indigo-400',
    };
  }
  if (cat === 'ESTETICA_DENTAL' || /blanquea|carilla|estetic/i.test(motivo)) {
    return {
      nombre: 'Estética Dental',
      colorBadge: 'bg-fuchsia-100 text-fuchsia-800 border-fuchsia-300 dark:bg-fuchsia-500/20 dark:text-fuchsia-300 dark:border-fuchsia-500/40',
      borderLeft: 'border-l-fuchsia-500',
      bgCard: 'bg-fuchsia-50/60 hover:bg-fuchsia-50 dark:bg-fuchsia-950/20 dark:hover:bg-fuchsia-950/30 border-fuchsia-200 dark:border-fuchsia-800/60',
      iconColor: 'text-fuchsia-600 dark:text-fuchsia-400',
    };
  }
  if (cat === 'IMPLANTOLOGIA' || /implant/i.test(motivo)) {
    return {
      nombre: 'Implantología',
      colorBadge: 'bg-cyan-100 text-cyan-800 border-cyan-300 dark:bg-cyan-500/20 dark:text-cyan-300 dark:border-cyan-500/40',
      borderLeft: 'border-l-cyan-500',
      bgCard: 'bg-cyan-50/60 hover:bg-cyan-50 dark:bg-cyan-950/20 dark:hover:bg-cyan-950/30 border-cyan-200 dark:border-cyan-800/60',
      iconColor: 'text-cyan-600 dark:text-cyan-400',
    };
  }

  return {
    nombre: 'Consulta General',
    colorBadge: 'bg-teal-100 text-teal-800 border-teal-300 dark:bg-teal-500/20 dark:text-teal-300 dark:border-teal-500/40',
    borderLeft: 'border-l-teal-500',
    bgCard: 'bg-teal-50/30 hover:bg-teal-50/60 dark:bg-slate-800/90 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-700',
    iconColor: 'text-teal-600 dark:text-teal-400',
  };
};

const ESTADOS_SIN_RESERVA = ['CANCELADA', 'NO_ASISTIO'];
const COLORES_SILLON = ['bg-teal-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-amber-500', 'bg-fuchsia-500', 'bg-emerald-500'];

export default function CitasAgendaView() {
  const { moneda } = useMoneda();
  const { user, isRecepcion, tienePermiso } = useAuth();
  const [searchParams] = useSearchParams();
  const queryPacienteId = searchParams.get('paciente_id');
  const queryAction = searchParams.get('action');

  const [citas, setCitas] = useState([]);
  const [sillones, setSillones] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [doctores, setDoctores] = useState([]);
  const [catalogoTratamientos, setCatalogoTratamientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Vista actual: 'MES' | 'DIA_SILLONES'
  const [vistaModo, setVistaModo] = useState('DIA_SILLONES');

  // Modo de rango horario en matriz: 'TODO' (24 Horas) | 'LABORAL' (07:00 a 20:30)
  const [rangoHoras, setRangoHoras] = useState('TODO');

  const formatDateLocal = (d) => {
    if (!d) return '';
    const dateObj = typeof d === 'string' ? new Date(d) : d;
    if (isNaN(dateObj.getTime())) return '';
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  // Fecha de referencia seleccionada
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [selectedCategoria, setSelectedCategoria] = useState('');

  // Modal cita (Crear / Editar)
  const [showModal, setShowModal] = useState(false);
  const [editingCitaId, setEditingCitaId] = useState(null);
  const [formCita, setFormCita] = useState({
    paciente_id: queryPacienteId || '',
    doctor_id: '',
    selected_item_plan_ids: [],
    item_plan_id: '',
    tratamiento_id: '',
    box_numero: '1',
    fecha: formatDateLocal(new Date()),
    hora_inicio: '10:00',
    hora_fin: '11:00',
    motivo: '',
    estado: 'PROGRAMADA',
  });

  // Reaccionar a parámetros de URL (?paciente_id=...&action=nueva_cita)
  useEffect(() => {
    if (queryPacienteId) {
      setFormCita((prev) => ({
        ...prev,
        paciente_id: queryPacienteId,
        selected_item_plan_ids: [],
        item_plan_id: '',
        tratamiento_id: '',
      }));
      if (queryAction === 'nueva_cita') {
        setShowModal(true);
      }
    }
  }, [queryPacienteId, queryAction]);

  // Origen de selección de procedimiento: 'PLAN' (Plan de tratamiento) | 'CATALOGO' (General de la BD)
  const [origenTratamiento, setOrigenTratamiento] = useState('PLAN');
  const [pacientePlanItems, setPacientePlanItems] = useState([]);
  const [pacienteOdontograma, setPacienteOdontograma] = useState(null);
  const [loadingPlanPaciente, setLoadingPlanPaciente] = useState(false);
  const [showDescartados, setShowDescartados] = useState(false);

  // Funciones auxiliares para acceder y resolver datos de citas
  const getCitaFecha = (c) => {
    if (c.fecha_inicio_programada) return c.fecha_inicio_programada.slice(0, 10);
    if (c.fecha) return c.fecha.slice(0, 10);
    return '';
  };

  const getCitaHoraInicio = (c) => {
    if (c.fecha_inicio_programada) return c.fecha_inicio_programada.slice(11, 16);
    if (c.hora_inicio) return c.hora_inicio.slice(0, 5);
    return '10:00';
  };

  const getCitaHoraFin = (c) => {
    if (c.fecha_fin_programada) return c.fecha_fin_programada.slice(11, 16);
    if (c.hora_fin) return c.hora_fin.slice(0, 5);
    return '11:00';
  };

  const getCitaMotivo = (c) => {
    return c.motivo_consulta || c.motivo || 'Consulta Odontológica General';
  };

  const getCitaBox = (c) => {
    if (c.box_numero) return parseInt(c.box_numero);
    const coincidencia = (c.notas_adicionales || '').match(/Box\s*(\d+)/);
    return coincidencia ? parseInt(coincidencia[1]) : 1;
  };

  const getCitaPacienteNombre = (c) => {
    if (c.paciente?.nombres) return `${c.paciente.nombres} ${c.paciente.apellidos || ''}`.trim();
    const p = pacientes.find((item) => item.id === c.paciente_id);
    if (p) return `${p.nombres} ${p.apellidos || ''}`.trim();
    return 'Paciente';
  };

  const getCitaDoctorNombre = (c) => {
    if (c.doctor?.nombre_completo) return c.doctor.nombre_completo;
    const d = doctores.find((item) => item.id === c.doctor_id || item.usuario_id === c.doctor_id);
    if (d) return d.nombre_completo || d.username;
    return 'Doctor';
  };

  // Mapeo horario a slots de 30 minutos (0 a 47)
  const getSlotIndexFromTime = (timeStr, isEnd = false) => {
    if (!timeStr) return -1;
    const parts = timeStr.split(':');
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1] || '0', 10);
    if (isNaN(h)) return -1;
    const totalMinutes = h * 60 + m;
    if (isEnd) {
      // Para hora de finalización irregular (ej. 20:45), debe abarcar el slot completo donde concluye
      return Math.ceil(totalMinutes / 30);
    }
    return Math.floor(totalMinutes / 30);
  };

  const getSlotsDuration = (startStr, endStr) => {
    const startIdx = getSlotIndexFromTime(startStr, false);
    const endIdx = getSlotIndexFromTime(endStr, true);
    if (startIdx === -1 || endIdx === -1 || endIdx <= startIdx) return 2; // Default 1 hr = 2 slots de 30 min
    return Math.max(1, endIdx - startIdx);
  };

  const getNextHourStr = (startStr, durationMinutes = 60) => {
    if (!startStr) return '11:00';
    const parts = startStr.split(':');
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1] || '0', 10);
    if (isNaN(h)) return '11:00';
    const totalMins = (h * 60 + m + durationMinutes) % (24 * 60);
    const endH = Math.floor(totalMins / 60);
    const endM = totalMins % 60;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  };

  // Cargar citas según el mes/rango actual
  const loadCitas = async () => {
    setLoading(true);
    setError('');
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
      const totalDays = new Date(year, month + 1, 0).getDate();

      let query = `?${new URLSearchParams(aPeriodoApi(new Date(year, month, 1), new Date(year, month, totalDays)))}`;
      if (selectedDoctorId) query += `&doctor_id=${selectedDoctorId}`;
      if (selectedCategoria) query += `&categoria=${selectedCategoria}`;

      const [cRes, pRes, dRes, tRes, sRes] = await Promise.all([
        api.getCitas(query),
        api.getPacientes('', 0, 100),
        api.getDoctores(),
        api.getCatalogoTratamientos(),
        api.getSillones(),
      ]);
      setSillones(Array.isArray(sRes) ? sRes : []);

      const listaPac = Array.isArray(pRes) ? pRes : [];
      const listaDoc = Array.isArray(dRes) ? dRes : [];
      const listaTrat = Array.isArray(tRes) ? tRes : [];

      setCitas(Array.isArray(cRes) ? cRes : []);
      setPacientes(listaPac);
      setDoctores(listaDoc);
      setCatalogoTratamientos(listaTrat);

      setFormCita((prev) => ({
        ...prev,
        paciente_id: queryPacienteId || prev.paciente_id || listaPac[0]?.id || '',
        doctor_id: prev.doctor_id || user?.doctor_id || listaDoc[0]?.id || '',
      }));
    } catch (err) {
      setError(err.message || 'Error cargando agenda de citas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCitas();
  }, [currentDate.getFullYear(), currentDate.getMonth(), selectedDoctorId, selectedCategoria]);

  // Navegación de meses
  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  // Navegación de días para la matriz
  const handlePrevDay = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() - 1);
    setCurrentDate(d);
  };

  const handleNextDay = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + 1);
    setCurrentDate(d);
  };

  // Transiciones de estado de sillón
  const handleUpdateEstado = async (citaId, nuevoEstado) => {
    try {
      await api.controlSillon(citaId, { estado: nuevoEstado });
      setSuccess(`Estado actualizado a ${nuevoEstado}`);
      setTimeout(() => setSuccess(''), 3000);
      loadCitas();
    } catch (err) {
      setError(err.message || 'Error actualizando estado del sillón');
    }
  };

  // Click en celda vacía de la matriz -> Nueva Cita en ese horario y box
  const handleSlotClick = (boxNum, hora) => {
    const horaFin = getNextHourStr(hora, 60);
    setEditingCitaId(null);
    setFormCita({
      paciente_id: queryPacienteId || '',
      doctor_id: selectedDoctorId || formCita.doctor_id || user?.doctor_id || doctores[0]?.id || '',
      selected_item_plan_ids: [],
      item_plan_id: '',
      tratamiento_id: '',
      box_numero: String(boxNum),
      fecha: formatDateLocal(currentDate),
      hora_inicio: hora,
      hora_fin: horaFin,
      motivo: '',
      estado: 'PROGRAMADA',
    });
    setShowModal(true);
  };

  // Click en tarjeta de cita -> Editar
  const handleEditCita = (cita) => {
    let parsedItemIds = [];
    if (cita.item_plan_id) parsedItemIds.push(cita.item_plan_id);
    if (cita.notas_adicionales && cita.notas_adicionales.includes('ItemsPlan:')) {
      const matches = cita.notas_adicionales.match(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g);
      if (matches) {
        matches.forEach((m) => {
          if (!parsedItemIds.includes(m)) parsedItemIds.push(m);
        });
      }
    }

    setEditingCitaId(cita.id);
    setFormCita({
      paciente_id: cita.paciente_id,
      doctor_id: cita.doctor_id,
      selected_item_plan_ids: parsedItemIds,
      item_plan_id: cita.item_plan_id || '',
      tratamiento_id: cita.tratamiento_id || cita.tratamiento?.id || '',
      box_numero: String(getCitaBox(cita)),
      fecha: getCitaFecha(cita),
      hora_inicio: getCitaHoraInicio(cita),
      hora_fin: getCitaHoraFin(cita),
      motivo: cita.motivo_consulta || cita.motivo || '',
      estado: cita.estado || 'PROGRAMADA',
    });
    setShowModal(true);
  };

  // Guardar cita (Crear o Actualizar)
  const handleSaveCita = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (!formCita.paciente_id) {
        setError('Por favor selecciona un paciente');
        return;
      }
      const fechaInicio = `${formCita.fecha}T${formCita.hora_inicio}:00`;
      const fechaFin = `${formCita.fecha}T${formCita.hora_fin}:00`;
      const motivoConsulta = formCita.motivo?.trim() || 'Consulta Odontológica General';
      const boxNum = parseInt(formCita.box_numero) || 1;
      
      const selectedIds = formCita.selected_item_plan_ids || [];
      const primaryItemPlanId = selectedIds[0] || formCita.item_plan_id || null;
      let notas = `Box ${boxNum}`;
      if (selectedIds.length > 0) {
        notas += ` | ItemsPlan: [${selectedIds.join(', ')}]`;
      }

      const resolvedDoctorId = formCita.doctor_id || user?.doctor_id || doctores[0]?.id;
      if (!resolvedDoctorId) {
        setError('Por favor selecciona un doctor asignado');
        return;
      }

      const payload = {
        paciente_id: formCita.paciente_id,
        doctor_id: resolvedDoctorId,
        item_plan_id: primaryItemPlanId,
        tratamiento_id: formCita.tratamiento_id || null,
        fecha_inicio_programada: fechaInicio,
        fecha_fin_programada: fechaFin,
        motivo_consulta: motivoConsulta,
        notas_adicionales: notas,
        box_numero: boxNum,
        fecha: formCita.fecha,
        hora_inicio: formCita.hora_inicio,
        hora_fin: formCita.hora_fin,
        motivo: motivoConsulta,
        estado: formCita.estado || 'PROGRAMADA',
      };

      if (editingCitaId) {
        await api.updateCita(editingCitaId, payload);
        setSuccess('Cita actualizada exitosamente');
      } else {
        await api.createCita(payload);
        setSuccess('Cita agendada exitosamente en el calendario');
      }

      setShowModal(false);
      setEditingCitaId(null);
      setTimeout(() => setSuccess(''), 3000);
      loadCitas();
    } catch (err) {
      let msg = err.message || 'Error al procesar la cita';
      try {
        const parsed = JSON.parse(msg);
        if (Array.isArray(parsed)) {
          msg = parsed.map((item) => `${item.loc?.slice(1).join('.') || 'campo'}: ${item.msg}`).join(', ');
        }
      } catch (_) {}
      setError(msg);
    }
  };

  // Cancelar cita existente (se conserva en el historial)
  const handleDeleteCita = async () => {
    if (!editingCitaId) return;
    if (!window.confirm('¿Seguro que deseas cancelar esta cita? Quedará en el historial y el horario se liberará.')) return;
    try {
      await api.deleteCita(editingCitaId);
      setSuccess('Cita cancelada correctamente');
      setShowModal(false);
      setEditingCitaId(null);
      setTimeout(() => setSuccess(''), 3000);
      loadCitas();
    } catch (err) {
      setError(err.message || 'Error al cancelar cita');
    }
  };

  // Cargar plan de tratamiento y odontograma cuando se selecciona un paciente en el modal
  useEffect(() => {
    const fetchPacienteTratamientos = async () => {
      if (!formCita.paciente_id) {
        setPacientePlanItems([]);
        setPacienteOdontograma(null);
        return;
      }
      setLoadingPlanPaciente(true);
      try {
        const [planesRes, odontoRes] = await Promise.all([
          api.getPlanes(formCita.paciente_id).catch(() => []),
          api.getOdontogramas(formCita.paciente_id).catch(() => []),
        ]);

        const planesArr = Array.isArray(planesRes) ? planesRes : [];
        let odontoCompleto = null;
        if (Array.isArray(odontoRes) && odontoRes.length > 0) {
          try {
            odontoCompleto = await api.getOdontograma(odontoRes[0].id);
          } catch (_) {}
        }
        setPacienteOdontograma(odontoCompleto);

        const allItems = [];
        planesArr.forEach((plan) => {
          (plan.items || []).forEach((it) => {
            allItems.push({
              ...it,
              plan_titulo: plan.titulo || plan.nombre || 'Plan de Tratamiento',
              plan_estado: plan.estado,
            });
          });
        });
        setPacientePlanItems(allItems);

        const hasPending = allItems.some(
          (it) => it.estado !== 'COMPLETADO' && it.estado !== 'CANCELADO'
        );
        if (hasPending) {
          setOrigenTratamiento('PLAN');
        } else {
          setOrigenTratamiento('CATALOGO');
        }
      } catch (err) {
        console.error('Error cargando tratamientos del paciente:', err);
      } finally {
        setLoadingPlanPaciente(false);
      }
    };

    if (showModal && formCita.paciente_id) {
      fetchPacienteTratamientos();
    }
  }, [formCita.paciente_id, showModal]);

  // Mapeo de hallazgos del odontograma del paciente
  const odontoHallazgosMap = useMemo(() => {
    const map = {};
    if (!pacienteOdontograma?.piezas) return map;
    pacienteOdontograma.piezas.forEach((pieza) => {
      (pieza.hallazgos || []).forEach((h) => {
        const key = `${pieza.numero_fdi}-${h.superficie}`;
        map[key] = {
          ...h,
          pieza_fdi: pieza.numero_fdi,
          esAzul: h.color_hex === '#3B82F6' || h.estado_clinico === 'REALIZADO_EN_CLINICA',
          esRojo: h.color_hex === '#EF4444' || h.estado_clinico === 'REQUERIDO_PATOLOGIA',
        };
        if (h.superficie === 'GENERAL') {
          map[`${pieza.numero_fdi}-GENERAL`] = map[key];
        }
      });
    });
    return map;
  }, [pacienteOdontograma]);

  // Clasificación de tratamientos: Pendientes (Rojo) vs Alta Clínica (Azul - Descartados)
  const { itemsPendientesPlan, itemsDescartadosPlan } = useMemo(() => {
    const pendientes = [];
    const descartados = [];

    pacientePlanItems.forEach((it) => {
      let sup = it.superficie || '';
      if (!sup && it.observaciones?.startsWith('Superficie: ')) {
        sup = it.observaciones.replace('Superficie: ', '').trim();
      }
      if (!sup) sup = 'GENERAL';

      const hallazgoMatch =
        odontoHallazgosMap[`${it.pieza_fdi}-${sup}`] ||
        odontoHallazgosMap[`${it.pieza_fdi}-GENERAL`];

      // ¿Es Alta Clínica / Completado (Azul)?
      const esCompletado =
        it.estado === 'COMPLETADO' ||
        it.estado === 'REALIZADO' ||
        hallazgoMatch?.esAzul;

      const itemEnriched = {
        ...it,
        superficie_normalizada: sup,
        nombre_tratamiento: it.tratamiento?.nombre || it.nombre_tratamiento || 'Procedimiento Dental',
        duracion_estimada_min: it.tratamiento?.duracion_estimada_min || 30,
        costo_base: it.costo_acordado ?? it.precio_unitario ?? it.tratamiento?.costo_base ?? 0,
        hallazgo: hallazgoMatch,
        esAltaClinica: esCompletado,
      };

      if (esCompletado) {
        descartados.push(itemEnriched);
      } else {
        pendientes.push(itemEnriched);
      }
    });

    // Hallazgos en el Odontograma marcados en ROJO (#EF4444) que aún no estén en los ítems
    if (pacienteOdontograma?.piezas) {
      pacienteOdontograma.piezas.forEach((pieza) => {
        (pieza.hallazgos || []).forEach((h) => {
          const esRojo = h.color_hex === '#EF4444' || h.estado_clinico === 'REQUERIDO_PATOLOGIA';
          if (esRojo) {
            const yaEnPendientes = pendientes.some(
              (p) => p.pieza_fdi === pieza.numero_fdi && (p.superficie_normalizada === h.superficie || p.superficie === h.superficie)
            );
            if (!yaEnPendientes) {
              const catMatch = catalogoTratamientos.find(
                (t) => h.detalle?.toLowerCase().includes(t.nombre.toLowerCase()) ||
                       (h.superficie === 'RAIZ' && t.categoria === 'ENDODONCIA')
              ) || catalogoTratamientos[0];

              pendientes.push({
                id: `hallazgo-${h.id}`,
                plan_id: null,
                hallazgo_id: h.id,
                pieza_fdi: pieza.numero_fdi,
                superficie_normalizada: h.superficie,
                tratamiento_id: catMatch?.id || null,
                nombre_tratamiento: h.detalle || `Tratamiento requerido en #${pieza.numero_fdi}`,
                duracion_estimada_min: catMatch?.duracion_estimada_min || 30,
                costo_base: catMatch?.costo_base || 0,
                hallazgo: h,
                es_hallazgo_directo: true,
              });
            }
          }
        });
      });
    }

    return { itemsPendientesPlan: pendientes, itemsDescartadosPlan: descartados };
  }, [pacientePlanItems, odontoHallazgosMap, pacienteOdontograma, catalogoTratamientos]);

  // Alternar selección de ítem desde el plan de tratamiento (soporte multi-tratamiento)
  const handleTogglePlanItem = (it) => {
    const currentSelected = formCita.selected_item_plan_ids || [];
    const isAlreadySelected = currentSelected.includes(it.id);
    let newSelected = [];

    if (isAlreadySelected) {
      newSelected = currentSelected.filter((id) => id !== it.id);
    } else {
      newSelected = [...currentSelected, it.id];
    }

    const selectedObjs = itemsPendientesPlan.filter((p) => newSelected.includes(p.id));

    // Duración total acumulada
    const totalMinutes = selectedObjs.reduce((acc, curr) => acc + (curr.duracion_estimada_min || 30), 0) || 30;
    const newHoraFin = getNextHourStr(formCita.hora_inicio, totalMinutes);

    // Concatenación descriptiva de motivos
    const combinedMotivo = selectedObjs.map((curr) => {
      const piezaStr = curr.pieza_fdi ? `#${curr.pieza_fdi}` : 'Gral';
      const supStr = curr.superficie_normalizada && curr.superficie_normalizada !== 'GENERAL' ? ` (${curr.superficie_normalizada})` : '';
      return `${curr.nombre_tratamiento} · Pieza ${piezaStr}${supStr}`;
    }).join(' + ');

    setFormCita((prev) => ({
      ...prev,
      selected_item_plan_ids: newSelected,
      item_plan_id: newSelected[0] || '',
      tratamiento_id: selectedObjs[0]?.tratamiento_id || '',
      hora_fin: newHoraFin,
      motivo: combinedMotivo || prev.motivo,
    }));
  };

  const handleSelectAllPlanItems = () => {
    const allIds = itemsPendientesPlan.map((it) => it.id);
    const totalMinutes = itemsPendientesPlan.reduce((acc, curr) => acc + (curr.duracion_estimada_min || 30), 0) || 30;
    const newHoraFin = getNextHourStr(formCita.hora_inicio, totalMinutes);
    const combinedMotivo = itemsPendientesPlan.map((curr) => {
      const piezaStr = curr.pieza_fdi ? `#${curr.pieza_fdi}` : 'Gral';
      const supStr = curr.superficie_normalizada && curr.superficie_normalizada !== 'GENERAL' ? ` (${curr.superficie_normalizada})` : '';
      return `${curr.nombre_tratamiento} · Pieza ${piezaStr}${supStr}`;
    }).join(' + ');

    setFormCita((prev) => ({
      ...prev,
      selected_item_plan_ids: allIds,
      item_plan_id: allIds[0] || '',
      tratamiento_id: itemsPendientesPlan[0]?.tratamiento_id || '',
      hora_fin: newHoraFin,
      motivo: combinedMotivo || prev.motivo,
    }));
  };

  const handleClearSelectedPlanItems = () => {
    setFormCita((prev) => ({
      ...prev,
      selected_item_plan_ids: [],
      item_plan_id: '',
      tratamiento_id: '',
      motivo: '',
    }));
  };

  // Generador de la cuadrícula del mes
  const generateMonthDays = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7; // Lunes = 0
    const totalDays = new Date(year, month + 1, 0).getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();

    const days = [];

    // Días del mes previo
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const dayNum = prevMonthDays - i;
      const prevM = month === 0 ? 11 : month - 1;
      const prevY = month === 0 ? year - 1 : year;
      const dateStr = `${prevY}-${String(prevM + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
      days.push({
        day: dayNum,
        monthOffset: -1,
        dateStr,
      });
    }

    // Días del mes actual
    const todayStr = formatDateLocal(new Date());
    for (let i = 1; i <= totalDays; i++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
      days.push({
        day: i,
        monthOffset: 0,
        dateStr,
        isToday: dateStr === todayStr,
      });
    }

    // Rellenar hasta múltiplo de 7
    const remaining = (7 - (days.length % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      const nextM = month === 11 ? 0 : month + 1;
      const nextY = month === 11 ? year + 1 : year;
      const dateStr = `${nextY}-${String(nextM + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
      days.push({
        day: i,
        monthOffset: 1,
        dateStr,
      });
    }

    return days;
  };

  const monthDays = generateMonthDays();
  const selectedDateStr = formatDateLocal(currentDate);

  // Citas del día seleccionado
  const citasDelDia = citas.filter((c) => {
    return getCitaFecha(c) === selectedDateStr;
  });

  // Slots de 30 minutos estrictamente limitados de 07:00 a 22:00 (solicitado)
  const slotsVisibles = [];
  for (let h = 7; h <= 21; h++) {
    const hh = String(h).padStart(2, '0');
    slotsVisibles.push({
      time: `${hh}:00`,
      index: h * 2,
      isHour: true,
      hour: h,
    });
    slotsVisibles.push({
      time: `${hh}:30`,
      index: h * 2 + 1,
      isHour: false,
      hour: h,
    });
  }
  slotsVisibles.push({
    time: '22:00',
    index: 22 * 2,
    isHour: true,
    hour: 22,
  });

  // Conjunto para rastrear celdas cubiertas por rowSpan en la matriz
  // Sillones activos, más los retirados que todavía tengan citas ese día
  const numerosConCitas = new Set(citasDelDia.map(getCitaBox));
  const sillonesVisibles = [
    ...sillones.filter((s) => s.activo || numerosConCitas.has(s.numero)),
    ...[...numerosConCitas]
      .filter((n) => !sillones.some((s) => s.numero === n))
      .map((n) => ({ numero: n, nombre: `Box ${n}`, especialidad: null, activo: false })),
  ].sort((a, b) => a.numero - b.numero);
  const coveredSlotsByBox = Object.fromEntries(sillonesVisibles.map((s) => [s.numero, new Set()]));
  const sillonesParaElegir = sillones.filter((s) => s.activo || String(s.numero) === String(formCita.box_numero));
  const primerSillon = String(sillones.find((s) => s.activo)?.numero ?? 1);

  const getBadgeColor = (estado) => {
    switch (estado) {
      case 'EN_SILLON':
        return 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500 animate-pulse';
      case 'FINALIZADA':
        return 'bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500';
      case 'EN_ESPERA':
        return 'bg-blue-100 text-blue-900 border-blue-300 dark:bg-blue-500/20 dark:text-blue-300 dark:border-blue-500';
      case 'NO_ASISTIO':
        return 'bg-rose-100 text-rose-900 border-rose-300 dark:bg-rose-500/20 dark:text-rose-300 dark:border-rose-500';
      case 'CANCELADA':
        return 'bg-stone-200 text-stone-700 border-stone-400 border-dashed dark:bg-stone-700/40 dark:text-stone-300 dark:border-stone-500';
      default:
        return 'bg-indigo-100 text-indigo-900 border-indigo-300 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-500';
    }
  };

  // Canceladas e inasistencias quedan como constancia, pero el horario sigue disponible
  const ocupaHorario = (c) => !ESTADOS_SIN_RESERVA.includes(c.estado);
  const puedeAvanzarCita = (c) => tienePermiso('CITAS_SILLON') && puedeModificarCita(c, user);
  const citaEnEdicion = citas.find((c) => c.id === editingCitaId);
  const soloLectura = Boolean(editingCitaId) && !(tienePermiso('CITAS_UPDATE') && puedeModificarCita(citaEnEdicion, user));

  const renderCitaSinReserva = (c) => (
    <div
      key={c.id}
      onClick={(e) => {
        e.stopPropagation();
        handleEditCita(c);
      }}
      className={`px-2.5 py-1.5 mb-1.5 rounded-lg border text-xs cursor-pointer transition hover:brightness-95 dark:hover:brightness-110 ${getBadgeColor(c.estado)}`}
      title={`${c.estado}: ${getCitaPacienteNombre(c)}. Click para ver el detalle`}
    >
      <div className="flex items-center justify-between gap-2 font-bold text-[10px]">
        <span>{c.estado === 'CANCELADA' ? 'CANCELADA' : 'NO ASISTIÓ'}</span>
        <span className="font-mono">{getCitaHoraInicio(c)} - {getCitaHoraFin(c)}</span>
      </div>
      <div className={`truncate mt-0.5 ${c.estado === 'CANCELADA' ? 'line-through' : ''}`}>
        {getCitaPacienteNombre(c)} · Dr(a). {getCitaDoctorNombre(c)}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header Superior */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Calendario de Citas & Matriz de Sillones</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            Control de disponibilidad horaria unificada y flujo de atención por boxes dentales
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Selector de Modo de Vista */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-xl border border-slate-300 dark:border-slate-700 shadow-sm">
            <button
              onClick={() => setVistaModo('DIA_SILLONES')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                vistaModo === 'DIA_SILLONES'
                  ? 'bg-primary-600 text-white shadow'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
              Matriz de Sillones
            </button>
            <button
              onClick={() => setVistaModo('MES')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                vistaModo === 'MES'
                  ? 'bg-primary-600 text-white shadow'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <CalendarDays className="w-4 h-4" />
              Vista Mensual
            </button>
          </div>

          <button
            onClick={() => {
              setEditingCitaId(null);
              setFormCita({
                paciente_id: queryPacienteId || '',
                doctor_id: selectedDoctorId || formCita.doctor_id || user?.doctor_id || doctores[0]?.id || '',
                selected_item_plan_ids: [],
                item_plan_id: '',
                tratamiento_id: '',
                box_numero: primerSillon,
                fecha: selectedDateStr,
                hora_inicio: '10:00',
                hora_fin: '11:00',
                motivo: '',
                estado: 'PROGRAMADA',
              });
              setShowModal(true);
            }}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20"
          >
            <Plus className="w-4 h-4" />
            Nueva Cita
          </button>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-300 dark:border-rose-500/30 rounded-xl text-rose-700 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-300 dark:border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {citas.length >= LIMITE_LISTADO && (
        <div role="status" className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-700 dark:text-amber-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Se muestran las primeras {LIMITE_LISTADO} citas del período. Filtra por doctor o especialidad para ver el resto.
        </div>
      )}

      {/* Barra de Navegación del Calendario */}
      <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
        {/* Controles Mes / Año */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl p-1">
            <button
              onClick={handlePrevMonth}
              className="p-1.5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition"
              title="Mes Anterior"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleToday}
              className="px-2.5 py-1 text-xs font-bold text-primary-600 dark:text-primary-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition"
            >
              Hoy
            </button>
            <button
              onClick={handleNextMonth}
              className="p-1.5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition"
              title="Mes Siguiente"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
            {MESES[currentDate.getMonth()]} {currentDate.getFullYear()}
          </h2>
        </div>

        {/* Filtros de Monitoreo: Especialidad y Doctor */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Filtro por Especialidad/Categoría de Tratamiento */}
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <select
              value={selectedCategoria}
              onChange={(e) => setSelectedCategoria(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-800 dark:text-white text-xs font-semibold shadow-sm focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todas las Especialidades</option>
              <option value="CIRUGIA_PERIODONCIA">Cirugía & Periodoncia</option>
              <option value="ENDODONCIA">Endodoncia</option>
              <option value="ORTODONCIA">Ortodoncia</option>
              <option value="RESTAURADORA">Operatoria / Resina</option>
              <option value="PREVENCION">Prevención / Limpieza</option>
              <option value="REHABILITACION_PROTESIS">Prótesis & Coronas</option>
              <option value="ESTETICA_DENTAL">Estética Dental</option>
              <option value="IMPLANTOLOGIA">Implantología</option>
            </select>
          </div>

          {/* Filtro por Doctor */}
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            <select
              value={selectedDoctorId}
              onChange={(e) => setSelectedDoctorId(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-800 dark:text-white text-xs font-semibold shadow-sm focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todos los Doctores</option>
              {doctores.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  Dr(a). {doc.nombre_completo || doc.username}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* VISTA 1: MATRIZ DE SILLONES UNIFICADA POR HORA (LA SOLICITADA) */}
      {vistaModo === 'DIA_SILLONES' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden space-y-0">
          {/* Cabecera de la Matriz con Navegación de Día e Indicador de Horario 07:00-22:00 */}
          <div className="p-4 bg-slate-50/80 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                Matriz Comparativa de Sillones Dentales
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Los {sillonesVisibles.length} sillones sincronizados por hora en una sola matriz (07:00 a 22:00). Visualiza qué boxes están libres en el mismo horario.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Badge Horario de Atención Limitado */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl shadow-xs text-xs font-semibold text-slate-700 dark:text-slate-300">
                <Clock className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
                <span>Horario Clínico: 07:00 - 22:00</span>
              </div>

              {/* Selector de Día */}
              <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl p-1 shadow-xs">
                <button
                  onClick={handlePrevDay}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-400 transition"
                  title="Día Anterior"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-mono text-xs font-bold text-primary-700 dark:text-primary-300">
                  {selectedDateStr}
                </span>
                <button
                  onClick={handleNextDay}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-400 transition"
                  title="Día Siguiente"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Leyenda de Colores por Tratamiento Clínico */}
          <div className="px-4 py-2.5 bg-slate-100/70 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700/80 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-bold text-slate-600 dark:text-slate-400 flex items-center gap-1.5 mr-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Tratamientos:
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300 border border-rose-200 dark:border-rose-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-rose-500" /> Cirugía / Periodoncia
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-amber-500" /> Endodoncia
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300 border border-purple-200 dark:border-purple-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-purple-500" /> Ortodoncia
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300 border border-sky-200 dark:border-sky-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-sky-500" /> Operatoria / Resinas
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> Prevención / Limpieza
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-indigo-500" /> Prótesis / Coronas
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-teal-50 text-teal-700 dark:bg-teal-500/20 dark:text-teal-300 border border-teal-200 dark:border-teal-500/30 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-teal-500" /> General / Control
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-stone-200 text-stone-700 dark:bg-stone-700/40 dark:text-stone-300 border border-dashed border-stone-400 dark:border-stone-500 font-semibold text-[11px] line-through">
              Cita cancelada
            </span>
          </div>

          {/* TABLA MATRIZ SINCRONIZADA CON ESPACIOS AMPLIADOS */}
          <div className="max-h-[750px] overflow-auto">
            <table className="w-full table-fixed border-collapse text-left" style={{ minWidth: `${112 + sillonesVisibles.length * 260}px` }}>
              <thead className="sticky top-0 z-20 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 border-b border-slate-300 dark:border-slate-700 shadow-sm">
                <tr>
                  <th className="w-28 px-3 py-3.5 text-center text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 border-r border-slate-300 dark:border-slate-700 sticky left-0 z-30 bg-slate-100 dark:bg-slate-800">
                    Hora
                  </th>
                  {sillonesVisibles.map((sillon, indice) => (
                    <th key={sillon.numero} className="px-4 py-3.5 border-r border-slate-300 dark:border-slate-700">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full shadow-sm ${COLORES_SILLON[indice % COLORES_SILLON.length]}`} />
                          {sillon.nombre}
                          {sillon.especialidad && <span className="font-normal text-slate-500 dark:text-slate-400">({sillon.especialidad})</span>}
                          {!sillon.activo && <span className="font-normal text-slate-500 dark:text-slate-400">· Desactivado</span>}
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                          {citasDelDia.filter((c) => getCitaBox(c) === sillon.numero && ocupaHorario(c)).length} citas
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {slotsVisibles.map((slot) => {
                  return (
                    <tr
                      key={slot.time}
                      className="min-h-[64px] hover:bg-slate-50/40 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      {/* Columna Izquierda: Hora Sincronizada con mayor espacio */}
                      <td
                        className={`w-28 px-3 py-3 text-center border-r border-b border-slate-200 dark:border-slate-800 sticky left-0 z-10 select-none min-h-[64px] h-16 ${
                          slot.isHour
                            ? 'bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-white font-extrabold shadow-inner'
                            : 'bg-slate-50/90 dark:bg-slate-900/80 text-slate-500 dark:text-slate-400 font-medium'
                        }`}
                      >
                        <div className="flex items-center justify-center gap-2">
                          <Clock
                            className={`w-4 h-4 ${
                              slot.isHour ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400 dark:text-slate-600'
                            }`}
                          />
                          <span className={slot.isHour ? 'text-sm font-extrabold font-mono tracking-tight' : 'text-xs font-semibold font-mono'}>
                            {slot.time}
                          </span>
                        </div>
                      </td>

                      {/* Las 3 Columnas de Sillones en la misma fila */}
                      {sillonesVisibles.map(({ numero: boxNum }) => {
                        // Si este slot ya está cubierto por el rowSpan de una cita previa en este box, no renderizamos <td>
                        if (coveredSlotsByBox[boxNum].has(slot.index)) {
                          return null;
                        }

                        const citasBox = citasDelDia.filter((c) => getCitaBox(c) === boxNum && ocupaHorario(c));
                        const sinReservaBox = citasDelDia.filter((c) => getCitaBox(c) === boxNum && !ocupaHorario(c));
                        const citaIniciando = citasBox.find((c) => {
                          const sIdx = getSlotIndexFromTime(getCitaHoraInicio(c));
                          return sIdx === slot.index;
                        });

                        if (citaIniciando) {
                          const span = getSlotsDuration(
                            getCitaHoraInicio(citaIniciando),
                            getCitaHoraFin(citaIniciando)
                          );
                          // Marcar slots siguientes como cubiertos por rowSpan
                          for (let k = 1; k < span; k++) {
                            coveredSlotsByBox[boxNum].add(slot.index + k);
                          }

                          const pacNombre = getCitaPacienteNombre(citaIniciando);
                          const docNombre = getCitaDoctorNombre(citaIniciando);
                          const horaIni = getCitaHoraInicio(citaIniciando);
                          const horaF = getCitaHoraFin(citaIniciando);
                          const motivo = getCitaMotivo(citaIniciando);
                          const tratConfig = getTratamientoConfig(citaIniciando);
                          // Constancias que caen dentro del bloque de esta cita
                          const sinReservaEnCelda = sinReservaBox.filter((c) => {
                            const idx = getSlotIndexFromTime(getCitaHoraInicio(c));
                            return idx >= slot.index && idx < slot.index + span;
                          });

                          return (
                            <td
                              key={boxNum}
                              rowSpan={span}
                              className="p-2 border-r border-b border-slate-200 dark:border-slate-800 align-top bg-white dark:bg-slate-900"
                              style={{ height: `${span * 64}px` }}
                            >
                              {sinReservaEnCelda.map(renderCitaSinReserva)}
                              <div
                                onClick={() => handleEditCita(citaIniciando)}
                                className={`p-3 rounded-xl border border-l-4 ${tratConfig.borderLeft} ${tratConfig.bgCard} transition-all shadow-xs hover:shadow-md cursor-pointer group flex flex-col justify-between ${sinReservaEnCelda.length === 0 ? 'h-full' : ''} min-h-[58px]`}
                                title="Click para editar cita odontológica"
                              >
                                <div>
                                  <div className="flex items-center justify-between text-xs mb-1.5 gap-2">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span
                                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${tratConfig.colorBadge}`}
                                      >
                                        {tratConfig.nombre}
                                      </span>
                                      <span
                                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${getBadgeColor(
                                          citaIniciando.estado
                                        )}`}
                                      >
                                        {citaIniciando.estado}
                                      </span>
                                    </div>
                                    <span className="font-mono text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 flex-wrap">
                                      <span className="flex items-center gap-1">
                                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                                        {horaIni} - {horaF}
                                      </span>
                                      {(() => {
                                        try {
                                          const [h1, m1] = horaIni.split(':').map(Number);
                                          const [h2, m2] = horaF.split(':').map(Number);
                                          const diff = (h2 * 60 + (m2 || 0)) - (h1 * 60 + (m1 || 0));
                                          if (diff > 0) {
                                            const dh = Math.floor(diff / 60);
                                            const dm = diff % 60;
                                            return (
                                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold border border-slate-200 dark:border-slate-700">
                                                {dh > 0 ? `${dh}h ` : ''}{dm > 0 ? `${dm}m` : ''}
                                              </span>
                                            );
                                          }
                                        } catch (e) {}
                                        return null;
                                      })()}
                                    </span>
                                  </div>

                                  <div className="text-sm font-extrabold text-slate-900 dark:text-white truncate">
                                    {pacNombre}
                                  </div>
                                  <div className="text-xs text-slate-600 dark:text-slate-300 truncate mt-0.5 flex items-center gap-1.5">
                                    <span className="font-medium">Dr(a). {docNombre}</span>
                                    {citaIniciando.tratamiento ? (
                                      <span className="text-primary-700 dark:text-primary-300 font-semibold truncate">
                                        · {citaIniciando.tratamiento.codigo}: {citaIniciando.tratamiento.nombre}
                                      </span>
                                    ) : (
                                      motivo && <span className="text-slate-500 dark:text-slate-400">· {motivo}</span>
                                    )}
                                  </div>
                                </div>

                                {/* Acciones Rápidas de Sillón */}
                                <div
                                  onClick={(e) => e.stopPropagation()}
                                  style={puedeAvanzarCita(citaIniciando) || citaIniciando.estado === 'FINALIZADA' ? undefined : { display: 'none' }}
                                  className="pt-2 mt-2 border-t border-slate-200/80 dark:border-slate-700/60 flex flex-wrap items-center gap-1.5"
                                >
                                  {(citaIniciando.estado === 'PROGRAMADA' || citaIniciando.estado === 'CONFIRMADA') && (
                                    <button
                                      onClick={() => handleUpdateEstado(citaIniciando.id, 'EN_ESPERA')}
                                      className="w-full py-1.5 bg-blue-50 hover:bg-blue-100 dark:bg-blue-600/20 dark:hover:bg-blue-600/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-500/30 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5"
                                    >
                                      Llegó a Recepción
                                    </button>
                                  )}
                                  {citaIniciando.estado === 'EN_ESPERA' && (
                                    <button
                                      onClick={() => handleUpdateEstado(citaIniciando.id, 'EN_SILLON')}
                                      className="w-full py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-xs"
                                    >
                                      <Play className="w-3.5 h-3.5" /> Pasar a Sillón
                                    </button>
                                  )}
                                  {citaIniciando.estado === 'EN_SILLON' && (
                                    <button
                                      onClick={() => handleUpdateEstado(citaIniciando.id, 'FINALIZADA')}
                                      className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-xs"
                                    >
                                      <CheckCircle2 className="w-3.5 h-3.5" /> Liberar Sillón
                                    </button>
                                  )}
                                  {citaIniciando.estado === 'FINALIZADA' && (
                                    <div className="w-full text-center text-xs font-semibold text-emerald-700 dark:text-emerald-400 flex items-center justify-center gap-1 py-0.5">
                                      <CheckCircle2 className="w-3.5 h-3.5" /> Atención Concluida
                                    </div>
                                  )}
                                  {citaIniciando.estado === 'FINALIZADA' && tienePermiso('CAJA_PAGOS') && (
                                    <EnlaceCobroCita cita={citaIniciando} />
                                  )}
                                </div>
                              </div>
                            </td>
                          );
                        }

                        // Celda vacía -> Sillón Libre con espacio grande y cómodo
                        return (
                          <td
                            key={boxNum}
                            onClick={() => handleSlotClick(boxNum, slot.time)}
                            className="h-16 min-h-[64px] p-2 border-r border-b border-slate-200 dark:border-slate-800/80 bg-white/40 hover:bg-primary-50/50 dark:bg-slate-900/30 dark:hover:bg-slate-800/60 align-middle transition-colors cursor-pointer group"
                            title={`Click para agendar cita en Box ${boxNum} a las ${slot.time}`}
                          >
                            {sinReservaBox
                              .filter((c) => getSlotIndexFromTime(getCitaHoraInicio(c)) === slot.index)
                              .map(renderCitaSinReserva)}
                            <div className="h-full min-h-[46px] rounded-xl border border-dashed border-slate-200 dark:border-slate-800 group-hover:border-primary-400 dark:group-hover:border-primary-500 bg-slate-50/40 group-hover:bg-primary-50/60 dark:bg-slate-900/40 dark:group-hover:bg-primary-950/20 transition-all flex items-center justify-between px-3.5">
                              <span className="text-xs text-slate-400 dark:text-slate-500 group-hover:text-primary-700 dark:group-hover:text-primary-300 font-medium transition flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-700 group-hover:bg-primary-500 transition" />
                                Libre
                              </span>
                              <span className="text-xs font-bold text-primary-600 dark:text-primary-400 opacity-0 group-hover:opacity-100 transition flex items-center gap-1.5">
                                <Plus className="w-3.5 h-3.5" /> Agendar en este horario
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VISTA 2: CALENDARIO MENSUAL (GRID) */}
      {vistaModo === 'MES' && (
        <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 shadow-sm overflow-hidden">
          {/* Cabecera días de la semana */}
          <div className="grid grid-cols-7 gap-2 mb-2">
            {DIAS_SEMANA.map((dia, idx) => (
              <div
                key={idx}
                className="text-center text-xs font-bold text-slate-600 dark:text-slate-400 py-1 uppercase tracking-wider"
              >
                {dia}
              </div>
            ))}
          </div>

          {/* Días del Mes */}
          <div className="grid grid-cols-7 gap-2">
            {monthDays.map((item, idx) => {
              const citasDelDiaItem = citas.filter((c) => {
                return getCitaFecha(c) === item.dateStr;
              });

              const isCurrentMonth = item.monthOffset === 0;
              const isSelected = item.dateStr === selectedDateStr;

              return (
                <div
                  key={idx}
                  onClick={() => {
                    const [y, m, d] = item.dateStr.split('-');
                    setCurrentDate(new Date(parseInt(y), parseInt(m) - 1, parseInt(d)));
                  }}
                  onDoubleClick={() => {
                    setEditingCitaId(null);
                    setFormCita({
                      paciente_id: queryPacienteId || '',
                      doctor_id: selectedDoctorId || formCita.doctor_id || user?.doctor_id || doctores[0]?.id || '',
                      box_numero: primerSillon,
                      fecha: item.dateStr,
                      hora_inicio: '10:00',
                      hora_fin: '11:00',
                      motivo: '',
                      estado: 'PROGRAMADA',
                    });
                    setShowModal(true);
                  }}
                  className={`min-h-[110px] p-2 rounded-xl border flex flex-col justify-between transition cursor-pointer select-none ${
                    !isCurrentMonth
                      ? 'bg-slate-50/50 dark:bg-slate-950/30 border-slate-100 dark:border-slate-800/40 opacity-40'
                      : isSelected
                      ? 'bg-primary-50/80 dark:bg-primary-950/40 border-primary-500 shadow-md ring-2 ring-primary-500/20'
                      : item.isToday
                      ? 'bg-teal-50/70 dark:bg-slate-800/80 border-teal-500 shadow-sm'
                      : 'bg-white dark:bg-slate-900/50 border-slate-200 dark:border-slate-700/40 hover:border-primary-400 dark:hover:border-slate-600'
                  }`}
                  title="Click para seleccionar día · Doble click para agendar cita"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-mono font-bold ${
                        item.isToday
                          ? 'w-6 h-6 rounded-full bg-teal-500 text-white flex items-center justify-center shadow-sm'
                          : isCurrentMonth
                          ? 'text-slate-900 dark:text-white'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {item.day}
                    </span>

                    {citasDelDiaItem.length > 0 && (
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 bg-primary-100 dark:bg-primary-600/30 text-primary-700 dark:text-primary-300 rounded border border-primary-300 dark:border-primary-500/30">
                        {citasDelDiaItem.length}
                      </span>
                    )}
                  </div>

                  {/* Tarjetitas de citas en el día */}
                  <div className="space-y-1 mt-1 flex-1 overflow-y-auto max-h-[70px]">
                    {citasDelDiaItem.slice(0, 3).map((c) => {
                      const pac = getCitaPacienteNombre(c);
                      const hora = getCitaHoraInicio(c);
                      const box = getCitaBox(c);
                      return (
                        <div
                          key={c.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditCita(c);
                          }}
                          className={`px-1.5 py-0.5 rounded text-[10px] truncate border flex items-center justify-between shadow-xs transition hover:brightness-95 dark:hover:brightness-110 cursor-pointer ${getBadgeColor(
                            c.estado
                          )}`}
                          title={`Click para editar: ${hora} - ${pac} (Box ${box})`}
                        >
                          <span className="font-mono font-bold mr-1">{hora}</span>
                          <span className={`truncate flex-1 ${c.estado === 'CANCELADA' ? 'line-through' : ''}`}>{pac}</span>
                        </div>
                      );
                    })}
                    {citasDelDiaItem.length > 3 && (
                      <span className="text-[9px] text-slate-500 dark:text-slate-400 block text-right font-medium">
                        +{citasDelDiaItem.length - 3} más...
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MODAL CITA: NUEVA O EDICIÓN */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  {soloLectura ? 'Detalle de la Cita' : editingCitaId ? 'Editar Cita Odontológica' : 'Agendar Cita en Calendario'}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {editingCitaId
                    ? 'Modifica los datos, horario, doctor o estado de la cita.'
                    : 'Ingresa los datos para programar la atención odontológica.'}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingCitaId(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCita} className="space-y-4">
              <ErrorModal mensaje={error} />
              {soloLectura && (
                <p className="p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-700 dark:text-slate-300">
                  Solo puedes consultar esta cita: pertenece a otro doctor o tu rol no permite modificarla.
                </p>
              )}
              <fieldset disabled={soloLectura} className="space-y-4 border-0 p-0 m-0 min-w-0">
              <PacienteSearchInput
                label="Paciente"
                required
                pacientes={pacientes}
                selectedPacienteId={formCita.paciente_id}
                onSelectPaciente={(newPid) => {
                  setFormCita((prev) => ({
                    ...prev,
                    paciente_id: newPid,
                    selected_item_plan_ids: [],
                    item_plan_id: '',
                    tratamiento_id: '',
                  }));
                }}
                placeholder="Buscar paciente por nombre o CI..."
              />

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Doctor Asignado *</label>
                {user?.puedeElegirDoctor || isRecepcion ? (
                  <select
                    required
                    value={formCita.doctor_id}
                    onChange={(e) => setFormCita({ ...formCita, doctor_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">-- Seleccionar Doctor --</option>
                    {doctores.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        Dr(a). {doc.nombre_completo || doc.username} {doc.especialidad ? `(${doc.especialidad})` : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700/60 rounded-xl text-slate-900 dark:text-white text-xs">
                    <span className="font-semibold text-teal-600 dark:text-teal-400 flex items-center gap-2">
                      <Stethoscope className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                      {soloLectura
                        ? `Dr(a). ${getCitaDoctorNombre(citaEnEdicion)}`
                        : `Dr(a). ${doctores.find((d) => d.id === user?.doctor_id)?.nombre_completo || user?.username} (Tú)`}
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <Shield className="w-3.5 h-3.5 text-slate-400" /> {soloLectura ? 'Solo consulta' : 'Bloqueado a tu perfil'}
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Fecha *</label>
                  <input
                    type="date"
                    required
                    value={formCita.fecha}
                    onChange={(e) => setFormCita({ ...formCita, fecha: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Box / Sillón *</label>
                  <select
                    value={formCita.box_numero}
                    onChange={(e) => setFormCita({ ...formCita, box_numero: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-primary-500"
                  >
                    {sillonesParaElegir.map((s) => (
                      <option key={s.numero} value={String(s.numero)}>
                        {s.nombre}{s.especialidad ? ` (${s.especialidad})` : ''}{s.activo ? '' : ' · Desactivado'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Hora Inicio *</label>
                  <input
                    type="time"
                    required
                    value={formCita.hora_inicio}
                    onChange={(e) => setFormCita({ ...formCita, hora_inicio: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Hora Fin *</label>
                  <input
                    type="time"
                    required
                    value={formCita.hora_fin}
                    onChange={(e) => setFormCita({ ...formCita, hora_fin: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Selección de Tratamiento Clínico: Plan del Paciente (Rojo) vs Catálogo General */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Tratamiento Clínico a Realizar
                  </label>
                  {formCita.paciente_id && (
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                      {loadingPlanPaciente ? 'Cargando plan...' : `${itemsPendientesPlan.length} pendientes en rojo`}
                    </span>
                  )}
                </div>

                {/* Switcher de Origen: Plan de Tratamiento vs Catálogo General */}
                <div className="grid grid-cols-2 gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/60">
                  <button
                    type="button"
                    onClick={() => setOrigenTratamiento('PLAN')}
                    className={`py-1.5 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
                      origenTratamiento === 'PLAN'
                        ? 'bg-rose-500/15 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400 border border-rose-500/30 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span>Plan del Paciente ({itemsPendientesPlan.length})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setOrigenTratamiento('CATALOGO');
                      setFormCita((prev) => ({ ...prev, item_plan_id: '' }));
                    }}
                    className={`py-1.5 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
                      origenTratamiento === 'CATALOGO'
                        ? 'bg-dental-600 dark:bg-primary-600 text-white shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Catálogo General ({catalogoTratamientos.length})</span>
                  </button>
                </div>

                {/* MODO 1: Plan de Tratamiento del Paciente (Marcados en Rojo - Descartando Azul) */}
                {origenTratamiento === 'PLAN' ? (
                  <div className="space-y-2">
                    {loadingPlanPaciente ? (
                      <div className="py-3 text-center text-xs text-slate-500 dark:text-slate-400">
                        Cargando plan y odontograma del paciente...
                      </div>
                    ) : itemsPendientesPlan.length === 0 ? (
                      <div className="p-3 bg-slate-50 dark:bg-slate-800/80 border border-dashed border-slate-300 dark:border-slate-700 rounded-xl text-center space-y-1">
                        <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          No hay tratamientos pendientes en rojo para este paciente.
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          {itemsDescartadosPlan.length > 0
                            ? `Todos los procedimientos del paciente (${itemsDescartadosPlan.length}) ya fueron completados / dados de alta clínica (azul).`
                            : 'El paciente aún no cuenta con un plan de tratamiento activo en el odontograma.'}
                        </p>
                        <button
                          type="button"
                          onClick={() => {
                            setOrigenTratamiento('CATALOGO');
                            setFormCita((prev) => ({ ...prev, item_plan_id: '' }));
                          }}
                          className="mt-1 px-3 py-1 bg-dental-600 hover:bg-dental-500 text-white text-xs font-bold rounded-lg cursor-pointer"
                        >
                          Elegir del Catálogo General
                        </button>
                      </div>
                    ) : (
                      <>
                        {/* Selector Múltiple de Tratamientos Pendientes en Rojo */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-200 dark:border-slate-800">
                            <span className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                              <ListChecks className="w-4 h-4 text-rose-500" />
                              <span>Procedimientos ({formCita.selected_item_plan_ids?.length || 0} de {itemsPendientesPlan.length} seleccionados)</span>
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={handleSelectAllPlanItems}
                                className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 hover:underline cursor-pointer"
                              >
                                Todos
                              </button>
                              <span className="text-slate-300 dark:text-slate-700">|</span>
                              <button
                                type="button"
                                onClick={handleClearSelectedPlanItems}
                                className="text-[11px] font-semibold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer"
                              >
                                Limpiar
                              </button>
                            </div>
                          </div>

                          <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                            {itemsPendientesPlan.map((it) => {
                              const isSelected = formCita.selected_item_plan_ids?.includes(it.id);
                              return (
                                <div
                                  key={it.id}
                                  onClick={() => handleTogglePlanItem(it)}
                                  className={`p-2 rounded-xl border transition cursor-pointer flex items-center justify-between gap-2 ${
                                    isSelected
                                      ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-400 dark:border-rose-500 text-rose-950 dark:text-white shadow-xs'
                                      : 'bg-white dark:bg-slate-800/80 border-slate-200 dark:border-slate-700/80 text-slate-700 dark:text-slate-300 hover:border-rose-300'
                                  }`}
                                >
                                  <div className="flex items-center gap-2.5 min-w-0">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(isSelected)}
                                      onChange={() => {}}
                                      className="w-4 h-4 text-rose-600 rounded border-slate-300 focus:ring-rose-500 pointer-events-none"
                                    />
                                    <div className="min-w-0">
                                      <div className="flex items-center gap-1.5 flex-wrap">
                                        <span className="font-mono font-bold text-[11px] px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300">
                                          #{it.pieza_fdi || 'Gral'}
                                        </span>
                                        <span className="text-xs font-semibold truncate">
                                          {it.nombre_tratamiento}
                                        </span>
                                        {it.superficie_normalizada && it.superficie_normalizada !== 'GENERAL' && (
                                          <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 dark:bg-slate-700 rounded text-slate-600 dark:text-slate-400 font-mono">
                                            {it.superficie_normalizada}
                                          </span>
                                        )}
                                      </div>
                                      <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-2">
                                        <span>⏱ {it.duracion_estimada_min} min</span>
                                        <span>•</span>
                                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{moneda(it.costo_base)}</span>
                                        {it.es_proxima_sesion && (
                                          <span className="text-amber-500 font-bold">★ Próxima sesión</span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex-shrink-0">
                                    <span className={`w-2.5 h-2.5 rounded-full block ${isSelected ? 'bg-rose-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Indicadores de descarte y alta clínica */}
                        <div className="flex items-center justify-between text-[11px] px-1">
                          <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-rose-500" />
                            {itemsPendientesPlan.length} procedimiento(s) pendiente(s) por realizar
                          </span>

                          {itemsDescartadosPlan.length > 0 && (
                            <button
                              type="button"
                              onClick={() => setShowDescartados(!showDescartados)}
                              className="text-blue-600 dark:text-blue-400 font-semibold hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <span className="w-2 h-2 rounded-full bg-blue-500" />
                              <span>{itemsDescartadosPlan.length} en Alta Clínica (descartados)</span>
                              <ChevronDown className={`w-3 h-3 transition-transform ${showDescartados ? 'rotate-180' : ''}`} />
                            </button>
                          )}
                        </div>

                        {/* Panel Desplegable de Tratamientos Descartados (Alta Clínica / Azul) */}
                        {showDescartados && itemsDescartadosPlan.length > 0 && (
                          <div className="p-2.5 bg-blue-50/70 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/40 rounded-xl space-y-1">
                            <div className="text-[10px] font-bold text-blue-700 dark:text-blue-300 uppercase tracking-wide flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-blue-600" />
                              Tratamientos en Alta Clínica / Control Posterior (Descartados de la agenda)
                            </div>
                            <div className="space-y-1 max-h-28 overflow-y-auto">
                              {itemsDescartadosPlan.map((d, idx) => (
                                <div key={d.id || idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between">
                                  <span className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                                    <span>Pieza #{d.pieza_fdi || 'Gral'} ({d.superficie_normalizada}) · {d.nombre_tratamiento}</span>
                                  </span>
                                  <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold">ALTA CLÍNICA</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ) : (
                  /* MODO 2: Catálogo General de la BD */
                  <div>
                    <select
                      value={formCita.tratamiento_id || ''}
                      onChange={(e) => {
                        const tId = e.target.value;
                        const sel = catalogoTratamientos.find((t) => t.id === tId);
                        if (sel) {
                          const hFin = getNextHourStr(formCita.hora_inicio, sel.duracion_estimada_min || 30);
                          setFormCita({
                            ...formCita,
                            item_plan_id: '',
                            tratamiento_id: tId,
                            motivo: sel.nombre,
                            hora_fin: hFin,
                          });
                        } else {
                          setFormCita({
                            ...formCita,
                            item_plan_id: '',
                            tratamiento_id: '',
                          });
                        }
                      }}
                      className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-primary-500 mb-2"
                    >
                      <option value="">-- Seleccionar Procedimiento del Catálogo General --</option>
                      {Object.entries(
                        catalogoTratamientos.reduce((acc, t) => {
                          acc[t.categoria] = acc[t.categoria] || [];
                          acc[t.categoria].push(t);
                          return acc;
                        }, {})
                      ).map(([catKey, list]) => (
                        <optgroup key={catKey} label={catKey.replace(/_/g, ' ')}>
                          {list.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.codigo} · {t.nombre} ({t.duracion_estimada_min} min — {moneda(t.costo_base)})
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                )}

                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 pt-1">
                  Detalle / Motivo de la Cita *
                </label>
                <input
                  type="text"
                  placeholder="ej. Evaluación general, Extracción de tercer molar"
                  value={formCita.motivo}
                  onChange={(e) => setFormCita({ ...formCita, motivo: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-primary-500 placeholder-slate-400"
                />
              </div>

              {/* Selector de Estado en Modo Edición */}
              {editingCitaId && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Estado de la Cita</label>
                  <select
                    value={formCita.estado}
                    onChange={(e) => setFormCita({ ...formCita, estado: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="PROGRAMADA">PROGRAMADA</option>
                    <option value="EN_ESPERA">EN_ESPERA</option>
                    <option value="EN_SILLON">EN_SILLON</option>
                    <option value="FINALIZADA">FINALIZADA</option>
                    <option value="CANCELADA">CANCELADA</option>
                    <option value="NO_ASISTIO">NO_ASISTIO</option>
                  </select>
                </div>
              )}

              </fieldset>

              {/* Botones de Acción */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-800">
                {editingCitaId && !soloLectura && formCita.estado !== 'CANCELADA' && formCita.estado !== 'FINALIZADA' ? (
                  <button
                    type="button"
                    onClick={handleDeleteCita}
                    className="px-3 py-2 bg-rose-50 hover:bg-rose-100 dark:bg-rose-500/20 dark:hover:bg-rose-500/30 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-500/30 text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Cancelar Cita
                  </button>
                ) : (
                  <div />
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingCitaId(null);
                    }}
                    className="px-3 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl transition"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    style={soloLectura ? { display: 'none' } : undefined}
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-primary-600/20 font-semibold"
                  >
                    {editingCitaId ? 'Guardar Cambios' : 'Agendar Cita'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
