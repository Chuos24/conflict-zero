'use client';

import { useState, useMemo, useEffect } from 'react';
import { 
  Search, 
  Download, 
  ChevronLeft, 
  ChevronRight, 
  Eye, 
  Filter,
  Calendar,
  AlertTriangle,
  CheckCircle,
  XCircle,
  X,
  FileDown,
  Trash2
} from 'lucide-react';

// Types
interface HistoryRecord {
  id: string;
  fecha: Date;
  ruc: string;
  razonSocial: string;
  score: number;
  estado: 'low' | 'medium' | 'high' | 'critical';
  sunatDebt: number;
  osceSanctions: number;
  mlAnomalyScore: number;
}

// Mock data generator
const generateMockData = (count: number): HistoryRecord[] => {
  const companyNames = [
    'Constructora Líder S.A.C.', 'Inversiones del Norte S.R.L.', 'Comercial Andina E.I.R.L.',
    'Minera Aurora Perú S.A.', 'Transportes del Sur S.A.C.', 'Agroindustrial San Miguel S.A.A.',
    'Textiles Modernos S.R.L.', 'Química Industrial del Perú S.A.', 'Alimentos Premium S.A.C.',
    'Tecnología Avanzada S.R.L.', 'Servicios Logísticos Integrados S.A.C.', 'Energía Verde del Perú S.A.',
    'Bienes Raíces Metropolitano S.A.C.', 'Salud y Bienestar S.R.L.', 'Educación Superior S.A.C.',
    'Consultoría Estratégica S.A.', 'Hoteles y Turismo del Sur S.A.C.', 'Manufacturas del Pacífico S.A.',
    'Comunicaciones Digitales S.R.L.', 'Seguridad Integral S.A.C.', 'Financiera del Norte E.D.P.Y.M.E.',
    'Recursos Hídricos S.A.C.', 'Medio Ambiente Sostenible S.R.L.', 'Infraestructura Urbana S.A.',
    'Exportadora de Café S.A.C.', 'Pesca Responsable S.A.', 'Software Factory Perú S.R.L.',
    'Automotriz Nacional S.A.C.', 'Farmacéutica Andina S.A.', 'Bebidas Refrescantes S.A.C.',
    'Electrodomésticos del Hogar S.R.L.', 'Moda Urbana Perú S.A.C.', 'Construcciones Metálicas S.A.',
    'Productos Orgánicos S.R.L.', 'Cementos Andinos S.A.', 'Acero Industrial S.A.C.',
    'Plásticos del Futuro S.R.L.', 'Maderas Tropicales S.A.', 'Papel y Cartón S.A.C.',
    'Vidrios Templados S.R.L.', 'Cerámicas del Valle S.A.C.', 'Equipos Médicos S.A.',
    'Instrumentos de Precisión S.R.L.', 'Robótica Industrial S.A.C.', 'Inteligencia Artificial Perú S.A.',
    'Ciberseguridad Avanzada S.R.L.', 'Nube Digital S.A.C.', 'Datos Analíticos S.A.',
    'Blockchain Solutions S.R.L.', 'IoT Smart Systems S.A.C.'
  ];

  const rucPrefixes = ['20', '10', '15'];
  const estados: ('low' | 'medium' | 'high' | 'critical')[] = ['low', 'medium', 'high', 'critical'];
  
  return Array.from({ length: count }, (_, i) => {
    const estado = estados[Math.floor(Math.random() * estados.length)];
    let baseScore = 50;
    
    switch (estado) {
      case 'low': baseScore = 75 + Math.random() * 25; break;
      case 'medium': baseScore = 50 + Math.random() * 25; break;
      case 'high': baseScore = 25 + Math.random() * 25; break;
      case 'critical': baseScore = Math.random() * 25; break;
    }
    
    const fecha = new Date();
    fecha.setDate(fecha.getDate() - Math.floor(Math.random() * 90));
    
    return {
      id: `hist-${i + 1}`,
      fecha,
      ruc: `${rucPrefixes[Math.floor(Math.random() * rucPrefixes.length)]}${String(Math.floor(Math.random() * 99999999)).padStart(8, '0')}`,
      razonSocial: companyNames[i % companyNames.length] + (i >= companyNames.length ? ` ${Math.floor(i / companyNames.length) + 1}` : ''),
      score: Math.round(baseScore),
      estado,
      sunatDebt: Math.random() > 0.7 ? Math.floor(Math.random() * 1000000) : 0,
      osceSanctions: Math.random() > 0.8 ? Math.floor(Math.random() * 5) : 0,
      mlAnomalyScore: Math.round(Math.random() * 100),
    };
  });
};

// Helper functions
const getScoreColor = (score: number): string => {
  if (score >= 80) return 'text-emerald-400';
  if (score >= 60) return 'text-amber-400';
  if (score >= 40) return 'text-orange-500';
  return 'text-rose-500';
};

