'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Check, Shield, Lock, FileText, Phone } from 'lucide-react';
import Button from '@/components/ui/Button';

const plans = [
  {
    name: 'Essential',
    price: 400,
    description: 'Para oficinas de abogados boutique y consultoras',
    requests: 1000,
    features: [
      '1,000 consultas mensuales',
      'Datos SUNAT en tiempo real',
      'Sanciones OSCE/TCE completas',
      'Score de riesgo avanzado',
      'Certificados PDF oficiales',
      'Historial de consultas (90 días)',
      'Soporte email (24h)',
    ],
    cta: 'Solicitar Acceso',
    ctaLink: '/register?plan=essential',
  },
  {
    name: 'Professional',
    price: 800,
    description: 'Para empresas de due diligence y fondos de inversión',
    requests: 5000,
    features: [
      '5,000 consultas mensuales',
      'Datos SUNAT en tiempo real',
      'Sanciones OSCE/TCE completas',
      'Score de riesgo personalizado',
      'Certificados PDF oficiales',
      'Historial ilimitado',
      'API REST completa',
      'Bulk upload (Excel/CSV)',
      'Soporte telefónico',
    ],
    cta: 'Solicitar Acceso',
    ctaLink: '/register?plan=professional',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 2500,
    description: 'Para bancos de inversión y consultoras Big Four',
    requests: 'Ilimitado',
    features: [
      'Consultas ilimitadas',
      'Datos SUNAT en tiempo real',
      'Sanciones OSCE/TCE + alertas',
      'Score de riesgo personalizado',
      'Certificados PDF oficiales',
      'Historial ilimitado',
      'API REST + Webhooks',
      'Bulk upload + Integraciones',
      'Manager de cuenta dedicado',
      'SLA 99.9% garantizado',
    ],
    cta: 'Contactar Director',
    ctaLink: 'mailto:director@czperu.com',
  },
];

export default function PricingPage() {
  const [hoveredPlan, setHoveredPlan] = useState<string | null>(null);

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
            <Link href="/login" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3] transition-colors">
              Acceso Clientes
            </Link>
            <Button
              onClick={() => window.location.href = '/register'}
              variant="secondary"
            >
              Solicitar Acceso
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-8 pt-24 pb-16">
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-6">Membership</p>
          <h1 className="text-4xl md:text-5xl font-light leading-tight mb-6">
            Acceso Exclusivo a<br />Inteligencia de Riesgo
          </h1>
          <p className="text-[#8a8a8a] text-lg leading-relaxed">
            Servicio diseñado para profesionales que requieren información 
            confiable y verificada. Sin planes gratuitos. Solo calidad.
          </p>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="border-y border-[#1a1a1a] bg-[#0d0d0d]">
        <div className="max-w-7xl mx-auto px-8 py-12">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <Lock className="h-6 w-6 text-[#c9a050] mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-sm text-[#8a8a8a]">Datos Encriptados</p>
            </div>
            <div>
              <FileText className="h-6 w-6 text-[#c9a050] mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-sm text-[#8a8a8a]">Fuentes Oficiales</p>
            </div>
            <div>
              <Phone className="h-6 w-6 text-[#c9a050] mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-sm text-[#8a8a8a]">Soporte Dedicado</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="max-w-7xl mx-auto px-8 py-24">
        <div className="grid md:grid-cols-3 gap-px bg-[#1a1a1a]">
          {plans.map((plan) => (
            <div 
              key={plan.name}
              className={`relative bg-[#0a0a0a] p-10 flex flex-col ${
                plan.featured ? 'md:-mt-4 md:mb-4' : ''
              }`}
              onMouseEnter={() => setHoveredPlan(plan.name)}
              onMouseLeave={() => setHoveredPlan(null)}
            >
              {plan.featured && (
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#c9a050] to-transparent" />
              )}

              <div className="mb-10">
                <p className="text-[#8a8a8a] text-xs tracking-[0.2em] uppercase mb-4">{plan.name}</p>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="text-4xl font-light">${plan.price}</span>
                  <span className="text-[#8a8a8a]">/mes</span>
                </div>
                <p className="text-sm text-[#8a8a8a] leading-relaxed">{plan.description}</p>
              </div>

              <div className="flex-1">
                <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-6">
                  {typeof plan.requests === 'number' 
                    ? `${plan.requests.toLocaleString()} consultas incluidas`
                    : 'Consultas ilimitadas'
                  }
                </p>
                <ul className="space-y-4">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <Check className="h-4 w-4 text-[#c9a050] mt-0.5 flex-shrink-0" strokeWidth={1.5} />
                      <span className="text-[#b0b0b0]">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <Link
                href={plan.ctaLink}
                className={`mt-10 w-full text-center py-4 text-sm tracking-[0.1em] uppercase transition-all border ${
                  plan.featured || hoveredPlan === plan.name
                    ? 'border-[#c9a050] bg-[#c9a050] text-[#0a0a0a]'
                    : 'border-[#2a2a2a] text-[#e8e6e3] hover:border-[#c9a050]'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Terms Notice */}
      <section className="border-t border-[#1a1a1a] bg-[#0d0d0d]">
        <div className="max-w-7xl mx-auto px-8 py-16">
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Membresía</p>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">
                Todos los planes requieren verificación de identidad. 
                El acceso es exclusivo para profesionales y empresas registradas.
                Precios en dólares americanos. Facturación mensual o anual.
              </p>
            </div>
            <div>
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Garantía</p>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">
                Los datos provienen directamente de SUNAT, OSCE y TCE. 
                Garantizamos la precisión de la información proporcionada.
                Certificados con validez legal para procesos de due diligence.
              </p>
            </div>
          </div>
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
              <Link href="/terminos" className="hover:text-[#e8e6e3] transition-colors">Términos de Servicio</Link>
              <Link href="/privacidad" className="hover:text-[#e8e6e3] transition-colors">Política de Privacidad</Link>
              <Link href="/contacto" className="hover:text-[#e8e6e3] transition-colors">Contacto</Link>
            </div>
            <p className="text-xs text-[#5a5a5a]">© 2026. Todos los derechos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
