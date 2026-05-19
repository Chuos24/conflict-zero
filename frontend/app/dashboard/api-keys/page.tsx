'use client';

import { useState, useEffect } from 'react';
import { Key, Copy, Eye, EyeOff, RefreshCw, AlertCircle } from 'lucide-react';
import Button from '@/components/ui/Button';
import Loading from '@/components/ui/Loading';

interface ApiKeyData {
  key: string;
  created_at: string;
  last_used: string | null;
  usage_count: number;
}

export default function ApiKeysPage() {
  const [apiKey, setApiKey] = useState<ApiKeyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  useEffect(() => {
    fetchApiKey();
  }, []);

  const fetchApiKey = async () => {
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

      if (!response.ok) throw new Error('Error al cargar API key');

      const data = await response.json();
      
      if (data.api_key) {
        setApiKey({
          key: data.api_key,
          created_at: new Date().toISOString(),
          last_used: null,
          usage_count: 0
        });
      }
    } catch (err) {
      setError('No se pudo cargar la información de API');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (apiKey?.key) {
      navigator.clipboard.writeText(apiKey.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const regenerateKey = async () => {
    if (!confirm('¿Estás seguro de regenerar tu API key? La key anterior dejará de funcionar inmediatamente.')) {
      return;
    }

    setRegenerating(true);
    try {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE}/auth/regenerate-api-key`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Error al regenerar API key');

      const data = await response.json();
      setApiKey({
        key: data.api_key,
        created_at: new Date().toISOString(),
        last_used: null,
        usage_count: 0
      });
      setShowKey(true);
    } catch (err) {
      setError('Error al regenerar API key');
    } finally {
      setRegenerating(false);
    }
  };

  const maskKey = (key: string) => {
    if (key.length <= 8) return '****';
    return key.slice(0, 4) + '••••••••••••••••••••' + key.slice(-4);
  };

  if (loading) {
    return <Loading fullScreen message="Cargando API keys" />;
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Desarrolladores</p>
          <h1 className="text-3xl font-light">API Keys</h1>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 flex items-center gap-3">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        <div className="border border-[#1a1a1a]">
          <div className="p-8 border-b border-[#1a1a1a]">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 border border-[#c9a050]/30 bg-[#c9a050]/5">
                <Key className="h-6 w-6 text-[#c9a050]" />
              </div>
              <div>
                <h2 className="text-lg">Tu API Key</h2>
                <p className="text-sm text-[#5a5a5a]">Usa esta key para autenticar tus requests</p>
              </div>
            </div>

            {apiKey ? (
              <div className="space-y-6">
                <div className="bg-[#0f0f0f] border border-[#2a2a2a] p-4">
                  <div className="flex items-center justify-between gap-4">
                    <code className="text-[#c9a050] font-mono text-sm">
                      {showKey ? apiKey.key : maskKey(apiKey.key)}
                    </code>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowKey(!showKey)}
                        className="p-2 text-[#5a5a5a] hover:text-[#e8e6e3] transition-colors"
                        title={showKey ? 'Ocultar' : 'Mostrar'}
                      >
                        {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                      <button
                        onClick={copyToClipboard}
                        className="p-2 text-[#5a5a5a] hover:text-[#c9a050] transition-colors"
                        title="Copiar"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {copied && (
                  <p className="text-sm text-[#c9a050]">API key copiada al portapapeles</p>
                )}

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="p-4 border border-[#1a1a1a]">
                    <p className="text-[#5a5a5a] mb-1">Creada</p>
                    <p>{new Date(apiKey.created_at).toLocaleDateString('es-PE')}</p>
                  </div>
                  <div className="p-4 border border-[#1a1a1a]">
                    <p className="text-[#5a5a5a] mb-1">Último uso</p>
                    <p>{apiKey.last_used ? new Date(apiKey.last_used).toLocaleDateString('es-PE') : 'Nunca'}</p>
                  </div>
                  <div className="p-4 border border-[#1a1a1a]">
                    <p className="text-[#5a5a5a] mb-1">Requests</p>
                    <p>{apiKey.usage_count.toLocaleString()}</p>
                  </div>
                </div>

                <div className="pt-6 border-t border-[#1a1a1a]">
                  <Button
                    variant="danger"
                    onClick={regenerateKey}
                    disabled={regenerating}
                    icon={<RefreshCw className={`h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} />}
                    className="text-sm normal-case tracking-normal"
                  >
                    {regenerating ? 'Regenerando...' : 'Regenerar API Key'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-[#5a5a5a] mb-4">No tienes una API key activa</p>
                <Button
                  onClick={regenerateKey}
                  disabled={regenerating}
                >
                  {regenerating ? 'Generando...' : 'Generar API Key'}
                </Button>
              </div>
            )}
          </div>

          <div className="p-8">
            <h3 className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a] mb-4">Uso de la API</h3>
            <div className="bg-[#0f0f0f] border border-[#2a2a2a] p-4 overflow-x-auto">
              <pre className="text-sm text-[#8a8a8a]">
                <code>{`curl -X GET \\
  '${API_BASE}/verify/consulta-osce/20100000001' \\
  -H 'Authorization: Bearer ${apiKey?.key || 'YOUR_API_KEY'}'`}</code>
              </pre>
            </div>
          </div>
        </div>

        <div className="mt-8 p-6 border border-[#1a1a1a] bg-[#0f0f0f]">
          <h3 className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a] mb-4">Documentación</h3>
          <p className="text-sm text-[#5a5a5a] mb-4">
            Consulta nuestra documentación completa de la API para integrar Conflict Zero en tus aplicaciones.
          </p>
          <a 
            href="/docs" 
            className="inline-flex items-center gap-2 text-sm text-[#c9a050] hover:text-[#d4aa5a] transition-colors"
          >
            Ver documentación
            <span className="text-lg">→</span>
          </a>
        </div>
      </div>
    </div>
  );
}