const getScoreBg = (score: number): string => {
  if (score >= 80) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
  if (score >= 60) return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  if (score >= 40) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
  return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
};

const getRiskLabel = (level: string) => {
  const labels: Record<string, { text: string; icon: typeof CheckCircle; color: string }> = {
    low: { text: 'Riesgo Bajo', icon: CheckCircle, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
    medium: { text: 'Riesgo Moderado', icon: AlertTriangle, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    high: { text: 'Riesgo Alto', icon: AlertTriangle, color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
    critical: { text: 'Riesgo Crítico', icon: XCircle, color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' }
  };
  return labels[level] || { text: level, icon: AlertTriangle, color: 'text-slate-400 bg-slate-500/10 border-slate-500/20' };
};

const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
    minimumFractionDigits: 0
  }).format(amount);
};

// CSV Export function
const exportToCSV = (records: HistoryRecord[]): string => {
  const headers = ['Fecha', 'RUC', 'Razón Social', 'Score', 'Estado', 'Deuda SUNAT', 'Sanciones OSCE'];
  const rows = records.map(r => [
    formatDate(r.fecha),
    r.ruc,
    r.razonSocial,
    r.score,
    getRiskLabel(r.estado).text,
    r.sunatDebt,
    r.osceSanctions
  ]);
  
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');
  
  return csvContent;
};

// Modal Component
interface DetailModalProps {
  record: HistoryRecord | null;
  isOpen: boolean;
  onClose: () => void;
}

const DetailModal = ({ record, isOpen, onClose }: DetailModalProps) => {
  if (!isOpen || !record) return null;

  const risk = getRiskLabel(record.estado);
  const RiskIcon = risk.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <h2 className="text-xl font-semibold text-white">Detalle de Consulta</h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Company Info */}
          <div className="space-y-2">
            <p className="text-sm text-slate-400">{record.ruc}</p>
            <h3 className="text-2xl font-bold text-white">{record.razonSocial}</h3>
            <div className="flex items-center gap-3 pt-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border ${risk.color}`}>
                <RiskIcon className="h-4 w-4" />
                {risk.text}
              </span>
              <span className="text-sm text-slate-500">
                {formatDate(record.fecha)}
              </span>
            </div>
          </div>

          {/* Score Display */}
          <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Score de Riesgo</p>
                <div className={`text-5xl font-bold ${getScoreColor(record.score)}`}>
                  {record.score}
                </div>
              </div>
              <div className="text-right">
                <div className="w-32 h-3 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      record.score >= 80 ? 'bg-emerald-500' :
                      record.score >= 60 ? 'bg-amber-500' :
                      record.score >= 40 ? 'bg-orange-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${record.score}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  {record.score >= 80 ? 'Excelente' :
                   record.score >= 60 ? 'Aceptable' :
                   record.score >= 40 ? 'Precaución' : 'Alto riesgo'}
                </p>
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/50">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Deuda SUNAT</p>
              <p className={`text-lg font-semibold ${record.sunatDebt > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {formatCurrency(record.sunatDebt)}
              </p>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/50">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Sanciones OSCE</p>
              <p className={`text-lg font-semibold ${record.osceSanctions > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {record.osceSanctions} {record.osceSanctions === 1 ? 'sanción' : 'sanciones'}
              </p>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/50">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Score ML</p>
              <p className="text-lg font-semibold text-purple-400">
                {record.mlAnomalyScore}%
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-slate-800 bg-slate-900/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Cerrar
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2">
            <FileDown className="h-4 w-4" />
            Descargar PDF
          </button>
        </div>
      </div>
    </div>
  );
};

