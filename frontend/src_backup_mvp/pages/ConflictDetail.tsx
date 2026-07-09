import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useConflictStore } from '../stores/conflictStore';
import { format } from '../utils/date';

export function ConflictDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentConflict, loading, error, fetchConflict, deleteConflict, setCurrentConflict } = useConflictStore();

  useEffect(() => {
    if (id) {
      fetchConflict(id);
    }
    return () => {
      setCurrentConflict(null);
    };
  }, [id, fetchConflict, setCurrentConflict]);

  const handleDelete = async () => {
    if (!id || !confirm('¿Estás seguro de que quieres eliminar este conflicto?')) return;
    await deleteConflict(id);
    navigate('/dashboard');
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Volver al Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!currentConflict) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-gray-600">No se encontró el conflicto</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Volver al Dashboard
          </button>
        </div>
      </div>
    );
  }

  const { title, description, type, severity, status, parties, createdAt } = currentConflict;

  const severityLabels: Record<number, string> = {
    1: 'Baja',
    2: 'Media',
    3: 'Alta',
    4: 'Crítica',
  };

  const severityColors: Record<number, string> = {
    1: 'bg-green-100 text-green-800',
    2: 'bg-yellow-100 text-yellow-800',
    3: 'bg-orange-100 text-orange-800',
    4: 'bg-red-100 text-red-800',
  };

  const statusColors: Record<string, string> = {
    active: 'bg-blue-100 text-blue-800',
    pending: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    escalated: 'bg-red-100 text-red-800',
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-blue-600 hover:text-blue-800 font-medium"
        >
          ← Volver
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/conflicts/${id}/edit`)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Editar
          </button>
          <button
            onClick={handleDelete}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Eliminar
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{title}</h1>
          <div className="flex flex-wrap gap-2">
            <span className={`px-2 py-1 rounded-full text-sm font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
            <span className={`px-2 py-1 rounded-full text-sm font-medium ${severityColors[severity] || 'bg-gray-100 text-gray-800'}`}>
              {severityLabels[severity] || 'Desconocida'}
            </span>
            <span className="px-2 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </span>
          </div>
        </div>

        {/* Description */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Descripción</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{description}</p>
        </div>

        {/* Parties */}
        {parties.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Partes Involucradas</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {parties.map((party) => (
                <div key={party.id} className="bg-gray-50 rounded-lg p-4">
                  <p className="font-medium text-gray-900">{party.name}</p>
                  <p className="text-sm text-gray-600">{party.role}</p>
                  {party.contact && (
                    <p className="text-sm text-gray-500">{party.contact}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="border-t border-gray-200 pt-4">
          <p className="text-sm text-gray-500">
            Creado: {createdAt ? format(createdAt) : 'Desconocido'}
          </p>
        </div>
      </div>
    </div>
  );
}