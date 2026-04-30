'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/components/auth-provider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertTriangle, Bell, Plus, Search, Trash2, TrendingUp, Shield, AlertCircle } from 'lucide-react';
import { API_URL } from '@/lib/config';

interface Supplier {
  id: string;
  supplier_ruc: string;
  supplier_name: string | null;
  alias: string | null;
  notes: string | null;
  tags: string[];
  current_score: number | null;
  current_status: {
    sunat_status: string;
    sunat_debt: number;
    osce_inhabilitado: boolean;
    osce_sanciones_vigentes: number;
    tce_sanciones_count: number;
    snapshot_date: string;
  } | null;
  has_pending_alerts: boolean;
  created_at: string;
}

interface Alert {
  id: string;
  supplier_ruc: string;
  supplier_name: string | null;
  change_type: string;
  previous_status: string | null;
  new_status: string | null;
  severity: string;
  is_read: boolean;
  created_at: string;
}

interface NetworkStats {
  total_suppliers: number;
  limit: number;
  unread_alerts: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

export default function NetworkPage() {
  const { token } = useAuth();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<NetworkStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [newRuc, setNewRuc] = useState('');
  const [newAlias, setNewAlias] = useState('');
  const [activeTab, setActiveTab] = useState<'suppliers' | 'alerts'>('suppliers');
  const [showAddDialog, setShowAddDialog] = useState(false);

  const fetchNetwork = async () => {
    try {
      const [suppliersRes, alertsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/v3/network/`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v3/network/alerts?unread_only=true`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v3/network/stats`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (suppliersRes.ok) setSuppliers(await suppliersRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (error) {
      console.error('Error fetching network:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchNetwork();
  }, [token]);

  const addSupplier = async () => {
    if (!newRuc || newRuc.length !== 11) return;
    
    try {
      const res = await fetch(`${API_URL}/api/v3/network/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          supplier_ruc: newRuc,
          supplier_name: null,
          alias: newAlias || null,
          notes: null,
          tags: []
        })
      });

