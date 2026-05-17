'use client';

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import { TrendingUp, Activity, Clock, Database, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import Loading from '@/components/ui/Loading';

// UHNW Color Palette
const COLORS = {
  gold: '#c9a050',
  goldLight: '#d4aa5a',
  goldDark: '#9a7b1a',
  black: '#0a0a0a',
  gray900: '#1a1a1a',
  gray800: '#2a2a2a',
  gray600: '#5a5a5a',
  gray400: '#8a8a8a',
  text: '#b0b0b0',
  white: '#e8e6e3',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444'
};

const RISK_COLORS = {
  low: COLORS.success,
  medium: COLORS.warning,
  high: '#f97316',
  critical: COLORS.danger
};

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
  recent_verifications: Array<{
    id: string;
    created_at: string;
    ruc: string;
    company_name: string | null;
    score: number;
    risk_level: 'low' | 'medium' | 'high' | 'critical';
  }>;
}

// Custom Tooltip para charts oscuros
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] p-3">
        <p className="text-[#8a8a8a] text-xs mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function StatsPage() {
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [verificationHistory, setVerificationHistory] = useState<any[]>([]);
  
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  useEffect(() => {
    setMounted(true);
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
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
          setError('Error al cargar las estadísticas');
        }
        setLoading(false);
        return;
      }

      const data = await response.json();
      setStats(data);

      // Generar datos de historial para el gráfico (últimos 30 días)
      const historyData = generateHistoryData(data.recent_verifications || []);
      setVerificationHistory(historyData);

      setError('');
    } catch (err) {
      console.error('Error fetching stats:', err);
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const generateHistoryData = (verifications: DashboardStats['recent_verifications']) => {
    const data = [];
    const today = new Date();
    
    // Crear mapa de verificaciones por día
    const verificationsByDay: Record<string, number> = {};
    verifications.forEach(v => {
      const date = new Date(v.created_at).toLocaleDateString('es-PE', { day: '2-digit', month: 'short' });
      verificationsByDay[date] = (verificationsByDay[date] || 0) + 1;
    });
    
    // Generar últimos 30 días
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' });
      data.push({
        date: dateStr,
        verificaciones: verificationsByDay[dateStr] || 0,
      });
    }
    return data;
  };

  // Preparar datos para el pie chart
  const riskDistributionData = stats ? [
    { name: 'Bajo', value: stats.risk_distribution.low, color: COLORS.success },
    { name: 'Medio', value: stats.risk_distribution.medium, color: COLORS.warning },
    { name: 'Alto', value: stats.risk_distribution.high, color: '#f97316' },
    { name: 'Crítico', value: stats.risk_distribution.critical, color: COLORS.danger }
  ].filter(item => item.value > 0) : [];

  // Calcular estadísticas
  const calculateChange = (current: number, previous: number) => {
    if (previous === 0) return current > 0 ? '+100%' : '0%';
    const change = ((current - previous) / previous) * 100;
    return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`;
  };

  const statCards = stats ? [
    { 
      label: 'Verificaciones Total', 
      value: stats.total_verifications.toLocaleString(), 
      change: calculateChange(stats.verifications_this_month, stats.total_verifications - stats.verifications_this_month), 
      trend: stats.verifications_this_month > (stats.total_verifications - stats.verifications_this_month) ? 'up' : 'down',
      icon: Activity 
    },
    { 
      label: 'Score Promedio', 
      value: stats.average_score.toFixed(1), 
      change: stats.average_score >= 70 ? 'Bueno' : stats.average_score >= 50 ? 'Regular' : 'Riesgoso', 
      trend: stats.average_score >= 60 ? 'up' : 'down',
      icon: TrendingUp 
    },
    { 
      label: 'Este Mes', 
      value: stats.verifications_this_month.toString(), 
      change: calculateChange(stats.verifications_this_month, Math.max(1, Math.floor(stats.verifications_this_month * 0.8))), 
      trend: 'up',
      icon: Clock 
    },
    { 
      label: 'Riesgo Alto/Crítico', 
      value: (stats.risk_distribution.high + stats.risk_distribution.critical).toString(), 
      change: `${((stats.risk_distribution.high + stats.risk_distribution.critical) / Math.max(1, stats.total_verifications) * 100).toFixed(0)}% del total`, 
      trend: (stats.risk_distribution.high + stats.risk_distribution.critical) > stats.risk_distribution.low ? 'down' : 'up',
      icon: Database 
    },
  ] : [];

  if (loading) {
    return <Loading fullScreen message="Cargando estadísticas..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchStats}
            className="px-4 py-2 bg-[#c9a050] text-[#0a0a0a] text-sm hover:bg-[#d4aa5a] transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Analytics</p>
          <h1 className="text-3xl font-light">Estadísticas</h1>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#1a1a1a] mb-8">
          {statCards.map((stat) => (
            <div key={stat.label} className="bg-[#0a0a0a] p-6">
              <div className="flex items-center justify-between mb-4">
                <stat.icon className="h-5 w-5 text-[#c9a050]" strokeWidth={1.5} />
                <span className={`text-xs flex items-center gap-1 ${
                  stat.trend === 'up' ? 'text-green-500' : 'text-[#c9a050]'
                }`}>
                  {stat.trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                  {stat.change}
                </span>
              </div>
              <p className="text-3xl font-light text-[#e8e6e3] mb-1">{stat.value}</p>
              <p className="text-xs text-[#5a5a5a] tracking-wide">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid md:grid-cols-3 gap-8">
          {/* Line Chart */}
          <div className="md:col-span-2 border border-[#1a1a1a] p-6">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Verificaciones (30 días)</p>
            {mounted && verificationHistory.length > 0 && (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={verificationHistory}>
                  <defs>
                    <linearGradient id="colorVerif" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.gold} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={COLORS.gold} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                  <XAxis dataKey="date" stroke="#5a5a5a" tick={{ fill: '#5a5a5a', fontSize: 10 }} />
                  <YAxis stroke="#5a5a5a" tick={{ fill: '#5a5a5a', fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area 
                    type="monotone" 
                    dataKey="verificaciones" 
                    stroke={COLORS.gold} 
                    fillOpacity={1} 
                    fill="url(#colorVerif)" 
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
            {verificationHistory.length === 0 && (
              <div className="h-[250px] flex items-center justify-center text-[#5a5a5a]">
                No hay datos suficientes para mostrar el gráfico
              </div>
            )}
          </div>

          {/* Pie Chart */}
          <div className="border border-[#1a1a1a] p-6">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Distribución de Riesgo</p>
            {mounted && riskDistributionData.length > 0 && (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={riskDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {riskDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
            {riskDistributionData.length === 0 && (
              <div className="h-[250px] flex items-center justify-center text-[#5a5a5a]">
                No hay datos suficientes
              </div>
            )}
            <div className="flex flex-wrap gap-4 justify-center mt-4">
              {riskDistributionData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div 
                    className="w-2 h-2" 
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-[#5a5a5a]">{item.name}: {item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Verifications Table */}
        {stats && stats.recent_verifications.length > 0 && (
          <div className="mt-8 border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Verificaciones Recientes</p>
            </div>
            <div className="divide-y divide-[#1a1a1a]">
              {stats.recent_verifications.slice(0, 5).map((v) => (
                <div key={v.id} className="p-4 flex items-center justify-between hover:bg-[#0d0d0d]">
                  <div>
                    <p className="text-sm text-[#e8e6e3]">{v.ruc}</p>
                    <p className="text-xs text-[#5a5a5a]">{v.company_name || 'Sin nombre'}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-2 py-1 text-xs border ${
                      v.score >= 80 ? 'border-green-500/30 text-green-400' :
                      v.score >= 60 ? 'border-amber-500/30 text-amber-400' :
                      v.score >= 40 ? 'border-orange-500/30 text-orange-400' :
                      'border-red-500/30 text-red-400'
                    }`}>
                      {v.score}
                    </span>
                    <span className="text-xs text-[#5a5a5a] uppercase">{v.risk_level}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
