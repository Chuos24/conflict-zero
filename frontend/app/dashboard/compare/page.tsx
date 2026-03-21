'use client';

import { useState } from 'react';
import { Scale, ArrowLeft, Plus, X, CheckCircle, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

interface RUCResult {
  ruc: string;
  razon_social: string;
  score: number;
  estado_sunat: string;
  condicion: string;
}

// PLAN LIMITATIONS
// Essential: max 2 RUCs
// Professional: max 5 RUCs  
// Enterprise: max 10 RUCs
const PLAN_LIMITS: Record<string, number> = {
  essential: 2,
  professional: 5,
  enterprise: 10
};

export default function ComparePage() {
  const [rucs, setRucs] = useState<string[]>(['', '']);
  const [results, setResults] = useState<RUCResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Esto vendría del backend/auth
  const userPlan = 'essential';
  const maxRUCs = PLAN_LIMITS[userPlan];

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
    
    // Simulación - en producción llamaría a la API
    setTimeout(() => {
      const mockResults: RUCResult[] = validRucs.map((ruc, i) => ({
        ruc,
        razon_social: `Empresa ${String.fromCharCode(65 + i)} S.A.C.`,
        score: Math.floor(Math.random() * 40) + 60,
        estado_sunat: 'ACTIVO',
        condicion: 'HABIDO'
      }));
      setResults(mockResults.sort((a, b) => b.score - a.score));
      setLoading(false);
    }, 1500);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400 border-green-500/30 bg-green-500/10';
    if (score >= 60) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    if (score >= 40) return 'text-orange-400 border-orange-500/30 bg-orange-500/10';
    return 'text-red-400 border-red-500/30 bg-red-500/10';
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-4xl mx-auto">
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
              Plan <span className="text-[#c9a050]">{userPlan.charAt(0).toUpperCase() + userPlan.slice(1)}</span>: 
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
                  />
                </div>
                {rucs.length > 2 && (
                  <button
                    onClick={() => removeRUC(index)}
                    className="p-3 border border-[#2a2a2a] text-[#5a5a5a] hover:border-red-500/50 hover:text-red-400"
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
                className="flex items-center gap-2 border border-[#2a2a2a] text-[#8a8a8a] px-4 py-3 hover:border-[#c9a050] hover:text-[#c9a050] transition-colors"
              >
                <Plus className="h-4 w-4" /> Agregar RUC
              </button>
            )}
            <button
              onClick={compareRUCs}
              disabled={loading}
              className="flex-1 bg-[#c9a050] text-[#0a0a0a] py-3 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors disabled:opacity-50"
            >
              {loading ? 'Comparando...' : 'Comparar'}
            </button>
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Resultados Ordenados por Score</p>
            </div>
            
            <div className="divide-y divide-[#1a1a1a]">
              {results.map((result, index) => (
                <div key={result.ruc} className="p-6 flex items-center justify-between hover:bg-[#0d0d0d]">
                  <div className="flex items-center gap-4">
                    <div className={`
                      w-8 h-8 flex items-center justify-center text-sm font-medium
                      ${index === 0 ? 'bg-[#c9a050] text-[#0a0a0a]' : 'border border-[#2a2a2a] text-[#5a5a5a]'}
                    `}>
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm text-[#5a5a5a] mb-1">{result.ruc}</p>
                      <p className="text-lg">{result.razon_social}</p>
                      <div className="flex gap-2 mt-2">
                        <span className="text-xs text-[#5a5a5a] border border-[#2a2a2a] px-2 py-0.5">{result.estado_sunat}</span>
                        <span className="text-xs text-[#5a5a5a] border border-[#2a2a2a] px-2 py-0.5">{result.condicion}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <span className={`inline-block px-4 py-2 text-2xl font-light border ${getScoreColor(result.score)}`}>
                      {result.score}
                    </span>
                    <p className="text-xs text-[#5a5a5a] mt-2">Score</p>
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