      if (res.ok) {
        setNewRuc('');
        setNewAlias('');
        setShowAddDialog(false);
        fetchNetwork();
      } else {
        const error = await res.json();
        alert(error.detail || 'Error al agregar proveedor');
      }
    } catch (error) {
      console.error('Error adding supplier:', error);
    }
  };

  const removeSupplier = async (ruc: string) => {
    if (!confirm('¿Eliminar este proveedor de tu red?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/v3/network/${ruc}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) fetchNetwork();
    } catch (error) {
      console.error('Error removing supplier:', error);
    }
  };

  const markAlertRead = async (alertId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v3/network/alerts/${alertId}/read`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) fetchNetwork();
    } catch (error) {
      console.error('Error marking alert read:', error);
    }
  };

  const getRiskColor = (score: number | null) => {
    if (score === null) return 'bg-gray-500';
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getRiskLabel = (score: number | null) => {
    if (score === null) return 'Sin datos';
    if (score >= 80) return 'Bajo';
    if (score >= 60) return 'Moderado';
    if (score >= 40) return 'Alto';
    return 'Crítico';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Cargando...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Mi Red</h1>
          <p className="text-gray-400 mt-1">
            Monitorea tus proveedores y recibe alertas de cambios
          </p>
        </div>
        <Button
          onClick={() => setShowAddDialog(true)}
          className="bg-[#c9a961] hover:bg-[#b8984f] text-black"
        >
          <Plus className="w-4 h-4 mr-2" />
          Agregar Proveedor
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Proveedores</p>
                  <p className="text-2xl font-bold text-white">
                    {stats.total_suppliers} / {stats.limit}
                  </p>
                </div>
                <Shield className="w-8 h-8 text-[#c9a961]" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Alertas</p>
                  <p className="text-2xl font-bold text-white">{stats.unread_alerts}</p>
                </div>
                <Bell className="w-8 h-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Riesgo Alto</p>
                  <p className="text-2xl font-bold text-red-500">{stats.high_risk_count}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Riesgo Medio</p>
                  <p className="text-2xl font-bold text-yellow-500">{stats.medium_risk_count}</p>
                </div>
                <AlertCircle className="w-8 h-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-4 border-b border-[#2a2a2a]">
        <button
          onClick={() => setActiveTab('suppliers')}
          className={`pb-2 px-4 ${
            activeTab === 'suppliers'
              ? 'text-[#c9a961] border-b-2 border-[#c9a961]'
              : 'text-gray-400'
          }`}
        >
          Proveedores ({suppliers.length})
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-2 px-4 ${
            activeTab === 'alerts'
              ? 'text-[#c9a961] border-b-2 border-[#c9a961]'
              : 'text-gray-400'
          }`}
        >
          Alertas ({alerts.length})
        </button>
      </div>

      {/* Suppliers Tab */}
      {activeTab === 'suppliers' && (
        <div className="space-y-4">
          {suppliers.length === 0 ? (
            <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
              <CardContent className="p-8 text-center">
                <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">
                  No tienes proveedores en tu red. Agrega tu primer RUC para empezar a monitorear.
                </p>
              </CardContent>
            </Card>
          ) : (
            suppliers.map((supplier) => (
              <Card
                key={supplier.id}
                className={`bg-[#1a1a1a] border-[#2a2a2a] ${
                  supplier.has_pending_alerts ? 'border-orange-500/50' : ''
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-white">
                          {supplier.alias || supplier.supplier_name || supplier.supplier_ruc}
                        </h3>
                        {supplier.has_pending_alerts && (
                          <Badge className="bg-orange-500/20 text-orange-400">
                            <Bell className="w-3 h-3 mr-1" />
                            Alerta
                          </Badge>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm mt-1">RUC: {supplier.supplier_ruc}</p>
                      
                      {supplier.current_status && (
                        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
                          <div className="bg-[#0a0a0a] rounded p-2">
                            <p className="text-xs text-gray-500">Score</p>
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${getRiskColor(supplier.current_score)}`} />
                              <span className="text-sm font-medium text-white">
                                {supplier.current_score || 'N/A'}
                              </span>
                            </div>
                          </div>
                          <div className="bg-[#0a0a0a] rounded p-2">
                            <p className="text-xs text-gray-500">OSCE</p>
                            <p className={`text-sm font-medium ${
                              supplier.current_status.osce_inhabilitado 
                                ? 'text-red-400' 
                                : 'text-green-400'
                            }`}>
                              {supplier.current_status.osce_inhabilitado ? 'Inhabilitado' : 'Habilitado'}
                            </p>
                          </div>
                          <div className="bg-[#0a0a0a] rounded p-2">
                            <p className="text-xs text-gray-500">Deuda SUNAT</p>
                            <p className="text-sm font-medium text-white">
                              S/ {supplier.current_status.sunat_debt?.toLocaleString() || '0'}
                            </p>
                          </div>
                          <div className="bg-[#0a0a0a] rounded p-2">
                            <p className="text-xs text-gray-500">Sanciones</p>
                            <p className="text-sm font-medium text-white">
                              OSCE: {supplier.current_status.osce_sanciones_vigentes || 0} | 
                              TCE: {supplier.current_status.tce_sanciones_count || 0}
                            </p>
                          </div>
                        </div>
                      )}

                      {supplier.tags && supplier.tags.length > 0 && (
                        <div className="flex gap-2 mt-3">
                          {supplier.tags.map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSupplier(supplier.supplier_ruc)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {alerts.length === 0 ? (
            <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
              <CardContent className="p-8 text-center">
                <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">
                  No tienes alertas pendientes. Tus proveedores están estables.
                </p>
              </CardContent>
            </Card>
          ) : (
            alerts.map((alert) => (
              <Card
                key={alert.id}
                className="bg-[#1a1a1a] border-[#2a2a2a]"
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge className={getSeverityColor(alert.severity)}>
                          {alert.severity}
                        </Badge>
                        <span className="text-sm text-gray-400">
                          {alert.supplier_name || alert.supplier_ruc}
                        </span>
                      </div>
                      <h4 className="text-white font-medium mt-2">
                        {alert.change_type === 'osce_inhabilitado' && 'Inhabilitación OSCE detectada'}
                        {alert.change_type === 'tce_nueva_sancion' && 'Nueva sanción TCE'}
                        {alert.change_type === 'osce_nueva_sancion' && 'Nueva sanción OSCE'}
                        {alert.change_type === 'sunat_deuda_aumento' && 'Aumento de deuda SUNAT'}
                        {alert.change_type === 'sunat_cambio_estado' && 'Cambio de estado SUNAT'}
                      </h4>
                      {alert.previous_status && alert.new_status && (
                        <p className="text-sm text-gray-400 mt-1">
                          {alert.previous_status} → {alert.new_status}
                        </p>
                      )}
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(alert.created_at).toLocaleString('es-PE')}
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => markAlertRead(alert.id)}
                      className="border-[#c9a961] text-[#c9a961] hover:bg-[#c9a961]/10"
                    >
                      Marcar leída
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Add Supplier Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="bg-[#1a1a1a] border-[#2a2a2a] text-white">
          <DialogHeader>
            <DialogTitle>Agregar Proveedor a tu Red</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-400">RUC (11 dígitos)</label>
              <Input
                value={newRuc}
                onChange={(e) => setNewRuc(e.target.value)}
                placeholder="20100000001"
                maxLength={11}
                className="bg-[#0a0a0a] border-[#2a2a2a] text-white"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400">Alias (opcional)</label>
              <Input
                value={newAlias}
                onChange={(e) => setNewAlias(e.target.value)}
                placeholder="Mi proveedor principal"
                className="bg-[#0a0a0a] border-[#2a2a2a] text-white"
              />
            </div>
            <Button
              onClick={addSupplier}
              disabled={newRuc.length !== 11}
              className="w-full bg-[#c9a961] hover:bg-[#b8984f] text-black"
            >
              <Plus className="w-4 h-4 mr-2" />
              Agregar a Mi Red
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
