'use client';

import { useState, useEffect, useMemo } from 'react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Loading from '@/components/ui/Loading';
import { Search, ChevronLeft, ChevronRight, Eye, XCircle, FileDown } from 'lucide-react';
import Link from 'next/link';

interface HistoryRecord {
  id: string;
  created_at: string;
  ruc: string;
  company_name: string | null;
  score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

interface DashboardStats {
  total_verifications: number;
  verifications_this_month: number;
  average_score: number;
  risk_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  recent_verifications: HistoryRecord[];
}

const getScoreBadge = (score: number): string => {
  if (score >= 80) return 'border-green-500/30 text-green-400 bg-green-500/10';
  if (score >= 60) return 'border-amber-500/30 text-amber-400 bg-amber-500/10';
  if (score >= 40) return 'border-orange-500/30 text-orange-400 bg-orange-500/10';
  return 'border-red-500/30 text-red-400 bg-red-500/10';
};

const getRiskLabel = (level: string): string => {
  const labels: Record<string, string> = {
    low: 'Bajo',
    medium: 'Medio',
    high: 'Alto',
    critical: 'Crítico'
  };
  return labels[level] || level;
};

const getRiskBadge = (level: string): string => {
  const badges: Record<string, string> = {
    low: 'border-green-500/30 text-green-400 bg-green-500/10',
    medium: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
    high: 'border-orange-500/30 text-orange-400 bg-orange-500/10',
    critical: 'border-red-500/30 text-red-400 bg-red-500/10'
  };
  return badges[level] || badges.medium;
};

export default function HistoryPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [userPlan, setUserPlan] = useState('essential');

  const itemsPerPage = 10;
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  // Cargar datos del dashboard
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // Obtener token del localStorage
        const token = localStorage.getItem('token');
        if (!token) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          setLoading(false);
          return;
        }

        // Fetch dashboard stats
        const response = await fetch(`${API_BASE}/api/v1/dashboard/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          if (response.status === 401) {
            setError('Sesión expirada. Por favor inicie sesión nuevamente.');
            localStorage.removeItem('token');
          } else {
            setError('Error al cargar el historial');
          }
          setLoading(false);
          return;
        }

        const data = await response.json();
        setStats(data);

        // Fetch user info para obtener el plan
        const userResponse = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (userResponse.ok) {
          const userData = await userResponse.json();
          setUserPlan(userData.plan_type || 'essential');
        }

        setError('');
      } catch (err) {
        console.error('Error fetching history:', err);
        setError('Error de conexión');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [API_BASE]);

  // Filtrar datos
  const filteredData = useMemo(() => {
    if (!stats?.recent_verifications) return [];

    return stats.recent_verifications
      .filter(item =>
        item.ruc.includes(searchTerm) ||
        (item.company_name?.toLowerCase() || '').includes(searchTerm.toLowerCase())
      )
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [stats?.recent_verifications, searchTerm]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleExport = () => {
    if (!filteredData.length) return;

    const csv = [
      ['Fecha', 'RUC', 'Razón Social', 'Score', 'Nivel de Riesgo'].join(','),
      ...filteredData.map(item => [
        new Date(item.created_at).toLocaleDateString('es-PE'),
        item.ruc,
        (item.company_name || '').replace(/,/g, ' '),
        item.score,
        getRiskLabel(item.risk_level)
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `historial_conflictzero_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <Link href="/login">
            <Button variant="outline">Iniciar Sesión</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Historial de Verificaciones</h2>
          <p className="text-sm text-gray-400 mt-1">
            {filteredData.length} verificación{filteredData.length !== 1 ? 'es' : ''} registrada{filteredData.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Buscar por RUC o razón social..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-10 w-72"
            />
          </div>
          <Button
            variant="outline"
            onClick={handleExport}
            disabled={!filteredData.length}
            className="flex items-center gap-2"
          >
            <FileDown className="w-4 h-4" />
            Exportar CSV
          </Button>
        </div>
      </div>

      {filteredData.length > 0 ? (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="w-full text-sm">
              <thead className="bg-gray-900/50 text-gray-400 uppercase text-xs">
                <tr>
                  <th className="px-4 py-3 text-left">Fecha</th>
                  <th className="px-4 py-3 text-left">RUC</th>
                  <th className="px-4 py-3 text-left">Razón Social</th>
                  <th className="px-4 py-3 text-center">Score</th>
                  <th className="px-4 py-3 text-center">Riesgo</th>
                  <th className="px-4 py-3 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {paginatedData.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-900/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300">
                      {new Date(item.created_at).toLocaleDateString('es-PE')}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-300">{item.ruc}</td>
                    <td className="px-4 py-3 text-gray-300">
                      {item.company_name || 'No disponible'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getScoreBadge(item.score)}`}>
                        {item.score}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRiskBadge(item.risk_level)}`}>
                        {getRiskLabel(item.risk_level)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Link
                        href={`/dashboard?ruc=${item.ruc}`}
                        className="inline-flex items-center text-red-400 hover:text-red-300 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-400">
                Mostrando {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredData.length)} de {filteredData.length}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-gray-400">
                  Página {currentPage} de {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 rounded-lg border border-gray-800">
          <p className="text-gray-400">No hay verificaciones registradas</p>
          <p className="text-sm text-gray-500 mt-1">
            Realiza una verificación desde el dashboard para verla aquí
          </p>
        </div>
      )}
    </div>
  );
}