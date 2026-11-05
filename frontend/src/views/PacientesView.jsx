import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import {
  Users,
  UserPlus,
  Search,
  Activity,
  FileText,
  DollarSign,
  Camera,
  AlertTriangle,
  Phone,
  Mail,
  Calendar,
  HeartPulse,
  Pill,
  ChevronRight,
  Edit2,
  CheckCircle,
  XCircle,
} from 'lucide-react';

export default function PacientesView() {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedPaciente, setSelectedPaciente] = useState(null);
  const [saldoPaciente, setSaldoPaciente] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [form, setForm] = useState({
    nombres: '',
    apellidos: '',
    tipo_documento: 'RUT',
    numero_documento: '',
    fecha_nacimiento: '',
    sexo: 'M',
    telefono: '',
    email: '',
    direccion: '',
    alergias: '',
    enfermedades_sistemicas: '',
    medicamentos_actuales: '',
    contacto_emergencia_nombre: '',
    contacto_emergencia_telefono: '',
  });

  const loadPacientes = async (query = '') => {
    setLoading(true);
    try {
      const data = await api.getPacientes(query);
      setPacientes(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Error al cargar pacientes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      loadPacientes(search);
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [search]);

  const handleSelectPaciente = async (paciente) => {
    setSelectedPaciente(paciente);
    try {
      const saldo = await api.getPacienteSaldo(paciente.id);
      setSaldoPaciente(saldo);
    } catch (err) {
      setSaldoPaciente(null);
    }
  };

  const handleOpenCreate = () => {
    setEditingId(null);
    setForm({
      nombres: '',
      apellidos: '',
      tipo_documento: 'RUT',
      numero_documento: '',
      fecha_nacimiento: '',
      sexo: 'M',
      telefono: '',
      email: '',
      direccion: '',
      alergias: '',
      enfermedades_sistemicas: '',
      medicamentos_actuales: '',
      contacto_emergencia_nombre: '',
      contacto_emergencia_telefono: '',
    });
    setShowModal(true);
  };

  const handleOpenEdit = (p) => {
    setEditingId(p.id);
    setForm({
      nombres: p.nombres || '',
      apellidos: p.apellidos || '',
      tipo_documento: p.tipo_documento || 'RUT',
      numero_documento: p.numero_documento || '',
      fecha_nacimiento: p.fecha_nacimiento ? p.fecha_nacimiento.slice(0, 10) : '',
      sexo: p.sexo || 'M',
      telefono: p.telefono || '',
      email: p.email || '',
      direccion: p.direccion || '',
      alergias: p.alergias || '',
      enfermedades_sistemicas: p.enfermedades_sistemicas || '',
      medicamentos_actuales: p.medicamentos_actuales || '',
      contacto_emergencia_nombre: p.contacto_emergencia_nombre || '',
      contacto_emergencia_telefono: p.contacto_emergencia_telefono || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editingId) {
        await api.updatePaciente(editingId, form);
        setSuccess('Ficha del paciente actualizada con éxito');
      } else {
        await api.createPaciente(form);
        setSuccess('Paciente registrado correctamente');
      }
      setShowModal(false);
      loadPacientes(search);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Error guardando datos');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Directorio Clínico de Pacientes</h1>
          <p className="text-slate-400 text-sm">
            Gestión de fichas médicas, anamnesis completa, antecedentes sistémicos y deudas (HU-03)
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20"
        >
          <UserPlus className="w-4 h-4" />
          Nuevo Paciente
        </button>
      </div>

      {/* Notificaciones */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Main Grid: Lista y Ficha Detallada */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Columna Izquierda: Búsqueda y Lista */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 space-y-4">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por nombre, RUT o apellido..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-xs focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
            {loading ? (
              <div className="py-8 text-center text-slate-400 text-xs">Cargando pacientes...</div>
            ) : pacientes.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">No se encontraron pacientes.</div>
            ) : (
              pacientes.map((p) => {
                const isSelected = selectedPaciente?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => handleSelectPaciente(p)}
                    className={`p-3 rounded-xl border cursor-pointer transition ${
                      isSelected
                        ? 'bg-primary-600/15 border-primary-500 text-white'
                        : 'bg-slate-900/40 border-slate-700/40 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-white">
                        {p.nombres} {p.apellidos}
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 rounded border border-slate-700">
                        {p.tipo_documento}: {p.numero_documento}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                      <span>{p.telefono || 'Sin teléfono'}</span>
                      {p.alergias && (
                        <span className="text-amber-400 font-medium text-[10px] flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Alergias
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Columna Derecha: Detalle de la Ficha Médica */}
        <div className="lg:col-span-2">
          {selectedPaciente ? (
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-6 space-y-6">
              {/* Header Ficha */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-700/60">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-white">
                      {selectedPaciente.nombres} {selectedPaciente.apellidos}
                    </h2>
                    <span className="px-2.5 py-0.5 bg-primary-500/10 border border-primary-500/30 text-primary-400 rounded-md text-xs font-mono font-bold">
                      {selectedPaciente.tipo_documento}: {selectedPaciente.numero_documento}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400 mt-1">
                    <span>Sexo: {selectedPaciente.sexo === 'M' ? 'Masculino' : selectedPaciente.sexo === 'F' ? 'Femenino' : 'Otro'}</span>
                    <span>·</span>
                    <span>Nacimiento: {selectedPaciente.fecha_nacimiento?.slice(0, 10) || 'N/D'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    to={`/citas?paciente_id=${selectedPaciente.id}&action=nueva_cita`}
                    className="px-3 py-1.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5 shadow-sm"
                  >
                    <Calendar className="w-3.5 h-3.5" /> Agendar Cita
                  </Link>
                  <button
                    onClick={() => handleOpenEdit(selectedPaciente)}
                    className="px-3 py-1.5 bg-slate-700/80 hover:bg-slate-600 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1"
                  >
                    <Edit2 className="w-3.5 h-3.5" /> Editar Ficha
                  </button>
                </div>
              </div>

              {/* Acciones Rápidas del Paciente */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <Link
                  to={`/citas?paciente_id=${selectedPaciente.id}&action=nueva_cita`}
                  className="p-3 bg-primary-600/10 hover:bg-primary-600/20 border border-primary-500/30 rounded-xl text-center group transition"
                >
                  <Calendar className="w-5 h-5 text-primary-400 mx-auto mb-1 group-hover:scale-110 transition" />
                  <span className="text-xs font-semibold text-primary-300 block">Agendar Cita</span>
                  <span className="text-[10px] text-slate-400">HU-05</span>
                </Link>

                <Link
                  to={`/odontograma?paciente_id=${selectedPaciente.id}`}
                  className="p-3 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-500/30 rounded-xl text-center group transition"
                >
                  <Activity className="w-5 h-5 text-emerald-400 mx-auto mb-1 group-hover:scale-110 transition" />
                  <span className="text-xs font-semibold text-emerald-300 block">Odontograma</span>
                  <span className="text-[10px] text-slate-400">HU-04</span>
                </Link>

                <Link
                  to={`/evolucion?paciente_id=${selectedPaciente.id}`}
                  className="p-3 bg-teal-600/10 hover:bg-teal-600/20 border border-teal-500/30 rounded-xl text-center group transition"
                >
                  <FileText className="w-5 h-5 text-teal-400 mx-auto mb-1 group-hover:scale-110 transition" />
                  <span className="text-xs font-semibold text-teal-300 block">Evolución</span>
                  <span className="text-[10px] text-slate-400">HU-07</span>
                </Link>

                <Link
                  to={`/radiografias?paciente_id=${selectedPaciente.id}`}
                  className="p-3 bg-cyan-600/10 hover:bg-cyan-600/20 border border-cyan-500/30 rounded-xl text-center group transition"
                >
                  <Camera className="w-5 h-5 text-cyan-400 mx-auto mb-1 group-hover:scale-110 transition" />
                  <span className="text-xs font-semibold text-cyan-300 block">Radiografías</span>
                  <span className="text-[10px] text-slate-400">HU-08</span>
                </Link>

                <Link
                  to={`/cobranzas?paciente_id=${selectedPaciente.id}`}
                  className="p-3 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-center group transition"
                >
                  <DollarSign className="w-5 h-5 text-indigo-400 mx-auto mb-1 group-hover:scale-110 transition" />
                  <span className="text-xs font-semibold text-indigo-300 block">Cobranza</span>
                  <span className="text-[10px] text-slate-400">HU-11</span>
                </Link>
              </div>

              {/* Estado Financiero / Saldo */}
              <div className="p-4 bg-slate-900/60 border border-slate-700/60 rounded-xl flex items-center justify-between flex-wrap gap-4">
                <div>
                  <span className="text-xs text-slate-400 font-medium">Estado de Cuenta / Deuda:</span>
                  <div className="flex items-center gap-3 mt-1">
                    <span
                      className={`text-lg font-bold ${
                        (saldoPaciente?.saldo_pendiente || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'
                      }`}
                    >
                      ${Number(saldoPaciente?.saldo_pendiente || 0).toLocaleString('es-CL', { minimumFractionDigits: 2 })}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        (saldoPaciente?.saldo_pendiente || 0) > 0
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {(saldoPaciente?.saldo_pendiente || 0) > 0 ? 'DEUDOR' : 'AL DÍA'}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 space-y-0.5 text-right">
                  <div>Presupuesto Total: ${Number(saldoPaciente?.total_tratamientos ?? saldoPaciente?.total_presupuestado ?? 0).toFixed(2)}</div>
                  <div>Abonado: ${Number(saldoPaciente?.total_pagado || 0).toFixed(2)}</div>
                </div>
              </div>

              {/* Anamnesis Médica y Antecedentes */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2 pb-2 border-b border-slate-700/60">
                  <HeartPulse className="w-4 h-4 text-rose-400" />
                  Anamnesis Clínica & Antecedentes
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Alergias */}
                  <div className="p-3.5 bg-rose-500/5 border border-rose-500/20 rounded-xl">
                    <div className="text-xs font-bold text-rose-400 mb-1 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Alergias Conocidas
                    </div>
                    <p className="text-xs text-slate-300">
                      {selectedPaciente.alergias || 'Sin alergias conocidas declaradas.'}
                    </p>
                  </div>

                  {/* Enfermedades Sistémicas */}
                  <div className="p-3.5 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                    <div className="text-xs font-bold text-amber-400 mb-1 flex items-center gap-1.5">
                      <HeartPulse className="w-4 h-4" /> Enfermedades Sistémicas
                    </div>
                    <p className="text-xs text-slate-300">
                      {selectedPaciente.enfermedades_sistemicas || 'Ninguna condición registrada.'}
                    </p>
                  </div>

                  {/* Medicamentos habituales */}
                  <div className="p-3.5 bg-blue-500/5 border border-blue-500/20 rounded-xl">
                    <div className="text-xs font-bold text-blue-400 mb-1 flex items-center gap-1.5">
                      <Pill className="w-4 h-4" /> Medicación Habitual
                    </div>
                    <p className="text-xs text-slate-300">
                      {selectedPaciente.medicamentos_actuales || 'No consume medicamentos habituales.'}
                    </p>
                  </div>
                </div>

                {/* Contacto y Emergencia */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div className="p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl space-y-1 text-xs">
                    <div className="font-semibold text-white mb-2">Información de Contacto</div>
                    <div className="text-slate-300 flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-primary-400" /> {selectedPaciente.telefono || 'Sin teléfono'}
                    </div>
                    <div className="text-slate-300 flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-primary-400" /> {selectedPaciente.email || 'Sin correo'}
                    </div>
                    <div className="text-slate-400 text-[11px] pt-1">
                      Dirección: {selectedPaciente.direccion || 'No registrada'}
                    </div>
                  </div>

                  <div className="p-3.5 bg-slate-900/60 border border-slate-700/40 rounded-xl space-y-1 text-xs">
                    <div className="font-semibold text-white mb-2">Contacto de Emergencia</div>
                    <div className="text-slate-200 font-medium">
                      {selectedPaciente.contacto_emergencia_nombre || 'No asignado'}
                    </div>
                    <div className="text-slate-300 flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-rose-400" /> {selectedPaciente.contacto_emergencia_telefono || 'Sin teléfono'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-12 text-center text-slate-400">
              <Users className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-300">Ningún paciente seleccionado</h3>
              <p className="text-xs text-slate-500 mt-1">
                Haz clic en un paciente de la lista para ver su expediente clínico completo.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modal Crear / Editar Paciente */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-1">
              {editingId ? 'Editar Ficha de Paciente' : 'Registrar Nuevo Paciente'}
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Ingresa los datos personales y la anamnesis médica obligatoria (HU-03).
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Nombres *</label>
                  <input
                    type="text"
                    required
                    value={form.nombres}
                    onChange={(e) => setForm({ ...form, nombres: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Apellidos *</label>
                  <input
                    type="text"
                    required
                    value={form.apellidos}
                    onChange={(e) => setForm({ ...form, apellidos: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Tipo Doc *</label>
                  <select
                    value={form.tipo_documento}
                    onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  >
                    <option value="RUT">RUT</option>
                    <option value="DNI">DNI</option>
                    <option value="PASAPORTE">Pasaporte</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Nº Documento *</label>
                  <input
                    type="text"
                    required
                    value={form.numero_documento}
                    onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Sexo *</label>
                  <select
                    value={form.sexo}
                    onChange={(e) => setForm({ ...form, sexo: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  >
                    <option value="M">Masculino</option>
                    <option value="F">Femenino</option>
                    <option value="OTRO">Otro</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">F. Nacimiento</label>
                  <input
                    type="date"
                    value={form.fecha_nacimiento}
                    onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Teléfono</label>
                  <input
                    type="text"
                    value={form.telefono}
                    onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
              </div>

              <div className="border-t border-slate-800 pt-3">
                <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">
                  Anamnesis Clínica & Salud General
                </span>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Alergias</label>
                    <textarea
                      rows="2"
                      placeholder="Penicilina, látex, etc."
                      value={form.alergias}
                      onChange={(e) => setForm({ ...form, alergias: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Enf. Sistémicas</label>
                    <textarea
                      rows="2"
                      placeholder="Hipertensión, diabetes..."
                      value={form.enfermedades_sistemicas}
                      onChange={(e) => setForm({ ...form, enfermedades_sistemicas: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Medicación Actual</label>
                    <textarea
                      rows="2"
                      placeholder="Aspirina, Metformina..."
                      value={form.medicamentos_actuales}
                      onChange={(e) => setForm({ ...form, medicamentos_actuales: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-3">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Contacto de Emergencia
                </span>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Nombre y Parentesco</label>
                    <input
                      type="text"
                      placeholder="ej. María González (Madre)"
                      value={form.contacto_emergencia_nombre}
                      onChange={(e) => setForm({ ...form, contacto_emergencia_nombre: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Teléfono Emergencia</label>
                    <input
                      type="text"
                      placeholder="+56 9 8765 4321"
                      value={form.contacto_emergencia_telefono}
                      onChange={(e) => setForm({ ...form, contacto_emergencia_telefono: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Guardar Paciente
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
