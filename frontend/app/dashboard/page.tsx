'use client';

import { useState } from 'react';
import { Search, CheckCircle, MapPin, ArrowUpRight } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const [ruc, setRuc] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (ruc.length !== 11) {
      setError('El RUC debe tener 11 dígitos');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_BASE}/consulta-osce/${ruc}`);
      const data = await response.json();
      
      if (data.success) {
        setResult(data);
      } else {
        setError(data.error || 'Error al verificar');
      }
    } catch {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div>
            <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Dashboard</p>
            <h1 className="text-3xl font-light">Verificación RUC</h1>
          </div>
          <Link 
            href="/pricing" 
            className="flex items-center gap-2 text-xs tracking-wide text-[#8a8a8a] hover:text-[#c9a050]"
          >
            <ArrowUpRight className="h-4 w-4" />
            Membership
          </Link>
        </div>

        <div className="border border-[#1a1a1a] p-8 mb-8">
          <form onSubmit={handleVerify} className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Ingrese RUC (11 dígitos)"
                value={ruc}
                onChange={(e) => setRuc(e.target.value.replace(/\D/g, '').slice(0, 11))}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-4 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                maxLength={11}
              />
            </div>
            <button
              type="submit"
              disabled={loading || ruc.length !== 11}
              className="bg-[#c9a050] text-[#0a0a0a] px-8 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors disabled:opacity-50"
            >
              {loading ? 'Verificando...' : 'Verificar'}
            </button>
          </form>

          {error && (
            <div className="mt-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400">{error}</div>
          )}
        </div>

        {result && result.data && (
          <div className="border border-[#1a1a1a]">
            <div className="p-8 border-b border-[#1a1a1a]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-[#c9a050] tracking-[0.2em] uppercase mb-2">{result.data.ruc}</p>
                  <h2 className="text-2xl font-light mb-4">{result.data.razon_social}</h2>
                  
                  <div className="flex gap-4">
                    <span className="text-xs tracking-wide text-[#8a8a8a] border border-[#2a2a2a] px-3 py-1">
                      SUNAT: {result.data.estado_sunat}
                    </span>
                    <span className="text-xs tracking-wide text-[#8a8a8a] border border-[#2a2a2a] px-3 py-1">
                      {result.data.condicion}
                    </span>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-5xl font-light text-[#c9a050]">{result.score}</p>
                  <p className="text-xs text-[#8a8a8a] mt-1">Score de Riesgo</p>
                </div>
              </div>
            </div>

            <div className="p-8">
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Dirección Fiscal</p>
                  <div className="flex items-start gap-3">
                    <MapPin className="h-4 w-4 text-[#c9a050] mt-1 flex-shrink-0" />
                    <div>
                      <p>{result.data.direccion || 'No disponible'}</p>
                      <p className="text-sm text-[#5a5a5a]">
                        {result.data.distrito && `${result.data.distrito}, `}
                        {result.data.provincia && `${result.data.provincia}, `}
                        {result.data.departamento}
                      </p>
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Fuente de Datos</p>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-[#c9a050]" />
                    <span className="text-sm">Decolecta SUNAT</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {!result && !loading && (
          <div className="text-center py-24 border border-[#1a1a1a]">
            <p className="text-[#5a5a5a]">Ingrese un RUC para verificar la información</p>
          </div>
        )}
      </div>
    </div>
  );
}
