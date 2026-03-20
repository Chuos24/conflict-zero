'use client';

import { useState } from 'react';
import { Search, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
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
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod';
      const response = await fetch(`${API_BASE}/consulta-osce/${ruc}`);
      const data = await response.json();
      
      if (data.success) {
        setResult(data);
      } else {
        setError(data.message || 'Error al verificar');
      }
    } catch (err: any) {
      setError('Error de conexión: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    if (score >= 40) return 'text-orange-500';
    return 'text-red-500';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Verificar RUC</h1>
        <p className="text-slate-500">Consulta información de empresas peruanas</p>
      </div>

      {/* Search Form */}
      <div className="bg-white p-6 rounded-xl shadow-sm border">
        <form onSubmit={handleVerify} className="flex gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Ingresa el RUC (11 dígitos)"
              value={ruc}
              onChange={(e) => setRuc(e.target.value.replace(/\D/g, '').slice(0, 11))}
              className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              maxLength={11}
            />
          </div>
          <button
            type="submit"
            disabled={loading || ruc.length !== 11}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            {loading ? 'Verificando...' : 'Verificar'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>
        )}
      </div>

      {/* Results */}
      {result && result.data && (
        <div className="space-y-6">
          {/* Score Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500">{result.data.ruc}</p>
                <h3 className="text-xl font-semibold">{result.data.razon_social}</h3>
                <div className="mt-2 flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full text-sm bg-slate-100">
                    {result.data.estado_sunat}
                  </span>
                  <span className="px-3 py-1 rounded-full text-sm bg-slate-100">
                    {result.data.condicion}
                  </span>
                </div>
              </div>
              
              <div className="text-right">
                <div className={`text-5xl font-bold ${getScoreColor(result.score)}`}>
                  {result.score}
                </div>
                <p className="text-sm text-slate-500 mt-1">Score de Riesgo</p>
              </div>
            </div>

            {/* Score Bar */}
            <div className="mt-6">
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getScoreBg(result.score)}`}
                  style={{ width: `${result.score}%` }}
                />
              </div>
              <div className="flex justify-between mt-2 text-sm text-slate-500">
                <span>0 (Alto Riesgo)</span>
                <span>100 (Bajo Riesgo)</span>
              </div>
            </div>
          </div>

          {/* Sanciones */}
          {result.data.total_registros > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-red-100">
              <div className="flex items-center gap-2 text-red-600 mb-4">
                <AlertTriangle className="h-5 w-5" />
                <h3 className="font-semibold">Sanciones Detectadas</h3>
              </div>
              
              <div className="space-y-3">
                {result.data.sanciones?.map((s: any, i: number) => (
                  <div key={i} className="p-4 bg-red-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      <span className="font-medium">{s.tipo_sancion}</span>
                      <span className="text-slate-400">| {s.entidad}</span>
                    </div>
                    <p className="text-sm text-slate-600 mt-1">{s.motivo}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Certificado */}
          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Certificado de Verificación</h3>
                <p className="text-sm text-slate-500">Genera un certificado PDF con validez legal</p>
              </div>
              <Link
                href={`/dashboard/verify?ruc=${result.data.ruc}`}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
              >
                Ver Detalles Completos
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="bg-slate-50 p-12 rounded-xl text-center">
          <CheckCircle className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Ingresa un RUC para verificar la información</p>
        </div>
      )}
    </div>
  );
}
