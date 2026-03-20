'use client';

import { useState } from 'react';
import { Search, Download, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { verification } from '@/lib/api';

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
      const response = await verification.verify(ruc);
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al verificar el RUC');
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

  const getRiskLabel = (level: string) => {
    const labels: any = {
      low: { text: 'Riesgo Bajo', icon: CheckCircle, color: 'text-green-600 bg-green-50' },
      medium: { text: 'Riesgo Moderado', icon: AlertTriangle, color: 'text-yellow-600 bg-yellow-50' },
      high: { text: 'Riesgo Alto', icon: AlertTriangle, color: 'text-orange-600 bg-orange-50' },
      critical: { text: 'Riesgo Crítico', icon: XCircle, color: 'text-red-600 bg-red-50' }
    };
    return labels[level] || { text: level, icon: AlertTriangle, color: 'text-slate-600 bg-slate-50' };
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Verificar RUC</h1>
        <p className="text-slate-500">Consulta la información de una empresa peruana</p>
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
      {result && (
        <div className="space-y-6">
          {/* Score Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500">{result.ruc}</p>
                <h2 className="text-2xl font-bold">{result.company_name}</h2>
                <div className="mt-4 flex items-center gap-2">
                  {(() => {
                    const risk = getRiskLabel(result.risk_level);
                    const Icon = risk.icon;
                    return (
                      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${risk.color}`}>
                        <Icon className="h-4 w-4" />
                        {risk.text}
                      </span>
                    );
                  })()}
                  {result.cached && (
                    <span className="text-xs text-slate-400">(Desde caché)</span>
                  )}
                </div>
              </div>

              <div className="text-center">
                <div className={`text-6xl font-bold ${getScoreColor(result.score)}`>
                  {result.score}
                </div>
                <p className="text-sm text-slate-500 mt-1">Score de Riesgo</p>
                <div className="w-32 h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                  <div
                    className={`h-full ${getScoreBg(result.score)}`}
                    style={{ width: `${result.score}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* SUNAT Data */}
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center text-sm">>SUNAT</span>
                Información Tributaria
              </h3>
              
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-slate-500">Deuda Coactiva</p>
                  <p className="text-lg font-semibold">
                    S/ {result.sunat_data?.debt_amount?.toLocaleString() || 0}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Estado</p>
                  <p className="text-sm font-medium">{result.sunat_data?.tax_status}</p>
                </div>
                
                <div className="pt-3 border-t">
                  <p className="text-xs text-slate-500">Contribución al score</p>
                  <p className="text-sm font-semibold text-blue-600">
                    +{result.score_breakdown?.sunat_contribution?.toFixed(1)} puntos
                  </p>
                </div>
              </div>
            </div>

            {/* OSCE Sanctions */}
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center text-sm">>OSCE</span>
                Sanciones
              </h3>
              
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-slate-500">Total de sanciones</p>
                  <p className="text-lg font-semibold">{result.osce_sanctions?.length || 0}</p>
                </div>

                {result.osce_sanctions?.length > 0 ? (
                  <div className="max-h-32 overflow-y-auto space-y-2">
                    {result.osce_sanctions.slice(0, 3).map((s: any, i: number) => (
                      <div key={i} className="p-2 bg-red-50 rounded text-xs">
                        <p className="font-medium">{s.description}</p>
                        <p className="text-slate-500">{s.status}</p>
                      </div>
                    ))}
                    {result.osce_sanctions.length > 3 && (
                      <p className="text-xs text-slate-500">Y {result.osce_sanctions.length - 3} más...</p>
                    )}
                  </div>
                ) : (
                  <div className="p-3 bg-green-50 rounded-lg text-sm text-green-700">
                    ✓ Sin sanciones registradas
                  </div>
                )}
                
                <div className="pt-3 border-t">
                  <p className="text-xs text-slate-500">Contribución al score</p>
                  <p className="text-sm font-semibold text-blue-600">
                    +{result.score_breakdown?.osce_contribution?.toFixed(1)} puntos
                  </p>
                </div>
              </div>
            </div>

            {/* ML Analysis */}
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center text-sm">>ML</span>
                Análisis Predictivo
              </h3>
              
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-slate-500">Score de anomalía</p>
                  <p className="text-lg font-semibold">
                    {result.ml_analysis?.anomaly_score?.toFixed(1)}%
                  </p>
                </div>

                <div>
                  <p className="text-sm text-slate-500">Confianza</p>
                  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500"
                      style={{ width: `${(result.ml_analysis?.confidence || 0) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {((result.ml_analysis?.confidence || 0) * 100).toFixed(0)}%
                  </p>
                </div>

                {result.ml_analysis?.risk_factors?.length > 0 && (
                  <div>
                    <p className="text-sm text-slate-500 mb-2">Factores de riesgo</p>
                    <ul className="text-xs space-y-1">
                      {result.ml_analysis.risk_factors.map((factor: string, i: number) => (
                        <li key={i} className="text-amber-600">• {factor}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                <div className="pt-3 border-t">
                  <p className="text-xs text-slate-500">Contribución al score</p>
                  <p className="text-sm font-semibold text-blue-600">
                    +{result.score_breakdown?.ml_contribution?.toFixed(1)} puntos
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <button
              onClick={() => setResult(null)}
              className="px-4 py-2 border rounded-lg font-medium hover:bg-slate-50"
            >
              Nueva consulta
            </button>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Descargar PDF
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
