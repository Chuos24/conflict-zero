
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  ScaleIcon, 
  ExclamationTriangleIcon, 
  CheckCircleIcon,
  XCircleIcon,
  ArrowLeftIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

interface RUCResult {
  ruc: string;
  razon_social: string;
  score: number;
  estado: string;
  sanciones_count: number;
  inhabilitaciones_count: number;
  estado_sunat: string;
  condicion: string;
}

export default function ComparePage() {
  const [rucs, setRucs] = useState<string[]>(['', '']);
  const [results, setResults] = useState<RUCResult[]>([]);
  const [loading, setLoading] = useState(false);

  const addRUC = () => {
    if (rucs.length < 5) {
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
    newRucs[index] = value;
    setRucs(newRucs);
  };

  const compareRUCs = async () => {
    const validRucs = rucs.filter(r => r.length === 11 && /^\d{11}$/.test(r));
    if (validRucs.length < 2) {
      alert('Ingrese al menos 2 RUCs válidos');
      return;
    }

    setLoading(true);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod';
    
    try {
      const promises = validRucs.map(ruc => 
        fetch(`${API_BASE}/consulta-osce/${ruc}`).then(r => r.json())
      );
      
      const responses = await Promise.all(promises);
      const formatted = responses.map((res, i) => ({
        ruc: validRucs[i],
        razon_social: res.data?.razon_social || 'No encontrado',
        score: res.score || 0,
        estado: res.data?.estado || 'DESCONOCIDO',
        sanciones_count: res.data?.sanciones?.length || 0,
        inhabilitaciones_count: res.data?.inhabilitaciones?.length || 0,
        estado_sunat: res.data?.estado_sunat || '-',
        condicion: res.data?.condicion || '-'
      }));
      
      setResults(formatted.sort((a, b) => b.score - a.score));
    } catch (err) {
      alert('Error al comparar: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    if (score >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-500/20 border-green-500/40';
    if (score >= 60) return 'bg-yellow-500/20 border-yellow-500/40';
    if (score >= 40) return 'bg-orange-500/20 border-orange-500/40';
    return 'bg-red-500/20 border-red-500/40';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0d1b2a] via-[#1b263b] to-[#415a77] p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <a href="/dashboard" className="inline-flex items-center text-[#c9a227] hover:text-[#e8d5a3] mb-4">
            <ArrowLeftIcon className="w-5 h-5 mr-2" />
            Volver al Dashboard
          </a>
          <h1 className="text-4xl font-bold text-white mb-2" style={{ fontFamily: 'Playfair Display, serif' }}>
            Comparar Proveedores
          </h1>
          <p className="text-white/60">Compare hasta 5 empresas simultáneamente</p>
        </motion.div>

        {/* Input Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white/5 backdrop-blur-sm border border-[#c9a227]/20 rounded-2xl p-8 mb-8"
        >
          <div className="space-y-4 mb-6">
            {rucs.map((ruc, index) => (
              <div key={index} className="flex gap-3">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={ruc}
                    onChange={(e) => updateRUC(index, e.target.value)}
                    placeholder={`RUC ${index + 1} (11 dígitos)`}
                    maxLength={11}
                    className="w-full bg-white/5 border border-white/20 rounded-xl px-5 py-4 text-white placeholder-white/40 focus:border-[#c9a227] focus:outline-none transition-colors"
                  />
                  {ruc.length === 11 && /^\d{11}$/.test(ruc) && (
                    <CheckCircleIcon className="absolute right-4 top-1/2 -translate-y-1/2 w-6 h-6 text-green-400" />
                  )}
                </div>
                {rucs.length > 2 && (
                  <button
                    onClick={() => removeRUC(index)}
                    className="px-4 py-2 text-red-400 hover:text-red-300 transition-colors"
                  >
                    <XCircleIcon className="w-6 h-6" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-4">
            {rucs.length < 5 && (
              <button
                onClick={addRUC}
                className="px-6 py-3 border border-[#c9a227]/40 text-[#c9a227] rounded-xl hover:bg-[#c9a227]/10 transition-all"
              >
                + Agregar RUC
              </button>
            )}
            <button
              onClick={compareRUCs}
              disabled={loading}
              className="flex-1 bg-gradient-to-r from-[#c9a227] to-[#e8d5a3] text-[#0d1b2a] font-semibold py-4 rounded-xl hover:shadow-lg hover:shadow-[#c9a227]/30 transition-all disabled:opacity-50"
            >
              {loading ? '⏳ Comparando...' : '⚖️ Comparar Empresas'}
            </button>
          </div>
        </motion.div>

        {/* Results */}
        {results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <h2 className="text-2xl font-semibold text-white mb-4">
              Resultados de Comparación
              <span className="text-[#c9a227] ml-2">({results.length} empresas)</span>
            </h2>

            {/* Winner Banner */}
            {results[0]?.score >= 80 && (
              <div className="bg-gradient-to-r from-green-500/20 to-green-600/20 border border-green-500/40 rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
                    <CheckCircleIcon className="w-8 h-8 text-white" />
                  </div>
                  <div>
                    <p className="text-green-400 font-semibold text-lg">Mejor Opción Recomendada</p>
                    <p className="text-white text-2xl font-bold">{results[0].razon_social}</p>
                    <p className="text-white/60">Score: {results[0].score}/100 • Sin sanciones</p>
                  </div>
                </div>
              </div>
            )}

            {/* Comparison Cards */}
            <div className="grid gap-4">
              {results.map((result, index) => (
                <motion.div
                  key={result.ruc}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`relative overflow-hidden rounded-2xl border ${getScoreBg(result.score)} p-6`}
                >
                  {/* Rank Badge */}
                  <div className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center font-bold text-lg">
                    #{index + 1}
                  </div>

                  <div className="grid md:grid-cols-4 gap-6 items-center">
                    {/* Company Info */}
                    <div className="md:col-span-2">
                      <h3 className="text-xl font-semibold text-white mb-1">{result.razon_social}</h3>
                      <p className="text-white/50 font-mono">RUC: {result.ruc}</p>
                      <div className="flex gap-3 mt-3">
                        <span className="px-3 py-1 rounded-full text-xs bg-white/10">
                          {result.estado_sunat}
                        </span>
                        <span className="px-3 py-1 rounded-full text-xs bg-white/10">
                          {result.condicion}
                        </span>
                      </div>
                    </div>

                    {/* Score */}
                    <div className="text-center">
                      <div className={`text-5xl font-bold ${getScoreColor(result.score)}`}>
                        {result.score}
                      </div>
                      <p className="text-white/50 text-sm mt-1">Score de Riesgo</p>
                    </div>

                    {/* Issues */}
                    <div className="space-y-2">
                      {result.inhabilitaciones_count > 0 && (
                        <div className="flex items-center gap-2 text-red-400">
                          <ExclamationTriangleIcon className="w-5 h-5" />
                          <span className="text-sm">{result.inhabilitaciones_count} inhabilitación(es)</span>
                        </div>
                      )}
                      {result.sanciones_count > 0 && (
                        <div className="flex items-center gap-2 text-orange-400">
                          <ScaleIcon className="w-5 h-5" />
                          <span className="text-sm">{result.sanciones_count} sanción(es)</span>
                        </div>
                      )}
                      {result.inhabilitaciones_count === 0 && result.sanciones_count === 0 && (
                        <div className="flex items-center gap-2 text-green-400">
                          <CheckCircleIcon className="w-5 h-5" />
                          <span className="text-sm">Sin sanciones</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-4 pt-4 border-t border-white/10 flex gap-3">
                    <a 
                      href={`/dashboard/verify?ruc=${result.ruc}`}
                      className="text-[#c9a227] hover:text-[#e8d5a3] text-sm flex items-center gap-2"
                    >
                      <DocumentTextIcon className="w-4 h-4" />
                      Ver detalles
                    </a>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Summary Table */}
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden mt-8">
              <table className="w-full">
                <thead className="bg-white/5">
                  <tr>
                    <th className="text-left px-6 py-4 text-[#c9a227] font-semibold">Empresa</th>
                    <th className="text-center px-6 py-4 text-[#c9a227] font-semibold">Score</th>
                    <th className="text-center px-6 py-4 text-[#c9a227] font-semibold">Sanciones</th>
                    <th className="text-center px-6 py-4 text-[#c9a227] font-semibold">Inhabilitaciones</th>
                    <th className="text-center px-6 py-4 text-[#c9a227] font-semibold">Estado SUNAT</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result) => (
                    <tr key={result.ruc} className="border-t border-white/5 hover:bg-white/5">
                      <td className="px-6 py-4">
                        <div className="font-medium text-white">{result.razon_social}</div>
                        <div className="text-sm text-white/50">{result.ruc}</div>
                      </td>
                      <td className="text-center px-6 py-4">
                        <span className={`text-2xl font-bold ${getScoreColor(result.score)}`}>
                          {result.score}
                        </span>
                      </td>
                      <td className="text-center px-6 py-4 text-white/70">{result.sanciones_count}</td>
                      <td className="text-center px-6 py-4">
                        <span className={result.inhabilitaciones_count > 0 ? 'text-red-400 font-semibold' : 'text-white/70'}>
                          {result.inhabilitaciones_count}
                        </span>
                      </td>
                      <td className="text-center px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs ${
                          result.estado_sunat === 'ACTIVO' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {result.estado_sunat}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
