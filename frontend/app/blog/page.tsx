'use client';

import Link from 'next/link';
import { Shield, ArrowRight, Clock, User } from 'lucide-react';

const blogPosts = [
  {
    id: 'due-diligence-2026',
    title: 'El Estado de la Due Diligence en el Perú 2026',
    excerpt: 'Un análisis exhaustivo de cómo las empresas peruanas están adoptando nuevas tecnologías para agilizar sus procesos de verificación de contrapartes.',
    author: 'Equipo Legal',
    date: '15 Mar 2026',
    readTime: '8 min',
    category: 'Análisis'
  },
  {
    id: 'sanciones-osce-tce',
    title: 'Guía Completa: Sanciones OSCE y TCE',
    excerpt: 'Todo lo que necesita saber sobre las inhabilitaciones y multas del OSCE y Tribunal de Contrataciones del Estado.',
    author: 'María Elena Vargas',
    date: '10 Mar 2026',
    readTime: '12 min',
    category: 'Guía'
  },
  {
    id: 'riesgo-proveedores',
    title: 'Mitigación de Riesgo en Cadenas de Suministro',
    excerpt: 'Estrategias probadas para reducir el riesgo contractual con proveedores en el sector público peruano.',
    author: 'Carlos Mendoza',
    date: '5 Mar 2026',
    readTime: '6 min',
    category: 'Estrategia'
  },
  {
    id: 'ml-detection',
    title: 'Machine Learning en la Detección de Riesgo',
    excerpt: 'Cómo los algoritmos de IA están revolucionando la identificación de anomalías en datos SUNAT.',
    author: 'Equipo Técnico',
    date: '28 Feb 2026',
    readTime: '10 min',
    category: 'Tecnología'
  },
  {
    id: 'compliance-osce',
    title: 'Compliance OSCE: Checklist 2026',
    excerpt: 'La lista definitiva de verificación para asegurar el cumplimiento normativo en contrataciones públicas.',
    author: 'Dra. Ana Lucero',
    date: '20 Feb 2026',
    readTime: '15 min',
    category: 'Compliance'
  },
  {
    id: 'casos-exito',
    title: 'Casos de Éxito: Reducción de Riesgo del 85%',
    excerpt: 'Cómo tres fondos de inversión lograron reducir drásticamente su exposición a contrapartes de alto riesgo.',
    author: 'Equipo Editorial',
    date: '15 Feb 2026',
    readTime: '7 min',
    category: 'Casos'
  }
];

export default function BlogPage() {
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
            <Link href="/pricing" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3]">Membership</Link>
            <Link href="/login" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3]">Acceso</Link>
            <Link 
              href="/register" 
              className="text-sm tracking-wide border border-[#c9a050] text-[#c9a050] px-6 py-2 hover:bg-[#c9a050] hover:text-[#0a0a0a]"
            >
              Solicitar Acceso
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-8 pt-24 pb-16">
        <div className="max-w-3xl">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-6">Publicaciones</p>
          <h1 
            className="text-5xl md:text-6xl font-light leading-tight mb-6"
            style={{ fontFamily: 'var(--font-playfair), serif' }}
          >
            Inteligencia<br />
            <span className="text-[#c9a050]">Contractual</span>
          </h1>
          <p className="text-xl text-[#8a8a8a] leading-relaxed">
            Análisis, guías y estrategias para la gestión de riesgo en contrataciones públicas.
          </p>
        </div>
      </section>

      {/* Featured Post */}
      <section className="border-y border-[#1a1a1a] bg-[#0d0d0d]">
        <div className="max-w-7xl mx-auto px-8 py-16">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4 block">Destacado</span>
              <h2 className="text-3xl font-light mb-4">
                El Futuro de la Due Diligence en América Latina
              </h2>
              <p className="text-[#8a8a8a] leading-relaxed mb-6">
                Un informe exclusivo sobre cómo las tecnologías emergentes están transformando 
                la verificación de contrapartes en el sector legal y financiero latinoamericano.
              </p>
              <Link 
                href="/blog" 
                className="inline-flex items-center gap-2 text-[#c9a050] hover:text-[#d4aa5a] cursor-default"
                onClick={(e) => e.preventDefault()}
              >
                Leer artículo <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="aspect-video bg-[#1a1a1a] border border-[#2a2a2a]">
              <div className="w-full h-full flex items-center justify-center">
                <span className="text-[#5a5a5a] text-sm tracking-wide">Imagen Destacada</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Blog Grid */}
      <section className="max-w-7xl mx-auto px-8 py-24">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-[#1a1a1a]">
          {blogPosts.map((post) => (
            <article key={post.id} className="bg-[#0a0a0a] p-8 group">
              <div className="mb-6">
                <span className="text-xs tracking-[0.2em] uppercase text-[#c9a050]">{post.category}</span>
              </div>
              
              <h3 className="text-xl font-light mb-4 group-hover:text-[#c9a050] transition-colors cursor-default">
                  {post.title}
                </h3>
              
              <p className="text-sm text-[#8a8a8a] leading-relaxed mb-6">{post.excerpt}</p>
              
              <div className="flex items-center gap-4 text-xs text-[#5a5a5a]">
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" /> {post.author}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {post.readTime}
                </span>
              </div>
              
              <p className="text-xs text-[#5a5a5a] mt-4">{post.date}</p>
            </article>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-8 py-24 text-center">
          <h2 className="text-3xl font-light mb-6">Acceso Exclusivo</h2>
          <p className="text-[#8a8a8a] max-w-xl mx-auto mb-10">
            Obtenga acceso ilimitado a todos nuestros informes y análisis exclusivos 
            sobre riesgo contractual en el Perú.
          </p>
          <Link 
            href="/pricing" 
            className="inline-flex items-center gap-2 bg-[#c9a050] text-[#0a0a0a] px-8 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a]"
          >
            Ver Membership
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
              <Link href="/terminos" className="hover:text-[#e8e6e3]">Términos</Link>
              <Link href="/privacidad" className="hover:text-[#e8e6e3]">Privacidad</Link>
              <Link href="/pricing" className="hover:text-[#e8e6e3]">Membership</Link>
            </div>
            <p className="text-xs text-[#5a5a5a]">© 2026. Todos los derechos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
