import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, CheckCircle, ArrowUpRight } from 'lucide-react';
import { useConflictStore } from '../stores/conflictStore';
import { StatusBadge, SeverityBadge } from './Badges';
import { Conflict, ConflictStatus } from '../types';

export function ConflictList() {
  const navigate = useNavigate();
  const { conflicts, loading, fetchConflicts } = useConflictStore();

  useEffect(() => {
    fetchConflicts();
  }, [fetchConflicts]);

  if (loading && conflicts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const getStatusIcon = (status: ConflictStatus) => {
    switch (status) {
      case ConflictStatus.ACTIVE:
        return <AlertTriangle className="w-4 h-4 text-blue-500" />;
      case ConflictStatus.PENDING:
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case ConflictStatus.RESOLVED:
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {conflicts.map((conflict: Conflict) => (
              <tr
                key={conflict.id}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => navigate(`/conflicts/${conflict.id}`)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    {getStatusIcon(conflict.status)}
                    <div className="ml-3">
                      <div className="text-sm font-medium text-gray-900">
                        {conflict.title}
                      </div>
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {conflict.description}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={conflict.status} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <SeverityBadge severity={conflict.severity} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900 capitalize">
                    {conflict.type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-500">
                    {new Date(conflict.createdAt).toLocaleDateString()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/conflicts/${conflict.id}`);
                    }}
                    className="text-primary-600 hover:text-primary-900"
                  >
                    <ArrowUpRight className="w-5 h-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {conflicts.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No conflicts found. Create your first one!
        </div>
      )}
    </div>
  );
}
