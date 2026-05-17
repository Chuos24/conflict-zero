'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Shield, Mail, MapPin, Phone, Send } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function ContactoPage() {
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    empresa: '',
    mensaje: ''
  });
  const [enviado, setEnviado] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setEnviado(true);
    setTimeout(() => setEnviado(false), 3000);
  };

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
            <Link href="/blog" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3]">Blog</Link>
            <Link href="/pricing" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3]">Membership</Link>
            <Link href="/login" className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3]">Acceso</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-8 pt-24 pb-16">
        <div className="max-w-3xl">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-6">Contacto</p>
          <h1 className="text-4xl md:text-5xl font-light leading-tight mb-6">
            Hablemos de <span className="text-[#c9a050]">Riesgo</span>
          </h1>
          <p className="text-xl text-[#8a8a8a] leading-relaxed">
            ¿Tiene preguntas sobre nuestros servicios? Estamos aquí para ayudarle.
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="max-w-7xl mx-auto px-8 pb-24">
        <div className="grid md:grid-cols-2 gap-px bg-[#1a1a1a]">
          {/* Formulario */}
          <div className="bg-[#0a0a0a] p-10">
            <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-8">Envíenos un Mensaje</p>
            
            {enviado ? (
              <div className="p-6 border border-green-500/30 bg-green-500/10 text-green-400">
                <p>Mensaje enviado correctamente. Le responderemos pronto.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <Input
                  label="Nombre"
                  value={formData.nombre}
                  onChange={(v) => setFormData({ ...formData, nombre: v })}
                  required
                />

                <Input
                  label="Email"
                  type="email"
                  value={formData.email}
                  onChange={(v) => setFormData({ ...formData, email: v })}
                  required
                />

                <Input
                  label="Empresa"
                  value={formData.empresa}
                  onChange={(v) => setFormData({ ...formData, empresa: v })}
                />

                <div>
                  <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Mensaje</label>
                  <textarea
                    value={formData.mensaje}
                    onChange={(e) => setFormData({ ...formData, mensaje: e.target.value })}
                    rows={4}
                    className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors resize-none"
                    required
                  />
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  icon={<Send className="h-4 w-4" />}
                >
                  Enviar Mensaje
                </Button>
              </form>
            )}
          </div>

          {/* Info */}
          <div className="bg-[#0a0a0a] p-10">
            <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-8">Información de Contacto</p>
            
            <div className="space-y-8">
              <div className="flex items-start gap-4">
                <Mail className="h-5 w-5 text-[#c9a050] mt-1" />
                <div>
                  <p className="text-sm text-[#8a8a8a] mb-1">Email</p>
                  <p>contacto@czperu.com</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <Phone className="h-5 w-5 text-[#c9a050] mt-1" />
                <div>
                  <p className="text-sm text-[#8a8a8a] mb-1">Teléfono</p>
                  <p>+51 1 555 0123</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <MapPin className="h-5 w-5 text-[#c9a050] mt-1" />
                <div>
                  <p className="text-sm text-[#8a8a8a] mb-1">Dirección</p>
                  <p>Av. Pardo y Aliaga 640<br/>San Isidro, Lima, Perú</p>
                </div>
              </div>
            </div>

            <div className="mt-12 pt-8 border-t border-[#1a1a1a]">
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-4">Horario de Atención</p>
              <p className="text-sm text-[#8a8a8a]">Lunes a Viernes: 9:00 - 18:00<br/>Sábados: 9:00 - 13:00</p>
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
