'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import Cookies from 'js-cookie';
import { Shield, Eye, EyeOff, Check } from 'lucide-react';

const plans: Record<string, { name: string; price: number }> = {
  essential: { name: 'Essential', price: 400 },
  professional: { name: 'Professional', price: 800 },
  enterprise: { name: 'Enterprise', price: 2500 },
};

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedPlan = searchParams.get('plan') || '';
  const planConfig = plans[selectedPlan];

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    company_name: '',
    ruc: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || '';
      const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, plan: selectedPlan }),
      });

      const data = await response.json();

      if (response.ok) {
        const loginResponse = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: formData.email, password: formData.password }),
        });
        const loginData = await loginResponse.json();
        
        if (loginResponse.ok) {
          Cookies.set('token', loginData.access_token, { expires: 1 });
          router.push('/dashboard');
        }
      } else {
        setError(data.detail || 'Error al registrar');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] py-16 px-8">
      <div className="max-w-md mx-auto">
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center gap-3">
            <Shield className="h-8 w-8 text-[#c9a050]" strokeWidth={1.5} />
            <span className="text-xl tracking-[0.2em] font-light uppercase">Conflict Zero</span>
          </Link>
        </div>

        {planConfig && (
          <div className="border border-[#c9a050]/30 bg-[#c9a050]/5 p-6 mb-8">
            <p className="text-xs tracking-[0.2em] uppercase text-[#c9a050] mb-2">Plan Seleccionado</p>
            <div className="flex justify-between items-baseline">
              <span className="text-lg">{planConfig.name}</span>
              <span className="text-[#c9a050]">${planConfig.price}/mes</span>
            </div>
          </div>
        )}

        <div className="border border-[#1a1a1a] p-10">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-4">Solicitud de Acceso</p>
          <h1 className="text-2xl font-light mb-8">Crear Cuenta</h1>

          {error && (
            <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 text-sm">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Nombre Completo *</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Email Corporativo *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Contraseña *</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#5a5a5a] hover:text-[#8a8a8a]"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Empresa *</label>
              <input
                type="text"
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">RUC de la Empresa</label>
              <input
                type="text"
                value={formData.ruc}
                onChange={(e) => setFormData({ ...formData, ruc: e.target.value.replace(/\D/g, '').slice(0, 11) })}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                maxLength={11}
              />
            </div>

            <div className="border border-[#1a1a1a] p-4 text-sm text-[#8a8a8a]">
              <div className="flex items-start gap-3">
                <Check className="h-4 w-4 text-[#c9a050] mt-0.5 flex-shrink-0" />
                <p>
                  Al solicitar acceso, acepta nuestros{' '}
                  <Link href="/terminos" className="text-[#c9a050] hover:underline">Términos de Servicio</Link>
                  {' '}y{' '}
                  <Link href="/privacidad" className="text-[#c9a050] hover:underline">Política de Privacidad</Link>.
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#c9a050] text-[#0a0a0a] py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors disabled:opacity-50"
            >
              {loading ? 'Procesando...' : 'Enviar Solicitud'}
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-[#1a1a1a] text-center">
            <p className="text-sm text-[#5a5a5a]">
              ¿Ya tiene cuenta?{' '}
              <Link href="/login" className="text-[#c9a050] hover:text-[#d4aa5a]">Acceder</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
