'use client';

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';
import {
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Activity,
  BarChart3,
  Clock,
  Database,
  Globe,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw
} from 'lucide-react';
import { motion } from 'framer-motion';

// Color palette - UHNW Dark Theme
const COLORS = {
  gold: '#c9a227',
  goldLight: '#e8d5a3',
  goldDark: '#9a7b1a',
  navy: '#0d1b2a',
  navyLight: '#1b263b',
  navyLighter: '#415a77',
  text: '#778da9',
  white: '#ffffff',
  success: '#16a34a',
  warning: '#f59e0b',
  danger: '#dc2626',
  info: '#3b82f6'
};

// Chart colors
const RISK_COLORS = {
  Bajo: COLORS.success,
  Moderado: COLORS.warning,
  Alto: '#f97316',
  Crítico: COLORS.danger
};

const SOURCE_COLORS = {
  'SUNAT Real': COLORS.gold,
  'SUNAT Mock': COLORS.navyLighter,
  'OSCE Scraper': COLORS.info,
  'OSCE Mock': COLORS.text
};

// Mock data - In production, this would come from an API
const generateVerificationData = () => {
  const data = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' }),
      fullDate: date.toISOString().split('T')[0],
      verificaciones: Math.floor(Math.random() * 150) + 50,
      criticas: Math.floor(Math.random() * 20),
      altas: Math.floor(Math.random() * 30),
      moderadas: Math.floor(Math.random() * 50),
      bajas: Math.floor(Math.random() * 60)
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

const topSanctionedEntities = [
  { name: 'CONSTRUCTORA ALFA', ruc: '20100101XXX', sanciones: 12, monto: 450000 },
  { name: 'IMPORTADORA BETA', ruc: '20200202XXX', sanciones: 9, monto: 320000 },
  { name: 'SERVICIOS GAMMA', ruc: '20300303XXX', sanciones: 8, monto: 280000 },
  { name: 'COMERCIAL DELTA', ruc: '20400404XXX', sanciones: 7, monto: 210000 },
  { name: 'CONSULTORA EPSILON', ruc: '20500505XXX', sanciones: 6, monto: 185000 },
  { name: 'TRANSPORTES ZETA', ruc: '20600606XXX', sanciones: 5, monto: 150000 },
  { name: 'INMOBILIARIA ETA', ruc: '20700707XXX', sanciones: 5, monto: 135000 },
  { name: 'TECNOLOGICA THETA', ruc: '20800808XXX', sanciones: 4, monto: 98000 }
];

const sourceBreakdownData = [
  { name: 'SUNAT Real', value: 485, type: 'sunat' },
  { name: 'SUNAT Mock', value: 215, type: 'sunat' },
  { name: 'OSCE Scraper', value: 342, type: 'osce' },
  { name: 'OSCE Mock', value: 158, type: 'osce' }
];

// Stats cards data
const statsCards = [
  {
    title: 'Verificaciones Hoy',
    value: '127',
    change: '+12.5%',
    trend: 'up',
    icon: Activity,
    color: COLORS.gold
  },
  {
    title: 'Riesgo Crítico',
    value: '23',
    change: '+5.2%',
    trend: 'up',
    icon: AlertTriangle,
    color: COLORS.danger
  },
  {
    title: 'Verificaciones OK',
    value: '89.2%',
    change: '+2.1%',
    trend: 'up',
    icon: ShieldCheck,
    color: COLORS.success
  },
  {
    title: 'Tiempo Promedio',
    value: '1.2s',
    change: '-0.3s',
    trend: 'down',
    icon: Clock,
    color: COLORS.info
  }
];

// Animated counter hook
function useAnimatedCounter(end: number, duration: number = 2000) {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    let startTime: number;
    let animationFrame: number;
    
    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };
    
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);
  
  return count;
}

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1b263b] border border-[#c9a227]/30 rounded-lg p-3 shadow-xl">
        <p className="text-[#e8d5a3] font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value.toLocaleString()}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Stat Card Component
function StatCard({ stat, index }: { stat: typeof statsCards[0]; index: number }) {
  const Icon = stat.icon;
  const isPositive = stat.trend === 'up' && stat.title !== 'Riesgo Crítico';
  const TrendIcon = stat.trend === 'up' ? ArrowUpRight : ArrowDownRight;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="relative overflow-hidden rounded-xl border border-[#c9a227]/15 bg-[#0d1b2a]/80 p-6 backdrop-blur-sm"
      style={{
        background: 'linear-gradient(135deg, rgba(201, 162, 39, 0.05) 0%, rgba(13, 27, 42, 0.9) 100%)'
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[#778da9]">
            {stat.title}
          </p>
          <motion.p
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
            className="mt-2 text-3xl font-bold text-white"
          >
            {stat.value}
          </motion.p>
          <div className="mt-2 flex items-center gap-1">
            <TrendIcon className={`h-4 w-4 ${isPositive ? 'text-green-500' : 'text-red-500'}`} />
            <span className={`text-sm font-medium ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
              {stat.change}
            </span>
            <span className="text-xs text-[#778da9]">vs ayer</span>
          </div>
        </div>
        <div 
          className="rounded-xl p-3"
          style={{ backgroundColor: `${stat.color}20` }}
        >
          <Icon className="h-6 w-6" style={{ color: stat.color }} />
        </div>
      </div>
      
      {/* Decorative gradient line */}
      <div 
        className="absolute bottom-0 left-0 h-0.5 w-full opacity-50"
        style={{
          background: `linear-gradient(90deg, transparent, ${stat.color}, transparent)`
        }}
      />
    </motion.div>
  );
}

export default function StatsPage() {
  const [mounted, setMounted] = useState(false);
  const [verificationData, setVerificationData] = useState(generateVerificationData());
  const [timeRange, setTimeRange] = useState('30d');
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  const handleRefresh = () => {
    setVerificationData(generateVerificationData());
  };
  
  if (!mounted) {
    return null;
  }
  
  return (
    <div className="min-h-screen bg-[#0d1b2a] text-white">
      {/* Header Section */}
      <div className="relative overflow-hidden border-b border-[#c9a227]/20 bg-gradient-to-r from-[#0d1b2a] via-[#1b263b] to-[#0d1b2a]">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNjOWEyMjciIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />
        
        <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h1 className="font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl">
                  Panel de <span className="text-[#c9a227]">Estadísticas</span>
                </h1>
                <p className="mt-2 text-[#778da9]">
                  Análisis de verificaciones y riesgos en tiempo real
                </p>
              </motion.div>
            </div>
            
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="flex items-center gap-3"
            >
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="rounded-lg border border-[#c9a227]/30 bg-[#1b263b]/80 px-4 py-2 text-sm text-white outline-none transition-all focus:border-[#c9a227] focus:ring-1 focus:ring-[#c9a227]"
              >
                <option value="7d">Últimos 7 días</option>
                <option value="30d">Últimos 30 días</option>
                <option value="90d">Últimos 90 días</option>
              </select>
              
              <button
                onClick={handleRefresh}
                className="flex items-center gap-2 rounded-lg border border-[#c9a227]/30 bg-[#1b263b]/80 px-4 py-2 text-sm text-[#c9a227] transition-all hover:bg-[#c9a227]/10"
              >
                <RefreshCw className="h-4 w-4" />
                Actualizar
              </button>
            </motion.div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Stats Cards */}
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statsCards.map((stat, index) => (
            <StatCard key={stat.title} stat={stat} index={index} />
          ))}
        </div>
        
        {/* Charts Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Verification Volume Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="rounded-xl border border-[#c9a227]/15 bg-[#0d1b2a]/60 p-6 backdrop-blur-sm lg:col-span-2"
          >
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-[#c9a227]/10 p-2">
                  <TrendingUp className="h-5 w-5 text-[#c9a227]" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Volumen de Verificaciones</h3>
                  <p className="text-xs text-[#778da9]">Últimos 30 días</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-[#c9a227]" />
                  <span className="text-[#778da9]">Total</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-[#dc2626]" />
                  <span className="text-[#778da9]">Críticas</span>
                </div>
              </div>
            </div>
            
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={verificationData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVerificaciones" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.gold} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={COLORS.gold} stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorCriticas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b263b" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="verificaciones"
                    name="Verificaciones"
                    stroke={COLORS.gold}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorVerificaciones)"
                  />
                  <Area
                    type="monotone"
                    dataKey="criticas"
                    name="Riesgo Crítico"
                    stroke={COLORS.danger}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCriticas)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
          
          {/* Risk Distribution Pie Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="rounded-xl border border-[#c9a227]/15 bg-[#0d1b2a]/60 p-6 backdrop-blur-sm"
          >
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-lg bg-[#c9a227]/10 p-2">
                <BarChart3 className="h-5 w-5 text-[#c9a227]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Distribución de Riesgo</h3>
                <p className="text-xs text-[#778da9]">Total: 985 verificaciones</p>
              </div>
            </div>
            
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {riskDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            {/* Legend */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              {riskDistributionData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-sm text-[#778da9]">{item.name}</span>
                  <span className="ml-auto text-sm font-medium text-white">{item.value}</span>
                </div>
              ))}
            </div>
          </motion.div>
          
          {/* Verification Sources */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            className="rounded-xl border border-[#c9a227]/15 bg-[#0d1b2a]/60 p-6 backdrop-blur-sm"
          >
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-lg bg-[#c9a227]/10 p-2">
                <Database className="h-5 w-5 text-[#c9a227]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Fuentes de Verificación</h3>
                <p className="text-xs text-[#778da9]">SUNAT vs OSCE</p>
              </div>
            </div>
            
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sourceBreakdownData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b263b" horizontal={true} vertical={false} />
                  <XAxis 
                    type="number" 
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    type="category" 
                    dataKey="name" 
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={90}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Verificaciones" radius={[0, 4, 4, 0]}>
                    {sourceBreakdownData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.type === 'sunat' ? COLORS.gold : COLORS.info}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            {/* Summary */}
            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-[#c9a227]/10 pt-4">
              <div className="text-center">
                <p className="text-xs text-[#778da9]">SUNAT Total</p>
                <p className="text-lg font-bold text-[#c9a227]">700</p>
                <p className="text-xs text-green-500">69.3% real</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-[#778da9]">OSCE Total</p>
                <p className="text-lg font-bold text-[#3b82f6]">500</p>
                <p className="text-xs text-green-500">68.4% scraper</p>
              </div>
            </div>
          </motion.div>
          
          {/* Top Sanctioned Entities */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.5 }}
            className="rounded-xl border border-[#c9a227]/15 bg-[#0d1b2a]/60 p-6 backdrop-blur-sm lg:col-span-2"
          >
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-red-500/10 p-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Top Entidades con Sanciones</h3>
                  <p className="text-xs text-[#778da9]">Ordenado por número de sanciones OSCE</p>
                </div>
              </div>
              <button className="text-sm text-[#c9a227] hover:text-[#e8d5a3] transition-colors">
                Ver todo →
              </button>
            </div>
            
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topSanctionedEntities} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b263b" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    height={60}
                    interval={0}
                  />
                  <YAxis 
                    yAxisId="left"
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    yAxisId="right"
                    orientation="right"
                    stroke="#415a77" 
                    tick={{ fill: '#778da9', fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `S/${(value/1000).toFixed(0)}k`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar 
                    yAxisId="left"
                    dataKey="sanciones" 
                    name="Sanciones" 
                    fill={COLORS.danger}
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar 
                    yAxisId="right"
                    dataKey="monto" 
                    name="Monto Total (S/)" 
                    fill={COLORS.warning}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            {/* Table View */}
            <div className="mt-6 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#c9a227]/10">
                    <th className="pb-3 text-left font-medium text-[#778da9]">Entidad</th>
                    <th className="pb-3 text-left font-medium text-[#778da9]">RUC</th>
                    <th className="pb-3 text-right font-medium text-[#778da9]">Sanciones</th>
                    <th className="pb-3 text-right font-medium text-[#778da9]">Monto Total</th>
                  </tr>
                </thead>
                <tbody>
                  {topSanctionedEntities.slice(0, 5).map((entity, index) => (
                    <tr key={entity.ruc} className="border-b border-[#1b263b] last:border-0">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#1b263b] text-xs font-medium text-[#c9a227]">
                            {index + 1}
                          </span>
                          <span className="font-medium text-white">{entity.name}</span>
                        </div>
                      </td>
                      <td className="py-3 text-[#778da9]">{entity.ruc}</td>
                      <td className="py-3 text-right">
                        <span className="rounded-full bg-red-500/10 px-2 py-1 text-xs font-medium text-red-400">
                          {entity.sanciones}
                        </span>
                      </td>
                      <td className="py-3 text-right font-medium text-[#c9a227]">
                        S/ {entity.monto.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        </div>
        
        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="mt-8 border-t border-[#c9a227]/10 pt-6 text-center text-sm text-[#778da9]"
        >
          <div className="flex items-center justify-center gap-6">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span>Conflict Zero Analytics</span>
            </div>
            <span className="text-[#415a77]">|</span>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-[#c9a227]" />
              <span>Datos actualizados: {new Date().toLocaleString('es-PE')}</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
