'use client';

import { useState, useEffect } from 'react';
import { Scale, ArrowLeft, Plus, X, CheckCircle, AlertTriangle } from 'lucide-react';
import Button from '@/components/ui/Button';
import Link from 'next/link';

interface RUCResult {
  ruc: string;
  razon_social: string;
  score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  estado_sunat: string;
  condicion: string;
  sanciones_osce: number;
  sanciones_tce: number;
  deuda_sunat: number;
}

interface CompareLimit {
  plan_type: string;
  max_rucs: number;
  limits_by_plan: Record<string, number>;
}

export default function ComparePage() {
  const [rucs, setRucs] = useState<string[]>(['', '']);
  const [results, setResults] = useState<RUCResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [limits, setLimits] = useState<CompareLimit | null>(null);
  const [comparisonSummary, setComparisonSummary] = useState<any>(null);
  
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  // Cargar límites al montar
  useEffect(() => {
    fetchLimits();
  }, []);

  const fetchLimits = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`${API_BASE}/api/v1/compare/limits`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setLimits(data);
      }
    } catch (err) {
      console.error('Error fetching limits:', err);
    }
  };

  const maxRUCs = limits?.max_rucs || 2;
  const userPlan = limits?.plan_type || 'essential';

  const addRUC = () => {
    if (rucs.length < maxRUCs) {
      setRucs([...rucs, '']);
    }
  };

  const removeRUC = (index: number) => {
    if (rucs.length > 2) {
      const newRucs = rucs.filter((_, i) => i !== index);
      setRucs(newRucs);
    }
  };

  const updateRUC = (index: number, value: string) => {
    const newRucs = [...rucs];
    newRucs[index] = value.replace(/\D/g, '').slice(0, 11);
    setRucs(newRucs);
  };

  const compareRUCs = async () => {
    const validRucs = rucs.filter(r => r.length === 11);
    if (validRucs.length < 2) {
      setError('Ingrese al menos 2 RUCs válidos de 11 dígitos');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);
    setComparisonSummary(null);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/compare`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ rucs: validRucs })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 401) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          localStorage.removeItem('token');
        } else if (response.status === 403) {
          setError(errorData.detail || 'Límite de RUCs excedido para su plan.');
        } else {
          setError(errorData.detail || 'Error al comparar RUCs');
        }
        setLoading(false);
        return;
      }

      const data = await response.json();
      setResults(data.results);
      setComparisonSummary(data.comparison_summary);
    } catch (err) {
      console.error('Error comparing RUCs:', err);
      setError('Error de conexión. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400 border-green-500/30 bg-green-500/10';
    if (score >= 60) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    if (score >= 40) return 'text-orange-400 border-orange-500/30 bg-orange-500/10';
    return 'text-red-400 border-red-500/30 bg-red-500/10';
  };

  const getRiskLabel = (level: string) => {
    const labels: Record<string, string> = {
      low: 'Bajo',
      medium: 'Medio',
      high: 'Alto',
      critical: 'Crítico'
    };
    return labels[level] || level;
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-[#5a5a5a] hover:text-[#c9a050]">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Comparación</p>
              <h1 className="text-3xl font-light">Comparar RUCs</h1>
            </div>
          </div>
        </div>

        {/* Plan Limitation Notice */}
        <div className="border border-[#c9a050]/20 bg-[#c9a050]/5 p-4 mb-8">
          <div className="flex items-center gap-3">
            <Scale className="h-4 w-4 text-[#c9a050]" />
            <p className="text-sm text-[#8a8a8a]">
              Plan <span className="text-[#c9a050] capitalize">{userPlan}</span>: 
              Máximo {maxRUCs} RUCs por comparación.{' '}
              {userPlan !== 'enterprise' && (
                <Link href="/pricing" className="text-[#c9a050] hover:underline">Upgrade</Link>
              )}
            </p>
          </div>
        </div>

        {/* Input Form */}
        <div className="border border-[#1a1a1a] p-8 mb-8">
          <div className="space-y-4 mb-6">
            {rucs.map((ruc, index) => (
              <div key={index} className="flex gap-4">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder={`RUC ${index + 1} (11 dígitos)`}
                    value={ruc}
                    onChange={(e) => updateRUC(index, e.target.value)}
                    className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                    maxLength={11}
                    disabled={loading}
                  />
                  {ruc.length > 0 && ruc.length !== 11 && (
                    <p className="text-xs text-red-400 mt-1">El RUC debe tener 11 dígitos</p>
                  )}
                </div>
                {rucs.length > 2 && (
                  <button
                    onClick={() => removeRUC(index)}
                    disabled={loading}
                    className="p-3 border border-[#2a2a2a] text-[#5a5a5a] hover:border-red-500/50 hover:text-red-400 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {error && (
            <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> {error}
            </div>
          )}

          <div className="flex gap-4">
            {rucs.length < maxRUCs && (
              <button
                onClick={addRUC}
                disabled={loading}
                className="flex items-center gap-2 border border-[#2a2a2a] text-[#8a8a5a] px-4 py-3 hover:border-[#c9a050] hover:text-[#c9a050] transition-colors disabled:opacity-50"
              >
                <Plus className="h-4 w-4" /> Agregar RUC
              </button>
            )}
            <Button
              onClick={compareRUCs}
              disabled={loading}
              variant="primary"
              icon={loading ? <span className="animate-spin">⏳</span> : undefined}
            >
              {loading ? 'Comparando...' : 'Comparar'}
            </Button>
          </div>
        </div>

        {/* Comparison Summary */}
        {comparisonSummary && (
          <div className="border border-[#1a1a1a] p-6 mb-8">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-4">Resumen de Comparación</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-[#0d0d0d]">
                <p className="text-2xl font-light text-[#c9a050]">{comparisonSummary.average_score}</p>
                <p className="text-xs text-[#5a5a5a]">Score Promedio</p>
              </div>
              <div className="text-center p-4 bg-[#0d0d0d]">
                <p className="text-2xl font-light text-green-400">{comparisonSummary.score_range.max}</p>
                <p className="text-xs text-[#5a5a5a]">Mejor Score</p>
              </div>
              <div className="text-center p-4 bg-[#0d0d0d]">
                <p className="text-2xl font-light text-red-400">{comparisonSummary.score_range.min}</p>
                <p className="text-xs text-[#5a5a5a]">Peor Score</p>
              </div>
              <div className="text-center p-4 bg-[#0d0d0d]">
                <p className="text-2xl font-light text-[#e8e6e3]">{results.length}</p>
                <p className="text-xs text-[#5a5a5a]">RUCs Comparados</p>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Resultados Ordenados por Score</p>
            </div>
            
            <div className="divide-y divide-[#1a1a1a]">
              {results.map((result, index) => (
                <div key={result.ruc} className="p-6 hover:bg-[#0d0d0d]">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`
                        w-8 h-8 flex items-center justify-center text-sm font-medium
                        ${index === 0 ? 'bg-[#c9a050] text-[#0a0a0a]' : 'border border-[#2a2a2a] text-[#5a5a5a]'}
                      `}>
                        {index === 0 ? <CheckCircle className="h-4 w-4" /> : index + 1}
                      </div>
                      <div>
                        <p className="text-sm text-[#5a5a5a] mb-1">{result.ruc}</p>
                        <p className="text-lg text-[#e8e6e3]">{result.razon_social}</p>
                        <div className="flex gap-2 mt-2 flex-wrap">
                          <span className="text-xs text-[#5a5a5a] border border-[#2a2a2a] px-2 py-0.5">
                            {result.estado_sunat}
                          </span>
                          <span className="text-xs text-[#5a5a5a] border border-[#2a2a2a] px-2 py-0.5">
                            {result.condicion}
                          </span>
                          {result.sanciones_osce > 0 && (
                            <span className="text-xs text-red-400 border border-red-500/30 px-2 py-0.5">
                              {result.sanciones_osce} sanción{result.sanciones_osce > 1 ? 'es' : ''} OSCE
                            </span>
                          )}
                          {result.sanciones_tce > 0 && (
                            <span className="text-xs text-orange-400 border border-orange-500/30 px-2 py-0.5">
                              {result.sanciones_tce} sanción{result.sanciones_tce > 1 ? 'es' : ''} TCE
                            </span>
                          )}
                          {result.deuda_sunat > 0 && (
                            <span className="text-xs text-amber-400 border border-amber-500/30 px-2 py-0.5">
                              Deuda: S/ {result.deuda_sunat.toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <span className={`inline-block px-4 py-2 text-2xl font-light border ${getScoreColor(result.score)}`}>
                        {result.score}
                      </span>
                      <p className="text-xs text-[#5a5a5a] mt-2 uppercase">{getRiskLabel(result.risk_level)}</p>
                    </div>
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
