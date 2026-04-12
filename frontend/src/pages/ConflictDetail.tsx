import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useConflictStore } from '../stores/conflictStore';
import { ConflictType, SeverityLevel, ConflictStatus } from '../types';
import type { CreateConflictData, UpdateConflictData } from '../types/forms';

interface FormData {
  title: string;
  description: string;
  type: ConflictType;
  severity: SeverityLevel;
  status: ConflictStatus;
  parties: { name: string; role: string; contact: string }[];
}

const initialFormData: FormData = {
  title: '',
  description: '',
  type: ConflictType.INTERPERSONAL,
  severity: SeverityLevel.MEDIUM,
  status: ConflictStatus.ACTIVE,
  parties: [{ name: '', role: '', contact: '' }],
};

export function ConflictForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentConflict, loading, fetchConflict, createConflict, updateConflict, setCurrentConflict } = useConflictStore();
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const isEditing = Boolean(id);

  useEffect(() => {
    if (id) {
      fetchConflict(id);
    } else {
      setCurrentConflict(null);
      setFormData(initialFormData);
    }
  }, [id, fetchConflict, setCurrentConflict]);

  useEffect(() => {
    if (currentConflict && isEditing) {
      setFormData({
        title: currentConflict.title,
        description: currentConflict.description,
        type: currentConflict.type,
        severity: currentConflict.severity,
        status: currentConflict.status,
        parties: currentConflict.parties.map((p) => ({
          name: p.name,
          role: p.role,
          contact: p.contact || '',
        })),
      });
    }
  }, [currentConflict, isEditing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const data: CreateConflictData | UpdateConflictData = {
      ...formData,
      parties: formData.parties.filter((p) => p.name.trim() !== ''),
    };

    if (isEditing && id) {
      await updateConflict(id, data as UpdateConflictData);
      navigate(`/conflicts/${id}`);
    } else {
      await createConflict(data as CreateConflictData);
      navigate('/dashboard');
    }
  };

  const addParty = () => {
    setFormData({
      ...formData,
      parties: [...formData.parties, { name: '', role: '', contact: '' }],
    });
  };

  const removeParty = (index: number) => {
    setFormData({
      ...formData,
      parties: formData.parties.filter((_, i) => i !== index),
    });
  };

  const updateParty = (index: number, field: keyof FormData['parties'][0], value: string) => {
    const newParties = [...formData.parties];
    newParties[index] = { ...newParties[index], [field]: value };
    setFormData({ ...formData, parties: newParties });
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        {isEditing ? 'Edit Conflict' : 'New Conflict'}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Basic Information</h2>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter conflict title"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description *
            </label>
            <textarea
              required
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Describe the conflict..."
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type *
              </label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value as ConflictType })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {Object.values(ConflictType).map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Severity *
              </label>
              <select
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: Number(e.target.value) as SeverityLevel })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value={SeverityLevel.LOW}>Low</option>
                <option value={SeverityLevel.MEDIUM}>Medium</option>
                <option value={SeverityLevel.HIGH}>High</option>
                <option value={SeverityLevel.CRITICAL}>Critical</option>
              </select>
            </div>

            {isEditing && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status *
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as ConflictStatus })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value={ConflictStatus.ACTIVE}>Active</option>
                  <option value={ConflictStatus.PENDING}>Pending</option>
                  <option value={ConflictStatus.RESOLVED}>Resolved</option>
                  <option value={ConflictStatus.ESCALATED}>Escalated</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Parties */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Involved Parties</h2>
            <button
              type="button"
              onClick={addParty}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              + Add Party
            </button>
          </div>

          {formData.parties.map((party, index) => (
            <div key={index} className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
                <input
                  type="text"
                  value={party.name}
                  onChange={(e) => updateParty(index, 'name', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Role</label>
                <input
                  type="text"
                  value={party.role}
                  onChange={(e) => updateParty(index, 'role', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  placeholder="e.g., Plaintiff, Defendant"
                />
              </div>
              <div className="flex space-x-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-500 mb-1">Contact</label>
                  <input
                    type="text"
                    value={party.contact}
                    onChange={(e) => updateParty(index, 'contact', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    placeholder="Email or phone"
                  />
                </div>
                {formData.parties.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeParty(index)}
                    className="self-end px-3 py-2 text-red-600 hover:bg-red-50 rounded-md text-sm"
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : isEditing ? 'Update Conflict' : 'Create Conflict'}
          </button>
        </div>
      </form>
    </div>
  );
}
