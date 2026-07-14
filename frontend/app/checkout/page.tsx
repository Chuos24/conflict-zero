'use client';

import { useState, useEffect, useCallback } from 'react';
import { Check, CreditCard, Shield, Zap, Building2, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { payments } from '@/lib/api';

interface Plan {
  id: string;
  name: string;
  price: number;
  monthly_limit: number;
  features: string[];
  highlighted?: boolean;
}

interface CulqiConfig {
  enabled: boolean;
  public_key: string | null;
  currency: string;
  plans: Record<string, { price: number; name: string }>;
}

const plans: Plan[] = [
  {
    id: 'essential',
    name: 'Essential',
    price: 400,
    monthly_limit: 1000,
    features: [
      '1,000 verificaciones/mes',
      'Historial 90 días',
      'Certificados PDF',
      'Soporte por email',
      'Comparar hasta 2 RUCs'
    ]
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 800,
    monthly_limit: 5000,
    highlighted: true,
    features: [
      '5,000 verificaciones/mes',
      'Historial ilimitado',
      'Certificados PDF',
      'Soporte prioritario',
      'API Access',
      'Carga masiva',
      'Comparar hasta 5 RUCs',
      'Scoring personalizado'
    ]
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 2500,
    monthly_limit: 100000,
    features: [
      '100,000+ verificaciones/mes',
      'Historial ilimitado',
      'Certificados PDF',
      'Soporte dedicado',
      'API Access',
      'Carga masiva',
      'Webhooks',
      'Comparar hasta 10 RUCs',
      'Manager dedicado'
    ]
  }
];

// Cargar script de Culqi.js dinámicamente
function loadCulqiScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') {
      reject(new Error('Window no disponible'));
      return;
    }
    // @ts-ignore
    if (window.Culqi) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://js.culqi.com/checkout-js/v4/checkout.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('No se pudo cargar Culqi.js'));
    document.head.appendChild(script);
  });
}