// Main Component
export default function HistoryPage() {
  // State
  const [records] = useState<HistoryRecord[]>(() => generateMockData(75));
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [detailRecord, setDetailRecord] = useState<HistoryRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filter records
  const filteredRecords = useMemo(() => {
    return records.filter(record => {
      // Search filter
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch = 
        record.ruc.toLowerCase().includes(searchLower) ||
        record.razonSocial.toLowerCase().includes(searchLower);
      
      // Risk filter
      const matchesRisk = riskFilter === 'all' || record.estado === riskFilter;
      
      // Date filter
      const recordDate = new Date(record.fecha);
      const fromDate = dateFrom ? new Date(dateFrom) : null;
      const toDate = dateTo ? new Date(dateTo) : null;
      
      const matchesDateFrom = !fromDate || recordDate >= fromDate;
      const matchesDateTo = !toDate || recordDate <= new Date(toDate.setHours(23, 59, 59));
      
      return matchesSearch && matchesRisk && matchesDateFrom && matchesDateTo;
    });
  }, [records, searchQuery, riskFilter, dateFrom, dateTo]);

  // Pagination
  const totalPages = Math.ceil(filteredRecords.length / itemsPerPage);
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredRecords.slice(start, start + itemsPerPage);
  }, [filteredRecords, currentPage, itemsPerPage]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, riskFilter, dateFrom, dateTo, itemsPerPage]);

  // Handle row selection
  const toggleRowSelection = (id: string) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedRows(newSelected);
  };

  const toggleAllSelection = () => {
    if (selectedRows.size === paginatedRecords.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(paginatedRecords.map(r => r.id)));
    }
  };

  // Handle export
  const handleExport = () => {
    const recordsToExport = selectedRows.size > 0
      ? records.filter(r => selectedRows.has(r.id))
      : filteredRecords;
    
    const csv = exportToCSV(recordsToExport);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `historial-consultas-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Handle row click
  const handleRowClick = (record: HistoryRecord) => {
    setDetailRecord(record);
    setIsModalOpen(true);
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setRiskFilter('all');
    setDateFrom('');
    setDateTo('');
    setSelectedRows(new Set());
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Historial de Consultas</h1>
          <p className="text-slate-400">Visualiza y exporta el historial de verificaciones realizadas</p>
        </div>
        <div className="flex items-center gap-3">
          {selectedRows.size > 0 && (
            <button
              onClick={() => setSelectedRows(new Set())}
              className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              Limpiar selección ({selectedRows.size})
            </button>
          )}
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Exportar {selectedRows.size > 0 ? `(${selectedRows.size})` : 'Todo'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Buscar por RUC o Razón Social..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
            />
          </div>

          {/* Risk Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 min-w-[160px]"
          >
            <option value="all">Todos los riesgos</option>
            <option value="low">Riesgo Bajo</option>
            <option value="medium">Riesgo Moderado</option>
            <option value="high">Riesgo Alto</option>
            <option value="critical">Riesgo Crítico</option>
          </select>

          {/* Toggle Filters */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2.5 border rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
              showFilters 
                ? 'bg-blue-600/20 border-blue-500/50 text-blue-400' 
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Filter className="h-4 w-4" />
            Filtros
          </button>
        </div>

        {/* Date Range Filters */}
        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-2 flex-1">
              <Calendar className="h-4 w-4 text-slate-500" />
              <span className="text-sm text-slate-400">Desde:</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>
            <div className="flex items-center gap-2 flex-1">
              <Calendar className="h-4 w-4 text-slate-500" />
              <span className="text-sm text-slate-400">Hasta:</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>
            <button
              onClick={clearFilters}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-slate-400">
        <p>
          Mostrando <span className="text-white font-medium">{paginatedRecords.length}</span> de{' '}
          <span className="text-white font-medium">{filteredRecords.length}</span> registros
          {selectedRows.size > 0 && (
            <span className="ml-2 text-blue-400">({selectedRows.size} seleccionados)</span>
          )}
        </p>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-800/50">
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={paginatedRecords.length > 0 && selectedRows.size === paginatedRecords.length}
                    onChange={toggleAllSelection}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500/50 focus:ring-offset-slate-900"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Fecha
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  RUC
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Razón Social
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {paginatedRecords.map((record) => {
                const risk = getRiskLabel(record.estado);
                const isSelected = selectedRows.has(record.id);

                return (
                  <tr
                    key={record.id}
                    onClick={() => handleRowClick(record)}
                    className={`group cursor-pointer transition-colors ${
                      isSelected ? 'bg-blue-500/10' : 'hover:bg-slate-800/50'
                    }`}
                  >
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleRowSelection(record.id)}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500/50 focus:ring-offset-slate-900"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300 whitespace-nowrap">
                      {formatDate(record.fecha)}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-white whitespace-nowrap">
                      {record.ruc}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300 max-w-[300px] truncate">
                      {record.razonSocial}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center">
                        <span className={`inline-flex items-center justify-center w-12 h-8 rounded-lg text-sm font-bold border ${getScoreBg(record.score)}`}>
                          {record.score}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${risk.color}`}>
                        <risk.icon className="h-3.5 w-3.5" />
                        {risk.text}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center">
                        <button
                          className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                          title="Ver detalles"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {paginatedRecords.length === 0 && (
          <div className="py-16 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-800 rounded-full flex items-center justify-center">
              <Search className="h-8 w-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No se encontraron registros</h3>
            <p className="text-slate-400">Intenta ajustar tus filtros de búsqueda</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Items per page */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Mostrar:</span>
          <select
            value={itemsPerPage}
            onChange={(e) => setItemsPerPage(Number(e.target.value))}
            className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <span className="text-sm text-slate-400">por página</span>
        </div>

        {/* Page navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>

          {/* Page numbers */}
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {/* Page info */}
        <div className="text-sm text-slate-400">
          Página <span className="text-white font-medium">{currentPage}</span> de{' '}
          <span className="text-white font-medium">{totalPages}</span>
        </div>
      </div>

      {/* Detail Modal */}
      <DetailModal
        record={detailRecord}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
