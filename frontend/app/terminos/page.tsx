'use client';

import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export default function TerminosPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3]">
      {/* Header */}
      <header className="border-b border-[#1a1a1a]">
        <div className="max-w-4xl mx-auto px-8 h-20 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-[#c9a050]" strokeWidth={1.5} />
            <span className="text-lg tracking-[0.2em] font-light uppercase">Conflict Zero</span>
          </Link>
          <Link href="/pricing" className="flex items-center gap-2 text-sm text-[#8a8a8a] hover:text-[#e8e6e3]">
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-24">
        <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-6">Legales</p>
        <h1 className="text-4xl font-light mb-16">Términos de Servicio</h1>

        <div className="space-y-12 text-[#b0b0b0] leading-relaxed">
          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">1. Naturaleza del Servicio</h2>
            <p className="mb-4">
              Conflict Zero es un servicio de inteligencia de riesgo diseñado exclusivamente para profesionales 
              del derecho, consultoras de due diligence, fondos de inversión y entidades financieras. 
              El acceso está restringido y sujeto a verificación de identidad.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">2. Membresía y Acceso</h2>
            <p className="mb-4">
              El servicio opera bajo modelo de membresía exclusiva. No existe plan gratuito. 
              Todos los miembros deben completar un proceso de verificación que incluye:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Verificación de identidad personal</li>
              <li>Verificación de empresa o firma</li>
              <li>Declaración de propósito de uso</li>
              <li>Aceptación de cláusulas de confidencialidad</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">3. Uso Aceptable</h2>
            <p className="mb-4">
              El servicio debe utilizarse únicamente para fines legales y legítimos de due diligence, 
              verificación de contrapartes y gestión de riesgo. Queda estrictamente prohibido:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>El uso del servicio para actividades ilícitas</li>
              <li>La reventa o redistribución de datos obtenidos</li>
              <li>El acceso automatizado no autorizado</li>
              <li>El uso para stalking, acoso o espionaje industrial</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">4. Precios y Facturación</h2>
            <p className="mb-4">
              Los precios están expresados en dólares americanos (USD). La facturación se realiza 
              mensualmente por adelantado. Los pagos son no reembolsables. El incumplimiento de pago 
              resultará en la suspensión inmediata del acceso.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">5. Limitación de Responsabilidad</h2>
            <p className="mb-4">
              Los datos proporcionados provienen de fuentes oficiales (SUNAT, OSCE, TCE). 
              Conflict Zero no garantiza la disponibilidad ininterrumpida del servicio. 
              La responsabilidad máxima se limita al monto pagado por el mes en curso.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">6. Terminación</h2>
            <p className="mb-4">
              Conflict Zero se reserva el derecho de terminar el acceso sin previo aviso en caso 
              de violación de estos términos. El miembro puede cancelar su membresía con 30 días 
              de anticipación.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">7. Jurisdicción</h2>
            <p className="mb-4">
              Estos términos se rigen por las leyes de la República del Perú. Cualquier disputa 
              será resuelta en los tribunales de Lima.
            </p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-[#1a1a1a]">
          <p className="text-sm text-[#5a5a5a]">
            Última actualización: Marzo 2026
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1a1a1a]">
        <div className="max-w-4xl mx-auto px-8 py-12">
          <div className="flex justify-between items-center">
            <p className="text-xs text-[#5a5a5a]">© 2026 Conflict Zero. Todos los derechos reservados.</p>
            <div className="flex gap-8 text-xs text-[#8a8a8a]">
              <Link href="/terminos" className="text-[#e8e6e3]">Términos</Link>
              <Link href="/privacidad" className="hover:text-[#e8e6e3]">Privacidad</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
