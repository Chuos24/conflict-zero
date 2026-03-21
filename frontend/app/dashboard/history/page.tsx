'use client';

import { useState, useMemo } from 'react';
import { Search, Download, ChevronLeft, ChevronRight, Eye, Calendar, XCircle, FileDown } from 'lucide-react';
import Link from 'next/link';

interface HistoryRecord {
  id: string;
  fecha: Date;
  ruc: string;
  razonSocial: string;
  score: number;
  estado: 'low' | 'medium' | 'high' | 'critical';
}

// Mock data - Essential: 90 días, Professional: ilimitado, Enterprise: ilimitado
const generateMockData = (count: number): HistoryRecord[] => {
  const companyNames = [
    'Constructora Líder S.A.C.', 'Inversiones del Norte S.R.L.', 'Comercial Andina E.I.R.L.',
    'Minera Aurora Perú S.A.', 'Transportes del Sur S.A.C.', 'Agroindustrial San Miguel S.A.A.',
    'Textiles Modernos S.R.L.', 'Química Industrial del Perú S.A.', 'Alimentos Premium S.A.C.',
  ];
  
  return Array.from({ length: count }, (_, i) => {
    const estados: ('low' | 'medium' | 'high' | 'critical')[] = ['low', 'medium', 'high', 'critical'];
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
      ruc: `20${String(Math.floor(Math.random() * 99999999)).padStart(8, '0')}`,
      razonSocial: companyNames[i % companyNames.length],
      score: Math.round(baseScore),
      estado,
    };
  });
};

const getScoreBadge = (score: number): string => {
  if (score >= 80) return 'border-green-500/30 text-green-400 bg-green-500/10';
  if (score >= 60) return 'border-amber-500/30 text-amber-400 bg-amber-500/10';
  if (score >= 40) return 'border-orange-500/30 text-orange-400 bg-orange-500/10';
  return 'border-red-500/30 text-red-400 bg-red-500/10';
};

export default function HistoryPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // PLAN LIMITATIONS - Essential: últimos 90 días, Prof/Ent: ilimitado
  const userPlan = 'essential'; // Esto vendría del backend
  const maxDays = userPlan === 'essential' ? 90 : 3650;
  
  const allData = useMemo(() => generateMockData(50), []);
  
  const filteredData = useMemo(() => {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - maxDays);
    
    return allData
      .filter(item => item.fecha >= cutoffDate)
      .filter(item => 
        item.ruc.includes(searchTerm) ||
        item.razonSocial.toLowerCase().includes(searchTerm.toLowerCase())
      )
      .sort((a, b) => b.fecha.getTime() - a.fecha.getTime());
  }, [allData, searchTerm, maxDays]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div>
            <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Registro</p>
            <h1 className="text-3xl font-light">Historial de Consultas</h1>
          </div>
          <button className="flex items-center gap-2 text-xs tracking-wide text-[#8a8a8a] hover:text-[#c9a050] transition-colors border border-[#2a2a2a] px-4 py-2">
            <FileDown className="h-4 w-4" />
            Exportar CSV
          </button>
        </div>

        {/* Search */}
        <div className="border border-[#1a1a1a] p-6 mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-[#5a5a5a]" />
            <input
              type="text"
              placeholder="Buscar por RUC o razón social..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              className="w-full bg-transparent border border-[#2a2a2a] pl-12 pr-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
            />
          </div>
          
          {userPlan === 'essential' && (
            <p className="text-xs text-[#5a5a5a] mt-3">
              Plan Essential: Mostrando últimos 90 días.{' '}
              <Link href="/pricing" className="text-[#c9a050] hover:underline">Upgrade</Link>
            </p>
          )}
        </div>

        {/* Table */}
        <div className="border border-[#1a1a1a]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#1a1a1a]">
                <th className="text-left p-4 text-xs tracking-[0.2em] uppercase text-[#8a8a8a] font-normal">Fecha</th>
                <th className="text-left p-4 text-xs tracking-[0.2em] uppercase text-[#8a8a8a] font-normal">RUC</th>
                <th className="text-left p-4 text-xs tracking-[0.2em] uppercase text-[#8a8a8a] font-normal">Razón Social</th>
                <th className="text-center p-4 text-xs tracking-[0.2em] uppercase text-[#8a8a8a] font-normal">Score</th>
                <th className="text-center p-4 text-xs tracking-[0.2em] uppercase text-[#8a8a8a] font-normal">Acción</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((item) => (
                <tr key={item.id} className="border-b border-[#1a1a1a] hover:bg-[#0d0d0d]">
                  <td className="p-4 text-sm text-[#8a8a8a]">
                    {item.fecha.toLocaleDateString('es-PE')}
                  </td>
                  <td className="p-4 text-sm font-mono">{item.ruc}</td>
                  <td className="p-4 text-sm">{item.razonSocial}</td>
                  <td className="p-4 text-center">
                    <span className={`inline-block px-3 py-1 text-sm border ${getScoreBadge(item.score)}`}>
                      {item.score}
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <Link 
                      href={`/dashboard?q=${item.ruc}`}
                      className="inline-flex items-center gap-1 text-xs text-[#c9a050] hover:text-[#d4aa5a]"
                    >
                      <Eye className="h-3 w-3" /> Ver
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {paginatedData.length === 0 && (
            <div className="text-center py-16">
              <XCircle className="h-8 w-8 text-[#2a2a2a] mx-auto mb-4" />
              <p className="text-[#5a5a5a]">No se encontraron registros</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6">
            <p className="text-xs text-[#5a5a5a]">
              Mostrando {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredData.length)} de {filteredData.length}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-[#c9a050] hover:text-[#c9a050] disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-[#c9a050] hover:text-[#c9a050] disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
