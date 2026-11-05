import React, { useState, useEffect, useRef } from 'react';
import { Search, User, X, Check, ChevronDown } from 'lucide-react';

export default function PacienteSearchInput({
  pacientes = [],
  selectedPacienteId = '',
  onSelectPaciente,
  placeholder = 'Buscar paciente por nombre, apellido o CI...',
  label = null,
  required = false,
  disabled = false,
  className = '',
  dropdownClassName = '',
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const selectedPaciente = pacientes.find((p) => p.id === selectedPacienteId);

  // Cerrar dropdown al hacer click afuera
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filtrado de pacientes en tiempo real
  const filteredPacientes = pacientes.filter((p) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase().trim();
    const nombreCompleto = `${p.nombres || ''} ${p.apellidos || ''}`.toLowerCase();
    const doc = (p.numero_documento || '').toLowerCase();
    const tel = (p.telefono || '').toLowerCase();
    return nombreCompleto.includes(term) || doc.includes(term) || tel.includes(term);
  });

  const handleSelect = (paciente) => {
    onSelectPaciente(paciente.id, paciente);
    setSearchTerm('');
    setIsOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onSelectPaciente('', null);
    setSearchTerm('');
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {label && (
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
          {label} {required && <span className="text-rose-500">*</span>}
        </label>
      )}

      {selectedPaciente && !isOpen ? (
        // Estado: Paciente Seleccionado
        <div
          onClick={() => !disabled && setIsOpen(true)}
          className={`flex items-center justify-between px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-800 dark:text-white text-xs font-medium transition cursor-pointer hover:border-primary-500 dark:hover:border-primary-500 ${
            disabled ? 'opacity-60 cursor-not-allowed' : ''
          }`}
        >
          <div className="flex items-center gap-2 truncate mr-2">
            <div className="w-6 h-6 rounded-lg bg-primary-500/10 dark:bg-primary-500/20 text-primary-600 dark:text-primary-400 flex items-center justify-center font-bold text-[11px] shrink-0">
              {selectedPaciente.nombres ? selectedPaciente.nombres[0].toUpperCase() : 'P'}
            </div>
            <div className="truncate">
              <span className="font-bold text-slate-900 dark:text-white">
                {selectedPaciente.nombres} {selectedPaciente.apellidos}
              </span>
              <span className="ml-2 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                ({selectedPaciente.tipo_documento || 'CI'}: {selectedPaciente.numero_documento})
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {!disabled && (
              <button
                type="button"
                onClick={handleClear}
                title="Cambiar o deseleccionar paciente"
                className="p-1 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </div>
        </div>
      ) : (
        // Estado: Barra de Búsqueda Activa
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            ref={inputRef}
            type="text"
            disabled={disabled}
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={placeholder}
            className="w-full pl-9 pr-8 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Lista Desplegable de Resultados */}
      {isOpen && (
        <div
          className={`absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-y-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl divide-y divide-slate-100 dark:divide-slate-800 ${dropdownClassName}`}
        >
          {filteredPacientes.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 dark:text-slate-400">
              No se encontraron pacientes para "{searchTerm}"
            </div>
          ) : (
            filteredPacientes.slice(0, 15).map((p) => {
              const isSelected = p.id === selectedPacienteId;
              return (
                <div
                  key={p.id}
                  onClick={() => handleSelect(p)}
                  className={`px-3 py-2.5 flex items-center justify-between cursor-pointer transition text-xs ${
                    isSelected
                      ? 'bg-primary-50 dark:bg-primary-950/40 text-primary-900 dark:text-primary-200'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/70 text-slate-800 dark:text-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold flex items-center justify-center text-xs shrink-0 border border-slate-200 dark:border-slate-700">
                      {p.nombres ? p.nombres[0].toUpperCase() : 'P'}
                    </div>
                    <div className="truncate">
                      <div className="font-bold text-slate-900 dark:text-white truncate">
                        {p.nombres} {p.apellidos}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                        {p.tipo_documento || 'CI'}: {p.numero_documento}
                        {p.telefono ? ` · 📞 ${p.telefono}` : ''}
                      </div>
                    </div>
                  </div>

                  {isSelected && <Check className="w-4 h-4 text-primary-600 dark:text-primary-400 shrink-0" />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
