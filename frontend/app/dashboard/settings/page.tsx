'use client';

import { useState, useEffect } from 'react';
import { Settings, User, Building2, Bell, Shield, Save, CheckCircle } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Loading from '@/components/ui/Loading';

interface UserProfile {
  email: string;
  full_name: string;
  company_name: string;
  ruc: string;
  plan_type: string;
  monthly_limit: number;
  monthly_requests: number;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    full_name: '',
    company_name: '',
    ruc: ''
  });

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Error al cargar perfil');

      const data = await response.json();
      setProfile(data);
      setFormData({
        full_name: data.full_name || '',
        company_name: data.company_name || '',
        ruc: data.ruc || ''
      });
    } catch (err) {
      setError('No se pudo cargar la información del perfil');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE}/auth/update-profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) throw new Error('Error al guardar cambios');

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError('Error al guardar los cambios');
    } finally {
      setSaving(false);
    }
  };

  const getPlanName = (plan: string) => {
    const plans: Record<string, string> = {
      'essential': 'Essential',
      'professional': 'Professional',
      'enterprise': 'Enterprise'
    };
    return plans[plan] || plan;
  };

  if (loading) {
    return <Loading fullScreen message="Cargando configuración" />;
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Cuenta</p>
          <h1 className="text-3xl font-light">Configuración</h1>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400">
            {error}
          </div>
        )}

        {saved && (
          <div className="mb-6 p-4 border border-green-900/50 bg-green-900/10 text-green-400 flex items-center gap-3">
            <CheckCircle className="h-5 w-5" />
            Cambios guardados exitosamente
          </div>
        )}

        <div className="grid gap-8">
          {/* Información del Plan */}
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-[#c9a050]" />
                <h2 className="text-lg">Plan Actual</h2>
              </div>
            </div>
            <div className="p-6">
              {profile && (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-light text-[#c9a050]">{getPlanName(profile.plan_type)}</p>
                    <p className="text-sm text-[#5a5a5a] mt-1">
                      {profile.monthly_requests.toLocaleString()} / {profile.monthly_limit.toLocaleString()} consultas este mes
                    </p>
                  </div>
                  <div className="w-48">
                    <div className="h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-[#c9a050] transition-all"
                        style={{ 
                          width: `${Math.min((profile.monthly_requests / profile.monthly_limit) * 100, 100)}%` 
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Perfil */}
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <User className="h-5 w-5 text-[#c9a050]" />
                <h2 className="text-lg">Información Personal</h2>
              </div>
            </div>
            <form onSubmit={handleSubmit} className="p-6">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm text-[#8a8a8a] mb-2">Email</label>
                  <input
                    type="email"
                    value={profile?.email || ''}
                    disabled
                    className="w-full bg-[#0f0f0f] border border-[#2a2a2a] px-4 py-3 text-[#5a5a5a] cursor-not-allowed"
                  />
                  <p className="text-xs text-[#5a5a5a] mt-1">El email no puede ser modificado</p>
                </div>

                <Input
                  label="Nombre Completo"
                  value={formData.full_name}
                  onChange={(v) => setFormData({ ...formData, full_name: v })}
                />
              </div>

              <div className="mt-6">
                <Button
                  type="submit"
                  disabled={saving}
                  icon={<Save className="h-4 w-4" />}
                >
                  {saving ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </div>
            </form>
          </div>

          {/* Empresa */}
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-[#c9a050]" />
                <h2 className="text-lg">Información de la Empresa</h2>
              </div>
            </div>
            <div className="p-6">
              <div className="grid md:grid-cols-2 gap-6">
                <Input
                  label="Nombre de la Empresa"
                  value={formData.company_name}
                  onChange={(v) => setFormData({ ...formData, company_name: v })}
                />
                <Input
                  label="RUC de la Empresa"
                  value={formData.ruc}
                  onChange={(v) => setFormData({ ...formData, ruc: v.replace(/\D/g, '').slice(0, 11) })}
                  maxLength={11}
                />
              </div>
            </div>
          </div>

          {/* Seguridad */}
          <div className="border border-[#1a1a1a]">
            <div className="p-6 border-b border-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <Settings className="h-5 w-5 text-[#c9a050]" />
                <h2 className="text-lg">Seguridad</h2>
              </div>
            </div>
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Cambiar Contraseña</p>
                  <p className="text-sm text-[#5a5a5a]">Actualiza tu contraseña de acceso</p>
                </div>
                <button className="text-sm text-[#c9a050] hover:text-[#d4aa5a] transition-colors">
                  Cambiar →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}