'use client';

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import { TrendingUp, Activity, Clock, Database, ArrowUpRight, ArrowDownRight } from 'lucide-react';

// UHNW Color Palette - Negro y Dorado
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
  Bajo: COLORS.success,
  Moderado: COLORS.warning,
  Alto: '#f97316',
  Crítico: COLORS.danger
};

// Mock data
const generateVerificationData = () => {
  const data = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' }),
      verificaciones: Math.floor(Math.random() * 50) + 10,
      criticas: Math.floor(Math.random() * 5),
    });
  }
  return data;
};

const riskDistributionData = [
  { name: 'Bajo', value: 428, color: COLORS.success },
  { name: 'Moderado', value: 312, color: COLORS.warning },
  { name: 'Alto', value: 156, color: '#f97316' },
  { name: 'Crítico', value: 89, color: COLORS.danger }
];

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
  const [verificationData, setVerificationData] = useState<any[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setVerificationData(generateVerificationData());
  }, []);

  const stats = [
    { 
      label: 'Verificaciones Mes', 
      value: '1,247', 
      change: '+12%', 
      trend: 'up',
      icon: Activity 
    },
    { 
      label: 'Riesgo Promedio', 
      value: '72.4', 
      change: '-3%', 
      trend: 'down',
      icon: TrendingUp 
    },
    { 
      label: 'Tiempo Promedio', 
      value: '2.3s', 
      change: '-15%', 
      trend: 'down',
      icon: Clock 
    },
    { 
      label: 'Datos Consultados', 
      value: '3.2K', 
      change: '+8%', 
      trend: 'up',
      icon: Database 
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Analytics</p>
          <h1 className="text-3xl font-light">Estadísticas</h1>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#1a1a1a] mb-8">
          {stats.map((stat) => (
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
            {mounted && (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={verificationData}>
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
          </div>

          {/* Pie Chart */}
          <div className="border border-[#1a1a1a] p-6">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Distribución de Riesgo</p>
            {mounted && (
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
            <div className="flex flex-wrap gap-4 justify-center mt-4">
              {riskDistributionData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div 
                    className="w-2 h-2" 
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-[#5a5a5a]">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
