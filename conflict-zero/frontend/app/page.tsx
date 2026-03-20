'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Shield, Zap, BarChart3 } from 'lucide-react';

export default function LandingPage() {
  const [ruc, setRuc] = useState('');
  const [loading, setLoading] = useState(false);

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
          Evalúa proveedores en segundos. Datos de SUNAT, OSCE y TCE en un solo lugar.
        </p>

        {/* Search Form */}
        <div className="max-w-xl mx-auto">
          <form className="flex gap-2">
            <input
              type="text"
              placeholder="Ingresa el RUC (11 dígitos)"
              value={ruc}
              onChange={(e) => setRuc(e.target.value.replace(/\D/g, '').slice(0, 11))}
              className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              maxLength={11}
            />
            <Link
              href={`/dashboard?ruc=${ruc}`}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 flex items-center gap-2"
            >
              <Search className="h-4 w-4" />
              {loading ? 'Verificando...' : 'Verificar'}
            </Link>
          </form>
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
              Lo que antes tomaba 3 horas, ahora se hace en 30 segundos.
            </p>
          </div>
          
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
              <Shield className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Fuentes Oficiales</h3>
            <p className="text-slate-600">
              Datos de SUNAT, OSCE y TCE. Información confiable.
            </p>
          </div>
          
          <div className="p-6 bg-white rounded-2xl shadow-sm border">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <BarChart3 className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Scoring Predictivo</h3>
            <p className="text-slate-600">
              Algoritmo de 0-100 que analiza deuda y sanciones.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-slate-50 py-12">
        <div className="container mx-auto px-4 text-center text-slate-500">
          <p>© 2026 Conflict Zero. Todos los derechos reservados.</p>
        </div>
      </footer>
    </div>
  );
}
