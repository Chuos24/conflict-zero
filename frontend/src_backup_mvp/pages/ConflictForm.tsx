import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useConflictStore } from '../stores/conflictStore';
import { ConflictType, SeverityLevel, ConflictStatus } from '../types';
import type { CreateConflictData } from '../types';

export function ConflictForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const { conflicts, addConflict, updateConflict } = useConflictStore();
  
  const isEditing = Boolean(id);
  const existingConflict = id ? conflicts.find(c => c.id === id) : undefined;

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: ConflictType.OTHER,
    severity: SeverityLevel.LOW,
    status: ConflictStatus.ACTIVE,
    parties: [{ name: '', role: '', contact: '' }]
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (existingConflict) {
      setFormData({
        title: existingConflict.title,
        description: existingConflict.description,
        type: existingConflict.type,
        severity: existingConflict.severity,
        status: existingConflict.status,
        parties: existingConflict.parties.length > 0 
          ? existingConflict.parties.map(p => ({ name: p.name, role: p.role, contact: p.contact || '' }))
          : [{ name: '', role: '', contact: '' }]
      });
    }
  }, [existingConflict]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Validación básica
      if (!formData.title.trim()) {
        throw new Error('El título es obligatorio');
      }
      if (!formData.description.trim()) {
        throw new Error('La descripción es obligatoria');
      }

      const validParties: CreateConflictData['parties'] = formData.parties
        .filter(p => p.name.trim() !== '')
        .map(p => ({ name: p.name, role: p.role, contact: p.contact || undefined }));
      
      if (isEditing && id) {
        await updateConflict(id, {
          ...formData,
          parties: validParties
        } as CreateConflictData);
      } else {
        await addConflict({
          ...formData,
          parties: validParties
        } as CreateConflictData);
      }
      
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setIsSubmitting(false);
    }
  };

  const addParty = () => {
    setFormData(prev => ({
      ...prev,
      parties: [...prev.parties, { name: '', role: '', contact: '' }]
    }));
  };

  const removeParty = (index: number) => {
    setFormData(prev => ({
      ...prev,
      parties: prev.parties.filter((_, i) => i !== index)
    }));
  };

  const updateParty = (index: number, field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      parties: prev.parties.map((party, i) => 
        i === index ? { ...party, [field]: value } : party
      )
    }));
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          {isEditing ? 'Editar Conflicto' : 'Nuevo Conflicto'}
        </h1>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Título */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Título *
            </label>
            <input
              type="text"
              id="title"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe brevemente el conflicto"
              required
            />
          </div>

          {/* Descripción */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Descripción *
            </label>
            <textarea
              id="description"
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe los detalles del conflicto..."
              required
            />
          </div>

          {/* Tipo y Severidad */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-1">
                Tipo
              </label>
              <select
                id="type"
                value={formData.type}
                onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as ConflictType }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={ConflictType.INTERPERSONAL}>Interpersonal</option>
                <option value={ConflictType.ORGANIZATIONAL}>Organizacional</option>
                <option value={ConflictType.RESOURCE}>Recursos</option>
                <option value={ConflictType.POLICY}>Políticas</option>
                <option value={ConflictType.OTHER}>Otro</option>
              </select>
            </div>

            <div>
              <label htmlFor="severity" className="block text-sm font-medium text-gray-700 mb-1">
                Severidad
              </label>
              <select
                id="severity"
                value={formData.severity}
                onChange={(e) => setFormData(prev => ({ ...prev, severity: parseInt(e.target.value) as SeverityLevel }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={SeverityLevel.LOW}>Baja</option>
                <option value={SeverityLevel.MEDIUM}>Media</option>
                <option value={SeverityLevel.HIGH}>Alta</option>
                <option value={SeverityLevel.CRITICAL}>Crítica</option>
              </select>
            </div>
          </div>

          {/* Estado (solo en edición) */}
          {isEditing && (
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                Estado
              </label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value as ConflictStatus }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={ConflictStatus.ACTIVE}>Activo</option>
                <option value={ConflictStatus.PENDING}>Pendiente</option>
                <option value={ConflictStatus.RESOLVED}>Resuelto</option>
                <option value={ConflictStatus.ESCALATED}>Escalado</option>
              </select>
            </div>
          )}

          {/* Partes involucradas */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Partes Involucradas</h3>
              <button
                type="button"
                onClick={addParty}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                + Agregar parte
              </button>
            </div>

            <div className="space-y-4">
              {formData.parties.map((party, index) => (
                <div key={index} className="p-4 bg-gray-50 rounded-md">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Nombre
                      </label>
                      <input
                        type="text"
                        value={party.name}
                        onChange={(e) => updateParty(index, 'name', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        placeholder="Nombre completo"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Rol
                      </label>
                      <input
                        type="text"
                        value={party.role}
                        onChange={(e) => updateParty(index, 'role', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        placeholder="Ej: Demandante, Mediador"
                      />
                    </div>
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Contacto
                        </label>
                        <input
                          type="text"
                          value={party.contact}
                          onChange={(e) => updateParty(index, 'contact', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="Email o teléfono"
                        />
                      </div>
                      {formData.parties.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeParty(index)}
                          className="self-end px-2 py-2 text-red-600 hover:text-red-800"
                          title="Eliminar parte"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Guardando...' : isEditing ? 'Actualizar Conflicto' : 'Crear Conflicto'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              disabled={isSubmitting}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
