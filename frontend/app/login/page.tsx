'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import Cookies from 'js-cookie';
import { Shield, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || '';
      const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        Cookies.set('token', data.access_token, { expires: 1 });
        router.push('/dashboard');
      } else {
        setError(data.detail || 'Credenciales inválidas');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center gap-3">
            <Shield className="h-8 w-8 text-[#c9a050]" strokeWidth={1.5} />
            <span className="text-xl tracking-[0.2em] font-light uppercase">Conflict Zero</span>
          </Link>
        </div>

        <div className="border border-[#1a1a1a] p-10">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-4">Acceso</p>
          <h1 className="text-2xl font-light mb-8">Iniciar Sesión</h1>

          {error && (
            <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 text-sm">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">Contraseña</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
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

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#c9a050] text-[#0a0a0a] py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors disabled:opacity-50"
            >
              {loading ? 'Accediendo...' : 'Acceder'}
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-[#1a1a1a] text-center">
            <p className="text-sm text-[#5a5a5a]">
              ¿No tiene cuenta?{' '}
              <Link href="/register" className="text-[#c9a050] hover:text-[#d4aa5a]">
                Solicitar acceso
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
