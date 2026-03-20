'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Shield, Zap, BarChart3, CheckCircle, ArrowRight } from 'lucide-react';
import { verification } from '@/lib/api';

export default function LandingPage() {
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
      const response = await verification.publicVerify(ruc);
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

  const getRiskLabel = (level: string) => {
    const labels: any = {
      low: 'Riesgo Bajo',
      medium: 'Riesgo Moderado',
      high: 'Riesgo Alto',
      critical: 'Riesgo Crítico'
    };
    return labels[level] || level;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold">Conflict Zero</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium hover:text-blue-600">
              Iniciar Sesión
            </Link>
            <Link 
              href="/register" 
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Registrarse
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Verificación de Riesgo Contractual
        </h1>
        <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto">
          Reduce el proceso de due diligence de <strong>3 horas a 30 segundos</strong>.
          Consulta sanciones de OSCE, TCE y deuda SUNAT en un solo click.
        </p>

        {/* Demo Search */}
        <div className="max-w-xl mx-auto mb-16">
          <form onSubmit={handleVerify} className="relative">
            <input
              type="text"
              placeholder="Ingresa un RUC de 11 dígitos..."
              value={ruc}
              onChange={(e) => setRuc(e.target.value.replace(/\D/g, '').slice(0, 11))}
              className="w-full px-6 py-4 pr-36 text-lg border rounded-2xl shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={loading || ruc.length !== 11}
              className="absolute right-2 top-2 bottom-2 bg-blue-600 text-white px-6 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>Verificando...</>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Verificar
                </>
              )}
            </button>
          </form>
          
          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>
          )}
          
          {/* Result Preview */}
          {result && (
            <div className="mt-8 p-6 bg-white rounded-2xl shadow-xl border text-left">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm text-slate-500">{result.ruc}</p>
                  <h3 className="text-lg font-semibold">{result.company_name}</h3>
                </div>
                <div className="text-right">
                  <div className={`text-4xl font-bold ${getScoreColor(result.score)}`>
                    {result.score}
                  </div>
                  <p className="text-sm text-slate-500">{getRiskLabel(result.risk_level)}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-slate-500">Deuda SUNAT</p>
                  <p className="font-semibold">S/ {result.sunat_data?.debt_amount?.toLocaleString() || 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-slate-500">Sanciones OSCE</p>
                  <p className="font-semibold">{result.osce_sanctions?.length || 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-slate-500">Sanciones TCE</p>
                  <p className="font-semibold">{result.tce_sanctions?.length || 0}</p>
                </div>
              </div>
              
              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Demo:</strong> Este es un resultado de demostración. 
                  <Link href="/register" className="underline">Regístrate</Link> para ver reportes completos.
                </p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">¿Por qué elegir Conflict Zero?</h2>
        
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
              <Zap className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">30 Segundos</h3>
            <p className="text-slate-600">
              Lo que antes tomaba 3 horas de revisión manual, ahora se hace en 30 segundos.
            </p>
          </div>
          
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
              <Shield className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Fuentes Oficiales</h3>
            <p className="text-slate-600">
              Datos actualizados de SUNAT, OSCE y TCE. Información confiable y verificable.
            </p>
          </div>
          
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <BarChart3 className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Scoring Predictivo</h3>
            <p className="text-slate-600">
              Algoritmo de 0-100 que analiza deuda, sanciones y patrones de riesgo.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Planes y Precios</h2>
        
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <h3 className="text-lg font-semibold">Free</h3>
            <div className="text-3xl font-bold my-4">$0</div>
            <ul className="space-y-2 text-slate-600 mb-6">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                100 consultas/mes
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Datos SUNAT
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Sanciones OSCE/TCE
              </li>
            </ul>
            <Link 
              href="/register"
              className="block w-full text-center py-2 border rounded-lg font-medium hover:bg-slate-50"
            >
              Comenzar Gratis
            </Link>
          </div>
          
          <div className="p-6 bg-blue-600 text-white rounded-2xl shadow-xl relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-400 text-yellow-900 px-3 py-1 rounded-full text-xs font-semibold">
              Popular
            </div>
            <h3 className="text-lg font-semibold">Starter</h3>
            <div className="text-3xl font-bold my-4">$400/mes</div>
            <ul className="space-y-2 text-blue-100 mb-6">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                1,000 consultas/mes
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Reportes PDF
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                API Access
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Soporte email
              </li>
            </ul>
            <Link 
              href="/register"
              className="block w-full text-center py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50"
            >
              Elegir Starter
            </Link>
          </div>
          
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <h3 className="text-lg font-semibold">Pro</h3>
            <div className="text-3xl font-bold my-4">$800/mes</div>
            <ul className="space-y-2 text-slate-600 mb-6">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Consultas ilimitadas
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Reportes personalizados
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                API con SLA
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Soporte prioritario
              </li>
            </ul>
            <Link 
              href="/register"
              className="block w-full text-center py-2 border rounded-lg font-medium hover:bg-slate-50"
            >
              Contactar Ventas
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 text-blue-600" />
              <span className="font-semibold">Conflict Zero</span>
            </div>
            <p className="text-sm text-slate-500">
              © 2026 Conflict Zero S.A.C. Todos los derechos reservados.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
