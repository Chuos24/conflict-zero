import { useEffect } from 'react';
import { Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ConflictList } from '../components/ConflictList';
import { useConflictStore } from '../stores/conflictStore';

export function Dashboard() {
  const { stats, fetchStats } = useConflictStore();

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const statCards = [
    { label: 'Total Conflicts', value: stats?.total || 0, color: 'bg-blue-500' },
    { label: 'Active', value: stats?.byStatus?.active || 0, color: 'bg-yellow-500' },
    { label: 'Resolved', value: stats?.byStatus?.resolved || 0, color: 'bg-green-500' },
    { label: 'Critical', value: stats?.bySeverity?.critical || 0, color: 'bg-red-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conflict Dashboard</h1>
          <p className="text-gray-500 mt-1">Manage and track all conflicts in one place</p>
        </div>
        <Link
          to="/conflicts/new"
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Conflict
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className={`w-12 h-12 rounded-lg ${stat.color} bg-opacity-10 flex items-center justify-center`}>
                <div className={`w-3 h-3 rounded-full ${stat.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Conflict List */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Conflicts</h2>
        <ConflictList />
      </div>
    </div>
  );
}
