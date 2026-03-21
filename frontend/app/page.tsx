'use client';

import Link from 'next/link';
import { Shield, Search, Lock, FileText, ChevronRight } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3]">
      {/* Header */}
      <header className="border-b border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-8 h-20 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Shield className="h-7 w-7 text-[#c9a050]" strokeWidth={1.5} />
            <span className="text-lg tracking-[0.2em] font-light uppercase">Conflict Zero</span>
          </Link>
          <div className="flex items-center gap-8">
            <Link href="/blog" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3] transition-colors">
              Blog
            </Link>
            <Link href="/pricing" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3] transition-colors">
              Membership
            </Link>
            <Link href="/login" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3] transition-colors">
              Acceso
            </Link>
            <Link 
              href="/register" 
              className="text-sm tracking-wide border border-[#c9a050] text-[#c9a050] px-6 py-2 hover:bg-[#c9a050] hover:text-[#0a0a0a] transition-all"
            >
              Solicitar Acceso
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-8 pt-32 pb-24">
        <div className="max-w-4xl">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-8">Inteligencia de Riesgo para Profesionales</p>
          <h1 
            className="text-5xl md:text-7xl font-light leading-[1.1] mb-8"
            style={{ fontFamily: 'var(--font-playfair), serif' }}
          >
            Verificación de<br />
            <span className="text-[#c9a050]">Contrapartes</span>
          </h1>
          
          <p className="text-xl text-[#8a8a8a] max-w-2xl leading-relaxed mb-12">
            Datos oficiales de SUNAT, OSCE y TCE para due diligence. 
            Servicio exclusivo para abogados, consultoras y fondos de inversión.
          </p>

          <div className="flex flex-col sm:flex-row gap-4">
            <Link 
              href="/register" 
              className="inline-flex items-center justify-center gap-2 bg-[#c9a050] text-[#0a0a0a] px-8 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors"
            >
              Solicitar Membresía
              <ChevronRight className="h-4 w-4" />
            </Link>
            <Link 
              href="/pricing" 
              className="inline-flex items-center justify-center gap-2 border border-[#2a2a2a] text-[#e8e6e3] px-8 py-4 text-sm tracking-[0.1em] uppercase hover:border-[#c9a050] transition-colors"
            >
              Ver Planes
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-[#1a1a1a] bg-[#0d0d0d]">
        <div className="max-w-7xl mx-auto px-8 py-24">
          <div className="grid md:grid-cols-3 gap-px bg-[#1a1a1a]">
            <div className="bg-[#0d0d0d] p-12">
              <Search className="h-8 w-8 text-[#c9a050] mb-6" strokeWidth={1.5} />
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Consulta</p>
              <h3 className="text-lg mb-3">Datos SUNAT</h3>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">
                Razón social, estado, condición y dirección fiscal en tiempo real.
              </p>
            </div>

            <div className="bg-[#0d0d0d] p-12">
              <Lock className="h-8 w-8 text-[#c9a050] mb-6" strokeWidth={1.5} />
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Verificación</p>
              <h3 className="text-lg mb-3">Sanciones OSCE/TCE</h3>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">
                Inhabilitaciones, multas y sanciones de entidades públicas.
              </p>
            </div>

            <div className="bg-[#0d0d0d] p-12">
              <FileText className="h-8 w-8 text-[#c9a050] mb-6" strokeWidth={1.5} />
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Certificación</p>
              <h3 className="text-lg mb-3">Certificados PDF</h3>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">
                Documentos oficiales con validez legal para procesos formales.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-7xl mx-auto px-8 py-24">
        <div className="grid grid-cols-3 gap-8 text-center">
          <div>
            <p className="text-4xl font-light text-[#c9a050] mb-2">500+</p>
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Miembros Activos</p>
          </div>
          <div>
            <p className="text-4xl font-light text-[#c9a050] mb-2">50K+</p>
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Consultas Mensuales</p>
          </div>
          <div>
            <p className="text-4xl font-light text-[#c9a050] mb-2">99.9%</p>
            <p className="text-xs tracking-[0.2em] uppercase text-[#8a8a8a]">Uptime Garantizado</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-8 py-24 text-center">
          <h2 
            className="text-3xl font-light mb-6"
            style={{ fontFamily: 'var(--font-playfair), serif' }}
          >
            Acceso Exclusivo
          </h2>
          <p className="text-[#8a8a8a] max-w-xl mx-auto mb-10">
            Servicio diseñado para profesionales que requieren información 
            confiable y verificada. Sin planes gratuitos.
          </p>
          <Link 
            href="/register" 
            className="inline-flex items-center justify-center gap-2 bg-[#c9a050] text-[#0a0a0a] px-8 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors"
          >
            Solicitar Membresía
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-8 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-[#c9a050]" strokeWidth={1.5} />
              <span className="text-sm tracking-[0.2em] uppercase">Conflict Zero</span>
            </div>
            <div className="flex gap-8 text-xs text-[#8a8a8a]">
              <Link href="/terminos" className="hover:text-[#e8e6e3] transition-colors">Términos</Link>
              <Link href="/privacidad" className="hover:text-[#e8e6e3] transition-colors">Privacidad</Link>
              <Link href="/pricing" className="hover:text-[#e8e6e3] transition-colors">Membership</Link>
            </div>
            <p className="text-xs text-[#5a5a5a]">© 2026. Todos los derechos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
