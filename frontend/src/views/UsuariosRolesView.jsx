import React, { useState, useEffect } from 'react';
import ErrorModal from '../components/ErrorModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Users,
  Shield,
  Key,
  UserPlus,
  PlusCircle,
  Search,
  CheckCircle,
  XCircle,
  Edit2,
  Lock,
  UserCheck,
  AlertCircle,
  Layers,
} from 'lucide-react';

export default function UsuariosRolesView() {
  const { tienePermiso } = useAuth();
  const [tab, setTab] = useState(tienePermiso('USUARIOS_MANAGE') ? 'usuarios' : 'roles'); // 'usuarios' | 'roles'
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modales
  const [showUserModal, setShowUserModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [selectedRoleForPerms, setSelectedRoleForPerms] = useState(null);
  const [selectedPermIds, setSelectedPermIds] = useState([]);

  // Form Usuario
  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    password: '',
    nombre_completo: '',
    rol_id: '',
    especialidad: '',
    numero_colegiado: '',
    color_agenda: '#3B82F6',
    es_doctor_admin: false,
    telefono: '',
    activo: true,
  });

  // Form Rol
  const [roleForm, setRoleForm] = useState({
    nombre: '',
    descripcion: '',
    permiso_ids: [],
  });

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      // Quien solo administra roles no puede listar usuarios, y viceversa
      const [uRes, rRes, pRes] = await Promise.all([
        tienePermiso('USUARIOS_MANAGE') ? api.getUsuarios() : [],
        api.getRoles(),
        api.getPermisos(),
      ]);
      setUsuarios(Array.isArray(uRes) ? uRes : []);
      setRoles(Array.isArray(rRes) ? rRes : []);
      setPermisos(Array.isArray(pRes) ? pRes : []);
      // Tras guardar se conserva el rol elegido, con sus permisos actualizados
      const rolVigente = rRes?.find((r) => r.id === selectedRoleForPerms?.id) || rRes?.[0];
      if (rolVigente) {
        handleSelectRolePerms(rolVigente);
      }
    } catch (err) {
      setError(err.message || 'Error cargando datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSelectRolePerms = (rol) => {
    setSelectedRoleForPerms(rol);
    const assignedIds = rol.permisos ? rol.permisos.map((p) => p.id) : [];
    setSelectedPermIds(assignedIds);
  };

  const handleTogglePerm = (permId) => {
    if (selectedPermIds.includes(permId)) {
      setSelectedPermIds(selectedPermIds.filter((id) => id !== permId));
    } else {
      setSelectedPermIds([...selectedPermIds, permId]);
    }
  };

  const handleSaveRolePerms = async () => {
    if (!selectedRoleForPerms) return;
    try {
      await api.asignarPermisosRol(selectedRoleForPerms.id, selectedPermIds);
      setSuccess('Permisos de rol actualizados con éxito');
      setTimeout(() => setSuccess(''), 3000);
      loadAll();
    } catch (err) {
      setError(err.message || 'Error al guardar permisos');
    }
  };

  const handleToggleActivo = async (user) => {
    try {
      await api.updateUsuario(user.id, { activo: !user.activo });
      setSuccess(`Usuario ${user.username} ${!user.activo ? 'activado' : 'desactivado'}`);
      setTimeout(() => setSuccess(''), 3000);
      loadAll();
    } catch (err) {
      setError(err.message || 'Error al cambiar estado');
    }
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const selectedRole = roles.find((r) => r.id === userForm.rol_id);
      const isRoleDoctor = selectedRole?.codigo === 'DOCTOR';
      const isRoleAdmin = selectedRole?.codigo === 'ADMIN';
      const shouldHaveDoctorProfile = isRoleDoctor || (isRoleAdmin && userForm.es_doctor_admin);

      const parts = (userForm.nombre_completo || '').trim().split(' ');
      const nombre = parts[0] || userForm.username;
      const apellido = parts.slice(1).join(' ') || (parts[0] ? ' ' : '');

      const payload = {
        username: userForm.username,
        email: userForm.email,
        nombre,
        apellido,
        telefono: userForm.telefono,
        rol_id: userForm.rol_id,
        activo: userForm.activo,
      };

      if (userForm.password) {
        payload.password = userForm.password;
      }

      if (shouldHaveDoctorProfile) {
        payload.doctor_perfil = {
          especialidad: userForm.especialidad || (isRoleAdmin ? 'Odontología General / Dirección Médica' : 'Odontología General'),
          numero_colegiatura: userForm.numero_colegiado || null,
          color_agenda: userForm.color_agenda || '#3B82F6',
        };
      }

      if (editingUser) {
        if (!payload.password) delete payload.password;
        await api.updateUsuario(editingUser.id, payload);
        setSuccess('Usuario actualizado correctamente');
      } else {
        await api.createUsuario(payload);
        setSuccess('Usuario creado exitosamente');
      }
      setShowUserModal(false);
      setEditingUser(null);
      setTimeout(() => setSuccess(''), 3000);
      loadAll();
    } catch (err) {
      setError(err.message || 'Error guardando usuario');
    }
  };

  const handleSaveRole = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.createRol(roleForm);
      setSuccess('Rol creado. Selecciónalo en la lista y marca sus permisos: sin permisos no podrá acceder a nada.');
      setShowRoleModal(false);
      setRoleForm({ nombre: '', descripcion: '', permiso_ids: [] });
      setTimeout(() => setSuccess(''), 6000);
      setTab('roles');
      loadAll();
    } catch (err) {
      setError(err.message || 'Error al crear rol');
    }
  };

  const filteredUsuarios = usuarios.filter((u) => {
    const q = search.toLowerCase();
    return (
      u.username?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      `${u.nombre || ''} ${u.apellido || ''}`.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Usuarios & Control de Acceso RBAC</h1>
          <p className="text-slate-400 text-sm">
            Gestión integral de personal, credenciales, perfiles médicos y permisos granulares (HU-01, HU-02)
          </p>
        </div>
        <div className="flex items-center gap-2">
          {tab === 'usuarios' ? (
            <button
              onClick={() => {
                setEditingUser(null);
                setUserForm({
                  username: '',
                  email: '',
                  password: '',
                  nombre_completo: '',
                  rol_id: roles[0]?.id || '',
                  especialidad: '',
                  numero_colegiado: '',
                  color_agenda: '#3B82F6',
                  es_doctor_admin: false,
                  telefono: '',
                  activo: true,
                });
                setShowUserModal(true);
              }}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20"
            >
              <UserPlus className="w-4 h-4" />
              Nuevo Usuario
            </button>
          ) : (
            <button
              onClick={() => setShowRoleModal(true)}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-primary-600/20"
            >
              <PlusCircle className="w-4 h-4" />
              Nuevo Rol
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800">
        <button
          onClick={() => setTab('usuarios')}
          className={`pb-3 px-4 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            tab === 'usuarios'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          Usuarios del Sistema ({usuarios.length})
        </button>
        <button
          onClick={() => setTab('roles')}
          className={`pb-3 px-4 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            tab === 'roles'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Shield className="w-4 h-4" />
          Roles y Matriz de Permisos ({roles.length})
        </button>
      </div>

      {/* Mensajes */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* TAB USUARIOS */}
      {tab === 'usuarios' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Buscar por usuario, nombre o email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-800/80 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-xs focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-700/60">
                  <tr>
                    <th className="py-3 px-4">Usuario / Nombre</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Rol Asignado</th>
                    <th className="py-3 px-4">Perfil Médico</th>
                    <th className="py-3 px-4 text-center">Estado</th>
                    <th className="py-3 px-4 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40 text-slate-300">
                  {filteredUsuarios.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-700/20 transition">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{`${u.nombre || ''} ${u.apellido || ''}`.trim() || u.username}</div>
                        <div className="text-[11px] text-slate-400 font-mono">@{u.username}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">{u.email}</td>
                      <td className="py-3 px-4">
                        <span className="px-2.5 py-1 bg-primary-500/10 border border-primary-500/30 text-primary-400 rounded-lg text-[11px] font-semibold">
                          {u.rol?.nombre || 'Sin Rol'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {u.doctor_perfil ? (
                          <div>
                            <span className="text-teal-400 font-medium">{u.doctor_perfil.especialidad}</span>
                            {u.doctor_perfil.numero_colegiatura && (
                              <div className="text-[10px] text-slate-500">Col: {u.doctor_perfil.numero_colegiatura}</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">Personal general</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            u.activo
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {u.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => {
                            setEditingUser(u);
                            const hasDocProfile = !!u.doctor_perfil || !!u.especialidad;
                            setUserForm({
                              username: u.username,
                              email: u.email,
                              password: '',
                              nombre_completo: u.nombre_completo || `${u.nombre || ''} ${u.apellido || ''}`.trim(),
                              rol_id: u.rol_id || '',
                              especialidad: u.doctor_perfil?.especialidad || u.especialidad || '',
                              numero_colegiado: u.doctor_perfil?.numero_colegiatura || u.numero_colegiado || '',
                              color_agenda: u.doctor_perfil?.color_agenda || '#3B82F6',
                              es_doctor_admin: hasDocProfile,
                              telefono: u.telefono || '',
                              activo: u.activo,
                            });
                            setShowUserModal(true);
                          }}
                          className="p-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg transition"
                          title="Editar usuario"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleActivo(u)}
                          className={`p-1.5 border rounded-lg transition ${
                            u.activo
                              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
                              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                          }`}
                          title={u.activo ? 'Desactivar acceso' : 'Reactivar acceso'}
                        >
                          {u.activo ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB ROLES & PERMISOS */}
      {tab === 'roles' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Lista de Roles */}
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 pb-2 border-b border-slate-700/60">
              <Shield className="w-4 h-4 text-primary-400" />
              Roles Definidos
            </h3>
            <div className="space-y-2">
              {roles.map((rol) => (
                <div
                  key={rol.id}
                  onClick={() => handleSelectRolePerms(rol)}
                  className={`p-3 rounded-xl border cursor-pointer transition ${
                    selectedRoleForPerms?.id === rol.id
                      ? 'bg-primary-600/15 border-primary-500 text-white'
                      : 'bg-slate-900/50 border-slate-700/50 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs">{rol.nombre}</span>
                    <span className="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded-md">
                      {rol.permisos?.length || 0} permisos
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                    {rol.descripcion || 'Sin descripción'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Matriz de Permisos */}
          <div className="lg:col-span-2 bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Permisos para: <span className="text-primary-400">{selectedRoleForPerms?.nombre || 'Seleccione un rol'}</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Marca o desmarca los privilegios asignados a este perfil RBAC.
                </p>
              </div>
              <button
                onClick={handleSaveRolePerms}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-emerald-600/20 transition flex items-center gap-1.5"
              >
                <CheckCircle className="w-4 h-4" />
                Guardar Permisos
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[500px] overflow-y-auto pr-1">
              {permisos.map((p) => {
                const checked = selectedPermIds.includes(p.id);
                return (
                  <div
                    key={p.id}
                    onClick={() => handleTogglePerm(p.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-start gap-3 ${
                      checked
                        ? 'bg-slate-900/90 border-primary-500/70 shadow-sm'
                        : 'bg-slate-900/40 border-slate-700/40 opacity-75 hover:opacity-100'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {}} // handled by parent div
                      className="mt-0.5 rounded border-slate-700 text-primary-500 focus:ring-0 cursor-pointer"
                    />
                    <div>
                      <div className="text-xs font-semibold text-white">{p.codigo_permiso}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{p.descripcion}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Modal Usuario */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-1">
              {editingUser ? 'Editar Usuario' : 'Crear Nuevo Usuario'}
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Ingresa los datos del empleado y asigna el perfil de acceso correspondiente.
            </p>

            <form onSubmit={handleSaveUser} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Username *</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingUser}
                    value={userForm.username}
                    onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs disabled:opacity-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    {editingUser ? 'Nueva Contraseña (Opcional)' : 'Contraseña *'}
                  </label>
                  <input
                    type="password"
                    required={!editingUser}
                    value={userForm.password}
                    onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                    placeholder={editingUser ? 'Dejar en blanco para conservar' : '••••••••'}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Nombre Completo *</label>
                <input
                  type="text"
                  required
                  value={userForm.nombre_completo}
                  onChange={(e) => setUserForm({ ...userForm, nombre_completo: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Email *</label>
                  <input
                    type="email"
                    required
                    value={userForm.email}
                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Rol *</label>
                  <select
                    value={userForm.rol_id}
                    onChange={(e) => setUserForm({ ...userForm, rol_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Pregunta si el rol seleccionado es ADMIN */}
              {roles.find((r) => r.id === userForm.rol_id)?.codigo === 'ADMIN' && (
                <div className="p-3 bg-primary-950/40 border border-primary-500/40 rounded-xl space-y-1.5">
                  <label className="flex items-center gap-2.5 cursor-pointer text-xs font-semibold text-white">
                    <input
                      type="checkbox"
                      checked={userForm.es_doctor_admin}
                      onChange={(e) => setUserForm({ ...userForm, es_doctor_admin: e.target.checked })}
                      className="rounded border-slate-700 text-primary-500 focus:ring-0 cursor-pointer w-4 h-4"
                    />
                    ¿Este Administrador también atenderá pacientes como Odontólogo / Doctor? (Perfil Clínico Dual)
                  </label>
                  <p className="text-[11px] text-slate-400 pl-6">
                    Al activar esta opción se creará su perfil médico oficial para registrar odontogramas, firmar historias clínicas y tener su propia columna en la agenda del sillón.
                  </p>
                </div>
              )}

              {/* Datos Profesionales (Doctores o Admin con Perfil Dual) */}
              {(roles.find((r) => r.id === userForm.rol_id)?.codigo === 'DOCTOR' ||
                (roles.find((r) => r.id === userForm.rol_id)?.codigo === 'ADMIN' && userForm.es_doctor_admin)) && (
                <div className="border-t border-slate-800 pt-3">
                  <span className="text-[11px] font-semibold text-primary-400 uppercase tracking-wider">
                    Datos Profesionales Médicos
                  </span>
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Especialidad</label>
                      <input
                        type="text"
                        placeholder="ej. Odontología General, Ortodoncia"
                        value={userForm.especialidad}
                        onChange={(e) => setUserForm({ ...userForm, especialidad: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Nº Colegiado</label>
                      <input
                        type="text"
                        placeholder="ej. COL-9982"
                        value={userForm.numero_colegiado}
                        onChange={(e) => setUserForm({ ...userForm, numero_colegiado: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                      />
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Color para la Agenda / Sillón</label>
                      <input
                        type="color"
                        value={userForm.color_agenda || '#3B82F6'}
                        onChange={(e) => setUserForm({ ...userForm, color_agenda: e.target.value })}
                        className="w-16 h-8 bg-slate-800 border border-slate-700 rounded-lg cursor-pointer"
                      />
                    </div>
                    <span className="text-xs text-slate-400 mt-4">Identificador visual para la agenda médica.</span>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Rol */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Crear Rol Personalizado</h3>
            <p className="text-xs text-slate-400 mb-4">
              Define un nuevo perfil de acceso para la clínica.
            </p>

            <form onSubmit={handleSaveRole} className="space-y-4">
              <ErrorModal mensaje={error} />
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Nombre del Rol *</label>
                <input
                  type="text"
                  required
                  placeholder="ej. Auditor Externo, Higienista"
                  value={roleForm.nombre}
                  onChange={(e) => setRoleForm({ ...roleForm, nombre: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Descripción</label>
                <textarea
                  rows="3"
                  value={roleForm.descripcion}
                  onChange={(e) => setRoleForm({ ...roleForm, descripcion: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRoleModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Crear Rol
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
