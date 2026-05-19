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
        `