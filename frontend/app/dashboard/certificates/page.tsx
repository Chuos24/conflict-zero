'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, Plus, Trash2, AlertTriangle, CheckCircle, XCircle, ArrowLeft, FileCheck, Clock } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Loading from '@/components/ui/Loading';
import Link from 'next/link';
import type { Certificate } from '@/types';

export default function CertificatesPage() {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  
  // Form state
  const [newRuc, setNewRuc] = useState('');
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newScore, setNewScore] = useState('85');
  const [newRiskLevel, setNewRiskLevel] = useState<'low' | 'medium' | 'high' | 'critical'>('low');
  const [newSunatStatus, setNewSunatStatus] = useState('ACTIVO');
  const [generating, setGenerating] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  useEffect(() => {
    fetchCertificates();
  }, []);

  const fetchCertificates = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/certificates/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          localStorage.removeItem('token');
          setLoading(false);
          return;
        }
        throw new Error('Error al cargar certificados');
      }

      const data = await response.json();
      setCertificates(data);
      setError('');
    } catch (err) {
      console.error('Error fetching certificates:', err);
      setError('Error de conexión. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const generateCertificate = async () => {
    if (newRuc.length !== 11) {
      setError('El RUC debe tener 11 dígitos');
      return;
    }

    const scoreNum = parseInt(newScore);
    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > 100) {
      setError('El score debe estar entre 0 y 100');
      return;
    }

    setGenerating(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        setGenerating(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/certificates/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ruc: newRuc,
          company_name: newCompanyName || undefined,
          score: scoreNum,
          risk_level: newRiskLevel,
          sunat_status: newSunatStatus || undefined,
          osce_sanctions_count: 0,
          tce_sanctions_count: 0
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 401) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          localStorage.removeItem('token');
        } else {
          setError(errorData.detail || 'Error al generar certificado');
        }
        setGenerating(false);
        return;
      }

      const data = await response.json();
      
      // Reset form
      setNewRuc('');
      setNewCompanyName('');
      setNewScore('85');
      setNewRiskLevel('low');
      setNewSunatStatus('ACTIVO');
      setShowGenerateForm(false);
      
      // Refresh data
      await fetchCertificates();
    } catch (err) {
      console.error('Error generating certificate:', err);
      setError('Error de conexión. Intente nuevamente.');
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = (code: string, ruc: string) => {
    const url = `${API_BASE}/api/v1/certificates/${code}/pdf`;
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.download = `certificado-kz-${ruc}-${code}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const revokeCertificate = async (certificateId: string) => {
    if (!confirm('¿Está seguro de revocar este certificado? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/certificates/${certificateId}/revoke`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Error al revocar certificado');
        return;
      }

      // Refresh data
      await fetchCertificates();
    } catch (err) {
      console.error('Error revoking certificate:', err);
      setError('Error de conexión. Intente nuevamente.');
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-400 border-green-500/30 bg-green-500/10';
    if (score >= 60) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    if (score >= 40) return 'text-orange-400 border-orange-500/30 bg-orange-500/10';
    return 'text-red-400 border-red-500/30 bg-red-500/10';
  };

  const getRiskLabel = (level: string): string => {
    const labels: Record<string, string> = {
      low: 'Bajo',
      medium: 'Medio',
      high: 'Alto',
      critical: 'Crítico'
    };
    return labels[level] || level;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'expired':
        return <Clock className="h-4 w-4 text-amber-400" />;
      case 'revoked':
        return <XCircle className="h-4 w-4 text-red-400" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      active: 'Vigente',
      expired: 'Expirado',
      revoked: 'Revocado'
    };
    return labels[status] || status;
  };

  const isExpired = (expiresAt?: string): boolean => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  if (loading) return <Loading />;

  if (error && !certificates.length) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <Link href="/login">
            <Button variant="outline">Iniciar Sesión</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-[#5a5a5a] hover:text-[#c9a050]">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Documentos</p>
              <h1 className="text-3xl font-light">Certificados</h1>
            </div>
          </div>
          <Button
            onClick={() => setShowGenerateForm(!showGenerateForm)}
            variant="primary"
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Generar Certificado
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> {error}
          </div>
        )}

        {/* Generate Form */}
        {showGenerateForm && (
          <div className="border border-[#1a1a1a] p-8 mb-8">
            <h2 className="text-lg font-medium mb-6">Generar Nuevo Certificado</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">RUC *</label>
                <Input
                  placeholder="11 dígitos"
                  value={newRuc}
                  onChange={(value) => setNewRuc(value.replace(/\D/g, '').slice(0, 11))}
                  maxLength={11}
                />
              </div>
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">Razón Social</label>
                <Input
                  placeholder="Nombre de la empresa"
                  value={newCompanyName}
                  onChange={setNewCompanyName}
                />
              </div>
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">Score (0-100) *</label>
                <Input
                  type="number"
                  placeholder="85"
                  value={newScore}
                  onChange={setNewScore}
                  maxLength={3}
                />
              </div>
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">Nivel de Riesgo *</label>
                <select
                  value={newRiskLevel}
                  onChange={(e) => setNewRiskLevel(e.target.value as 'low' | 'medium' | 'high' | 'critical')}
                  className="w-full bg-transparent border border-[#2a2a2a] px-4 py-2 text-sm text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none"
                >
                  <option value="low" className="bg-[#0a0a0a]">Bajo</option>
                  <option value="medium" className="bg-[#0a0a0a]">Medio</option>
                  <option value="high" className="bg-[#0a0a0a]">Alto</option>
                  <option value="critical" className="bg-[#0a0a0a]">Crítico</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">Estado SUNAT</label>
                <Input
                  placeholder="ACTIVO"
                  value={newSunatStatus}
                  onChange={setNewSunatStatus}
                />
              </div>
            </div>
            <div className="flex gap-4">
              <Button
                onClick={generateCertificate}
                disabled={generating || newRuc.length !== 11}
                variant="primary"
              >
                {generating ? 'Generando...' : 'Generar Certificado'}
              </Button>
              <Button
                onClick={() => setShowGenerateForm(false)}
                variant="outline"
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <FileCheck className="h-5 w-5 text-[#c9a050]" />
              <span className="text-[#8a8a8a] text-sm">Total Certificados</span>
            </div>
            <p className="text-3xl font-light text-[#e8e6e3]">{certificates.length}</p>
          </div>
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="text-[#8a8a8a] text-sm">Vigentes</span>
            </div>
            <p className="text-3xl font-light text-green-400">
              {certificates.filter(c => c.status === 'active' && !isExpired(c.expires_at)).length}
            </p>
          </div>
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Clock className="h-5 w-5 text-amber-400" />
              <span className="text-[#8a8a8a] text-sm">Expirados/Revocados</span>
            </div>
            <p className="text-3xl font-light text-amber-400">
              {certificates.filter(c => c.status !== 'active' || isExpired(c.expires_at)).length}
            </p>
          </div>
        </div>

        {/* Certificates List */}
        <div>
          {certificates.length > 0 ? (
            <div className="border border-[#1a1a1a] divide-y divide-[#1a1a1a]">
              {certificates.map((cert) => (
                <div key={cert.id} className="p-6 hover:bg-[#0d0d0d] transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-4 mb-2">
                        <p className="text-sm text-[#5a5a5a] font-mono">{cert.ruc}</p>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getScoreColor(cert.score)}`}>
                          {cert.score}
                        </span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getScoreColor(cert.score)}`}>
                          {getRiskLabel(cert.risk_level)}
                        </span>
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs border border-[#2a2a2a]">
                          {getStatusIcon(cert.status)}
                          {getStatusLabel(cert.status)}
                        </span>
                      </div>
                      <p className="text-lg text-[#e8e6e3] mb-2">
                        {cert.company_name || 'Empresa sin nombre'}
                      </p>
                      <div className="flex gap-4 text-sm text-[#5a5a5a]">
                        <span>Código: <span className="font-mono text-[#c9a050]">{cert.code.toUpperCase()}</span></span>
                        <span>Emitido: {new Date(cert.generated_at).toLocaleDateString('es-PE')}</span>
                        {cert.expires_at && (
                          <span>
                            Expira: {new Date(cert.expires_at).toLocaleDateString('es-PE')}
                            {isExpired(cert.expires_at) && (
                              <span className="text-red-400 ml-1">(Expirado)</span>
                            )}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => downloadPdf(cert.code, cert.ruc)}
                        className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-[#c9a050] hover:text-[#c9a050] transition-colors"
                        title="Descargar PDF"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      {cert.status === 'active' && !isExpired(cert.expires_at) && (
                        <button
                          onClick={() => revokeCertificate(cert.id)}
                          className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-red-500/50 hover:text-red-400 transition-colors"
                          title="Revocar certificado"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 border border-[#1a1a1a]">
              <FileText className="w-12 h-12 text-[#5a5a5a] mx-auto mb-4" />
              <p className="text-[#8a8a8a] mb-2">No tienes certificados generados</p>
              <p className="text-sm text-[#5a5a5a] mb-4">
                Genera certificados de verificación para tus proveedores
              </p>
              <Button
                onClick={() => setShowGenerateForm(true)}
                variant="outline"
                className="flex items-center gap-2 mx-auto"
              >
                <Plus className="h-4 w-4" />
                Generar primer certificado
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
