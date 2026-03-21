'use client';

import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export default function PrivacidadPage() {
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
        <h1 className="text-4xl font-light mb-16">Política de Privacidad</h1>

        <div className="space-y-12 text-[#b0b0b0] leading-relaxed">
          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">1. Compromiso con la Privacidad</h2>
            <p className="mb-4">
              Conflict Zero opera bajo los más altos estándares de confidencialidad. Entendemos 
              que nuestros clientes manejan información sensible y nos comprometemos a proteger 
              tanto sus datos como los de sus consultas.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">2. Información Recopilada</h2>
            <p className="mb-4">
              Recopilamos únicamente la información necesaria para la prestación del servicio:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Datos de identificación corporativa y personal (verificación KYC)</li>
              <li>Historial de consultas realizadas</li>
              <li>Información de facturación</li>
              <li>Logs de acceso (IP, timestamp, dispositivo)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">3. Uso de la Información</h2>
            <p className="mb-4">
              La información recopilada se utiliza exclusivamente para:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Prestación del servicio de inteligencia de riesgo</li>
              <li>Verificación de identidad y prevención de fraude</li>
              <li>Facturación y cumplimiento fiscal</li>
              <li>Mejora continua del servicio</li>
            </ul>
            <p className="mt-4">
              <strong className="text-[#e8e6e3]">No vendemos ni compartimos</strong> su información con terceros 
              para fines comerciales.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">4. Seguridad de Datos</h2>
            <p className="mb-4">
              Implementamos medidas de seguridad de grado empresarial:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Encriptación AES-256 en tránsito y reposo</li>
              <li>Acceso restringido por autenticación multifactor</li>
              <li>Auditorías de seguridad periódicas</li>
              <li>Servidores en infraestructura AWS con certificación SOC 2</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">5. Retención y Eliminación</h2>
            <p className="mb-4">
              Los datos se retienen durante el período de membresía activa más 7 años 
              (requerimiento legal peruano). Los datos de consultas individuales pueden ser 
              eliminados previa solicitud formal, excepto cuando exista obligación legal de conservación.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">6. Derechos del Usuario</h2>
            <p className="mb-4">
              Usted tiene derecho a:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Acceder a sus datos personales</li>
              <li>Rectificar información inexacta</li>
              <li>Solicitar eliminación de datos (con limitaciones legales)</li>
              <li>Oponerse al procesamiento de sus datos</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">7. Cambios en la Política</h2>
            <p className="mb-4">
              Cualquier modificación a esta política será notificada con 30 días de anticipación 
              vía email. El uso continuado del servicio después de los cambios constituye aceptación.
            </p>
          </section>

          <section>
            <h2 className="text-lg text-[#e8e6e3] mb-4 tracking-wide">8. Contacto</h2>
            <p className="mb-4">
              Para consultas sobre privacidad, contacte a nuestro Oficial de Protección de Datos:
            </p>
            <p className="text-[#e8e6e3]">
              Email: dpo@czperu.com
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
              <Link href="/terminos" className="hover:text-[#e8e6e3]">Términos</Link>
              <Link href="/privacidad" className="text-[#e8e6e3]">Privacidad</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