export default function CheckoutPage() {
  const [selectedPlan, setSelectedPlan] = useState<string>('professional');
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'transfer'>('card');
  const [processing, setProcessing] = useState(false);
  const [step, setStep] = useState<'select' | 'payment' | 'success'>('select');
  const [culqiConfig, setCulqiConfig] = useState<CulqiConfig | null>(null);
  const [culqiLoaded, setCulqiLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlanData = plans.find(p => p.id === selectedPlan);

  // Obtener configuración de Culqi del backend
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const { data } = await payments.config();
        setCulqiConfig(data);
      } catch (err) {
        console.warn('No se pudo obtener config de pagos:', err);
      }
    };
    fetchConfig();
  }, []);

  // Cargar Culqi.js cuando se selecciona método de pago tarjeta
  useEffect(() => {
    if (paymentMethod === 'card' && culqiConfig?.enabled && !culqiLoaded) {
      loadCulqiScript()
        .then(() => setCulqiLoaded(true))
        .catch(err => console.error('Error cargando Culqi:', err));
    }
  }, [paymentMethod, culqiConfig, culqiLoaded]);

  const handleContinue = () => {
    setStep('payment');
    setError(null);
  };

  // Inicializar y abrir Culqi Checkout
  const openCulqiCheckout = useCallback(() => {
    if (typeof window === 'undefined') return;
    // @ts-ignore
    const Culqi = window.Culqi;
    if (!Culqi || !culqiConfig?.public_key || !selectedPlanData) return;

    const amount = selectedPlanData.price * 100; // Culqi usa céntimos

    const settings = {
      title: 'Conflict Zero',
      currency: culqiConfig.currency || 'PEN',
      amount: amount,
      order: `plan-${selectedPlan}-${Date.now()}`,
      xculqirsapublickey: culqiConfig.public_key,
      description: `Plan ${selectedPlanData.name} — Conflict Zero`,
      // @ts-ignore
      clientId: ' conflict-zero-client',
      paymentMethods: {
        tarjeta: true,
        yape: true,
        billetera: false,
        bancaMovil: false,
        agente: false,
        cuotealo: false,
      },
      options: {
        lang: 'es',
        modal: true,
        buttons: true,
        menubar: true,
        installments: true,
        paymentMethods: {
          tarjeta: true,
          yape: true,
        },
      },
      // @ts-ignore
      appearance: {
        theme: 'dark',
        rules: {
          'body-background': '#0a0a0a',
          'button-background': '#c9a050',
          'button-text': '#0a0a0a',
        }
      }
    };

    Culqi.settings(settings);

    // @ts-ignore
    Culqi.error = function(error: any) {
      console.error('Culqi error:', error);
      setError(error.user_message || 'Error en el pago. Intente nuevamente.');
      setProcessing(false);
    };

    // @ts-ignore
    Culqi.token = async function(token: any) {
      if (token.id) {
        try {
          const result = await payments.charge(token.id, selectedPlan);
          if (result.data.success) {
            setStep('success');
          } else {
            setError(result.data.detail || 'Error procesando el pago');
          }
        } catch (err: any) {
          setError(err.response?.data?.detail || 'Error procesando el pago');
        } finally {
          setProcessing(false);
        }
      }
    };

    Culqi.open();
  }, [culqiConfig, selectedPlan, selectedPlanData]);

  const handlePayment = async () => {
    setProcessing(true);
    setError(null);

    if (paymentMethod === 'card') {
      if (!culqiConfig?.enabled) {
        setError('Pasarela de pagos no configurada. Contacte a soporte.');
        setProcessing(false);
        return;
      }
      openCulqiCheckout();
      return; // Culqi maneja el callback
    }

    // Transferencia bancaria - simulación (requiere confirmación manual)
    await new Promise(resolve => setTimeout(resolve, 1500));
    setProcessing(false);
    setStep('success');
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
        <div className="max-w-md mx-auto text-center pt-20">
          <div className="w-20 h-20 rounded-full border-2 border-[#c9a050] flex items-center justify-center mx-auto mb-8">
            <Check className="h-10 w-10 text-[#c9a050]" />
          </div>
          <h1 className="text-3xl font-light mb-4">¡Suscripción Exitosa!</h1>
          <p className="text-[#8a8a8a] mb-8">
            Tu plan {selectedPlanData?.name} ha sido activado. Ya puedes comenzar a usar todas las funcionalidades.
          </p>
          <Button onClick={() => window.location.href = '/dashboard'} variant="primary">
            Ir al Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-2">
            {step === 'select' ? 'Paso 1 de 2' : 'Paso 2 de 2'}
          </p>
          <h1 className="text-3xl font-light">
            {step === 'select' ? 'Selecciona tu Plan' : 'Método de Pago'}
          </h1>
        </div>

        {error && (
          <div className="max-w-xl mx-auto mb-6 p-4 border border-red-900/50 bg-red-900/10 flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {step === 'select' ? (
          <>
            {/* Plan Selection */}
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  onClick={() => setSelectedPlan(plan.id)}
                  className={`relative border cursor-pointer transition-all ${
                    selectedPlan === plan.id
                      ? 'border-[#c9a050] bg-[#c9a050]/5'
                      : 'border-[#1a1a1a] hover:border-[#2a2a2a]'
                  } ${plan.highlighted ? 'md:-mt-4 md:mb-4' : ''}`}
                >
                  {plan.highlighted && (
                    <div className="absolute -top-px left-0 right-0 bg-[#c9a050] text-[#0a0a0a] text-xs tracking-[0.2em] uppercase py-2 text-center">
                      Recomendado
                    </div>
                  )}
                  <div className="p-6 pt-8">
                    <h3 className="text-lg font-light mb-2">{plan.name}</h3>
                    <div className="mb-6">
                      <span className="text-4xl font-light">S/ {plan.price}</span>
                      <span className="text-[#5a5a5a]">/mes</span>
                    </div>
                    <ul className="space-y-3 mb-6">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-sm">
                          <Check className="h-4 w-4 text-[#c9a050] mt-0.5 flex-shrink-0" />
                          <span className="text-[#8a8a8a]">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <div className={`w-4 h-4 border rounded-full mx-auto ${
                      selectedPlan === plan.id
                        ? 'border-[#c9a050] bg-[#c9a050]'
                        : 'border-[#2a2a2a]'
                    }`} />
                  </div>
                </div>
              ))}
            </div>

            {/* Continue Button */}
            <div className="text-center">
              <Button onClick={handleContinue} variant="primary">
                Continuar
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* Payment Step */}
            <div className="grid md:grid-cols-2 gap-8">
              {/* Order Summary */}
              <div className="border border-[#1a1a1a] p-6">
                <h3 className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Resumen del Pedido</h3>
                {selectedPlanData && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between py-4 border-b border-[#1a1a1a]">
                      <div>
                        <p className="font-medium">{selectedPlanData.name}</p>
                        <p className="text-sm text-[#5a5a5a]">Suscripción mensual</p>
                      </div>
                      <p className="text-xl">S/ {selectedPlanData.price}</p>
                    </div>
                    <div className="flex items-center justify-between py-4">
                      <p className="font-medium">Total</p>
                      <p className="text-2xl text-[#c9a050]">S/ {selectedPlanData.price}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Payment Method */}
              <div className="border border-[#1a1a1a] p-6">
                <h3 className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Método de Pago</h3>
                
                <div className="space-y-4 mb-6">
                  <button
                    onClick={() => { setPaymentMethod('card'); setError(null); }}
                    className={`w-full flex items-center gap-4 p-4 border transition-colors ${
                      paymentMethod === 'card'
                        ? 'border-[#c9a050] bg-[#c9a050]/5'
                        : 'border-[#1a1a1a] hover:border-[#2a2a2a]'
                    }`}
                  >
                    <CreditCard className="h-5 w-5 text-[#c9a050]" />
                    <div className="flex-1 text-left">
                      <p>Tarjeta de Crédito/Débito</p>
                      <p className="text-xs text-[#5a5a5a]">
                        {culqiConfig?.enabled ? 'Visa, Mastercard, Yape' : 'No disponible — configure CULQI_PUBLIC_KEY'}
                      </p>
                    </div>
                    <div className={`w-4 h-4 border rounded-full ${
                      paymentMethod === 'card' ? 'border-[#c9a050] bg-[#c9a050]' : 'border-[#2a2a2a]'
                    }`} />
                  </button>

                  <button
                    onClick={() => { setPaymentMethod('transfer'); setError(null); }}
                    className={`w-full flex items-center gap-4 p-4 border transition-colors ${
                      paymentMethod === 'transfer'
                        ? 'border-[#c9a050] bg-[#c9a050]/5'
                        : 'border-[#1a1a1a] hover:border-[#2a2a2a]'
                    }`}
                  >
                    <Building2 className="h-5 w-5 text-[#c9a050]" />
                    <div className="flex-1 text-left">
                      <p>Transferencia Bancaria</p>
                      <p className="text-xs text-[#5a5a5a]">Depósito o transferencia (activación manual)</p>
                    </div>
                    <div className={`w-4 h-4 border rounded-full ${
                      paymentMethod === 'transfer' ? 'border-[#c9a050] bg-[#c9a050]' : 'border-[#2a2a2a]'
                    }`} />
                  </button>
                </div>

                {paymentMethod === 'card' && !culqiConfig?.enabled && (
                  <div className="p-4 border border-yellow-900/50 bg-yellow-900/10 text-yellow-400 text-sm mb-4">
                    La pasarela de pagos no está configurada. Por favor use transferencia bancaria o contacte a soporte.
                  </div>
                )}

                {paymentMethod === 'transfer' && (
                  <div className="p-4 border border-[#1a1a1a] bg-[#0f0f0f]">
                    <p className="text-sm text-[#8a8a8a] mb-2">Datos bancarios:</p>
                    <p className="font-mono text-sm">Banco: BCP</p>
                    <p className="font-mono text-sm">Cuenta: 191-00000000-0-00</p>
                    <p className="font-mono text-sm">CCI: 00219100000000000000</p>
                    <p className="font-mono text-sm">Titular: Conflict Zero S.A.C.</p>
                  </div>
                )}

                <div className="flex items-center gap-4 mt-6">
                  <Button
                    onClick={() => setStep('select')}
                    variant="secondary"
                  >
                    ← Volver
                  </Button>
                  <Button
                    onClick={handlePayment}
                    disabled={processing || (paymentMethod === 'card' && !culqiConfig?.enabled)}
                    variant="primary"
                    icon={processing ? <Zap className="h-4 w-4 animate-pulse" /> : undefined}
                  >
                    {processing ? 'Procesando...' : `Pagar S/ ${selectedPlanData?.price}`}
                  </Button>
                </div>
              </div>
            </div>

            {/* Security Note */}
            <div className="mt-8 text-center">
              <div className="inline-flex items-center gap-2 text-sm text-[#5a5a5a]">
                <Shield className="h-4 w-4" />
                <span>Pago seguro con encriptación SSL</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
