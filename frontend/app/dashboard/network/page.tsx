'use client';

import { useState, useEffect } from 'react';
import { Network, Plus, Trash2, Bell, CheckCircle, AlertTriangle, XCircle, Shield, ArrowLeft, AlertOctagon } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Loading from '@/components/ui/Loading';
import Link from 'next/link';
import type { Supplier, SupplierAlert, NetworkListResponse, AlertsResponse } from '@/types';

export default function NetworkPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [alerts, setAlerts] = useState<SupplierAlert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'suppliers' | 'alerts'>('suppliers');
  
  // Form state
  const [newRuc, setNewRuc] = useState('');
  const [newName, setNewName] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [addingSupplier, setAddingSupplier] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

  // Cargar datos
  useEffect(() => {
    fetchNetworkData();
  }, []);

  const fetchNetworkData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        setLoading(false);
        return;
      }

      // Fetch suppliers
      const suppliersRes = await fetch(`${API_BASE}/api/v1/network/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!suppliersRes.ok) {
        if (suppliersRes.status === 401) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          localStorage.removeItem('token');
          setLoading(false);
          return;
        }
        throw new Error('Error al cargar proveedores');
      }

      const suppliersData: NetworkListResponse = await suppliersRes.json();
      setSuppliers(suppliersData.suppliers);
      setUnreadCount(suppliersData.alerts_unread);

      // Fetch alerts
      const alertsRes = await fetch(`${API_BASE}/api/v1/network/alerts`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (alertsRes.ok) {
        const alertsData: AlertsResponse = await alertsRes.json();
        setAlerts(alertsData.alerts);
      }

      setError('');
    } catch (err) {
      console.error('Error fetching network data:', err);
      setError('Error de conexión. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const addSupplier = async () => {
    if (newRuc.length !== 11) {
      setError('El RUC debe tener 11 dígitos');
      return;
    }

    setAddingSupplier(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        setAddingSupplier(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/network/add`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ruc: newRuc,
          supplier_name: newName || undefined,
          notes: newNotes || undefined
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 409) {
          setError('Este RUC ya está en tu red de monitoreo');
        } else if (response.status === 401) {
          setError('Sesión expirada. Por favor inicie sesión nuevamente.');
          localStorage.removeItem('token');
        } else {
          setError(errorData.detail || 'Error al agregar proveedor');
        }
        setAddingSupplier(false);
        return;
      }

      const data = await response.json();
      
      // Reset form
      setNewRuc('');
      setNewName('');
      setNewNotes('');
      setShowAddForm(false);
      
      // Refresh data
      await fetchNetworkData();
    } catch (err) {
      console.error('Error adding supplier:', err);
      setError('Error de conexión. Intente nuevamente.');
    } finally {
      setAddingSupplier(false);
    }
  };

  const removeSupplier = async (ruc: string) => {
    if (!confirm(`¿Está seguro de eliminar el proveedor ${ruc} de tu red?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Sesión expirada. Por favor inicie sesión nuevamente.');
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/network/${ruc}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Error al eliminar proveedor');
        return;
      }

      // Refresh data
      await fetchNetworkData();
    } catch (err) {
      console.error('Error removing supplier:', err);
      setError('Error de conexión. Intente nuevamente.');
    }
  };

  const markAlertRead = async (alertId: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`${API_BASE}/api/v1/network/alerts/${alertId}/read`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        // Update local state
        setAlerts(prev => prev.map(a => 
          a.id === alertId ? { ...a, is_read: true } : a
        ));
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Error marking alert as read:', err);
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

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertOctagon className="h-5 w-5 text-red-400" />;
      case 'high':
        return <AlertTriangle className="h-5 w-5 text-orange-400" />;
      case 'medium':
        return <Bell className="h-5 w-5 text-amber-400" />;
      default:
        return <Bell className="h-5 w-5 text-blue-400" />;
    }
  };

  const getChangeTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      'score_change': 'Cambio en score',
      'osce_new_sanction': 'Nueva sanción OSCE',
      'tce_new_sanction': 'Nueva sanción TCE'
    };
    return labels[type] || type;
  };

  if (loading) return <Loading />;

  if (error && !suppliers.length && !alerts.length) {
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
              <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">Monitoreo</p>
              <h1 className="text-3xl font-light">Mi Red</h1>
            </div>
          </div>
          <Button
            onClick={() => setShowAddForm(!showAddForm)}
            variant="primary"
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Agregar Proveedor
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 border border-red-900/50 bg-red-900/10 text-red-400 text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> {error}
          </div>
        )}

        {/* Add Supplier Form */}
        {showAddForm && (
          <div className="border border-[#1a1a1a] p-8 mb-8">
            <h2 className="text-lg font-medium mb-6">Agregar Proveedor a Monitoreo</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
                <label className="block text-sm text-[#8a8a8a] mb-2">Nombre (opcional)</label>
                <Input
                  placeholder="Nombre del proveedor"
                  value={newName}
                  onChange={setNewName}
                />
              </div>
              <div>
                <label className="block text-sm text-[#8a8a8a] mb-2">Notas (opcional)</label>
                <Input
                  placeholder="Notas personalizadas"
                  value={newNotes}
                  onChange={setNewNotes}
                />
              </div>
            </div>
            <div className="flex gap-4">
              <Button
                onClick={addSupplier}
                disabled={addingSupplier || newRuc.length !== 11}
                variant="primary"
              >
                {addingSupplier ? 'Agregando...' : 'Agregar a Mi Red'}
              </Button>
              <Button
                onClick={() => setShowAddForm(false)}
                variant="outline"
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Network className="h-5 w-5 text-[#c9a050]" />
              <span className="text-[#8a8a8a] text-sm">Proveedores</span>
            </div>
            <p className="text-3xl font-light text-[#e8e6e3]">{suppliers.length}</p>
          </div>
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Bell className="h-5 w-5 text-[#c9a050]" />
              <span className="text-[#8a8a8a] text-sm">Alertas sin leer</span>
            </div>
            <p className="text-3xl font-light text-[#e8e6e3]">{unreadCount}</p>
          </div>
          <div className="border border-[#1a1a1a] p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Shield className="h-5 w-5 text-[#c9a050]" />
              <span className="text-[#8a8a8a] text-sm">Revisión diaria</span>
            </div>
            <p className="text-3xl font-light text-[#e8e6e3]">6:00 AM</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-8 border-b border-[#1a1a1a] mb-8">
          <button
            onClick={() => setActiveTab('suppliers')}
            className={`pb-4 text-sm tracking-wide transition-colors ${
              activeTab === 'suppliers'
                ? 'text-[#c9a050] border-b-2 border-[#c9a050]'
                : 'text-[#8a8a8a] hover:text-[#e8e6e3]'
            }`}
          >
            Proveedores ({suppliers.length})
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-4 text-sm tracking-wide transition-colors ${
              activeTab === 'alerts'
                ? 'text-[#c9a050] border-b-2 border-[#c9a050]'
                : 'text-[#8a8a8a] hover:text-[#e8e6e3]'
            }`}
          >
            Alertas ({alerts.length})
          </button>
        </div>

        {/* Suppliers Tab */}
        {activeTab === 'suppliers' && (
          <div>
            {suppliers.length > 0 ? (
              <div className="border border-[#1a1a1a] divide-y divide-[#1a1a1a]">
                {suppliers.map((supplier) => (
                  <div key={supplier.id} className="p-6 hover:bg-[#0d0d0d] transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-4 mb-2">
                          <p className="text-sm text-[#5a5a5a] font-mono">{supplier.ruc}</p>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getScoreColor(supplier.score)}`}>
                            {supplier.score}
                          </span>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getScoreColor(supplier.score)}`}>
                            {getRiskLabel(supplier.risk_level)}
                          </span>
                        </div>
                        <p className="text-lg text-[#e8e6e3] mb-2">
                          {supplier.supplier_name || 'Proveedor sin nombre'}
                        </p>
                        <div className="flex gap-4 text-sm text-[#5a5a5a]">
                          <span>OSCE: {supplier.osce_sanciones} sanciones</span>
                          <span>TCE: {supplier.tce_sanciones} sanciones</span>
                          <span>Agregado: {new Date(supplier.added_at).toLocaleDateString('es-PE')}</span>
                          {supplier.last_checked && (
                            <span>Última revisión: {new Date(supplier.last_checked).toLocaleDateString('es-PE')}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/dashboard?ruc=${supplier.ruc}`}
                          className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-[#c9a050] hover:text-[#c9a050] transition-colors"
                        >
                          <Shield className="h-4 w-4" />
                        </Link>
                        <button
                          onClick={() => removeSupplier(supplier.ruc)}
                          className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-red-500/50 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 border border-[#1a1a1a]">
                <Network className="w-12 h-12 text-[#5a5a5a] mx-auto mb-4" />
                <p className="text-[#8a8a8a] mb-2">No tienes proveedores en monitoreo</p>
                <p className="text-sm text-[#5a5a5a] mb-4">
                  Agrega proveedores para recibir alertas automáticas de cambios
                </p>
                <Button
                  onClick={() => setShowAddForm(true)}
                  variant="outline"
                  className="flex items-center gap-2 mx-auto"
                >
                  <Plus className="h-4 w-4" />
                  Agregar primer proveedor
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Alerts Tab */}
        {activeTab === 'alerts' && (
          <div>
            {alerts.length > 0 ? (
              <div className="border border-[#1a1a1a] divide-y divide-[#1a1a1a]">
                {alerts.map((alert) => (
                  <div 
                    key={alert.id} 
                    className={`p-6 hover:bg-[#0d0d0d] transition-colors ${
                      !alert.is_read ? 'bg-[#c9a050]/5' : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="mt-1">
                        {getAlertIcon(alert.severity)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <p className="text-sm font-medium text-[#e8e6e3]">
                            {getChangeTypeLabel(alert.change_type)}
                          </p>
                          <span className={`text-xs px-2 py-0.5 border ${getScoreColor(
                            alert.severity === 'critical' ? 10 : 
                            alert.severity === 'high' ? 30 : 
                            alert.severity === 'medium' ? 50 : 80
                          )}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                          {!alert.is_read && (
                            <span className="text-xs text-[#c9a050] border border-[#c9a050]/30 px-2 py-0.5">
                              NUEVA
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-[#8a8a8a] mb-1">
                          RUC: <span className="text-[#e8e6e3] font-mono">{alert.supplier_ruc}</span>
                          {alert.supplier_name && ` - ${alert.supplier_name}`}
                        </p>
                        {(alert.previous_status || alert.new_status) && (
                          <div className="flex items-center gap-2 text-sm mt-2">
                            {alert.previous_status && (
                              <span className="text-[#5a5a5a]">{alert.previous_status}</span>
                            )}
                            {alert.previous_status && alert.new_status && (
                              <span className="text-[#8a8a8a]">→</span>
                            )}
                            {alert.new_status && (
                              <span className="text-[#e8e6e3]">{alert.new_status}</span>
                            )}
                          </div>
                        )}
                        <p className="text-xs text-[#5a5a5a] mt-2">
                          {new Date(alert.created_at).toLocaleString('es-PE')}
                          {alert.email_sent && ' • Email enviado'}
                        </p>
                      </div>
                      {!alert.is_read && (
                        <button
                          onClick={() => markAlertRead(alert.id)}
                          className="p-2 border border-[#2a2a2a] text-[#8a8a8a] hover:border-[#c9a050] hover:text-[#c9a050] transition-colors"
                          title="Marcar como leída"
                        >
                          <CheckCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 border border-[#1a1a1a]">
                <Bell className="w-12 h-12 text-[#5a5a5a] mx-auto mb-4" />
                <p className="text-[#8a8a8a] mb-2">No hay alertas</p>
                <p className="text-sm text-[#5a5a5a]">
                  Las alertas aparecerán cuando detectemos cambios en tus proveedores monitoreados
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
