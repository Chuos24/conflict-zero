'use client';

import { useState } from 'react';
import { Check, CreditCard, Shield, Zap, Building2 } from 'lucide-react';
import Link from 'next/link';

interface Plan {
  id: string;
  name: string;
  price: number;
  monthly_limit: number;
  features: string[];
  highlighted?: boolean;
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

export default function CheckoutPage() {
  const [selectedPlan, setSelectedPlan] = useState<string>('professional');
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'transfer'>('card');
  const [processing, setProcessing] = useState(false);
  const [step, setStep] = useState<'select' | 'payment' | 'success'>('select');

  const selectedPlanData = plans.find(p => p.id === selectedPlan);

  const handleContinue = () => {
    setStep('payment');
  };

  const handlePayment = async () => {
    setProcessing(true);
    // Simulación de procesamiento
    await new Promise(resolve => setTimeout(resolve, 2000));
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
          <Link
            href="/dashboard"
            className="inline-block bg-[#c9a050] text-[#0a0a0a] px-8 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors"
          >
            Ir al Dashboard
          </Link>
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
                      <span className="text-4xl font-light">${plan.price}</span>
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
              <button
                onClick={handleContinue}
                className="bg-[#c9a050] text-[#0a0a0a] px-12 py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors"
              >
                Continuar
              </button>
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
                      <p className="text-xl">${selectedPlanData.price}</p>
                    </div>
                    <div className="flex items-center justify-between py-4">
                      <p className="font-medium">Total</p>
                      <p className="text-2xl text-[#c9a050]">${selectedPlanData.price}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Payment Method */}
              <div className="border border-[#1a1a1a] p-6">
                <h3 className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a] mb-6">Método de Pago</h3>
                
                <div className="space-y-4 mb-6">
                  <button
                    onClick={() => setPaymentMethod('card')}
                    className={`w-full flex items-center gap-4 p-4 border transition-colors ${
                      paymentMethod === 'card'
                        ? 'border-[#c9a050] bg-[#c9a050]/5'
                        : 'border-[#1a1a1a] hover:border-[#2a2a2a]'
                    }`}
                  >
                    <CreditCard className="h-5 w-5 text-[#c9a050]" />
                    <div className="flex-1 text-left">
                      <p>Tarjeta de Crédito/Débito</p>
                      <p className="text-xs text-[#5a5a5a]">Visa, Mastercard, Amex</p>
                    </div>
                    <div className={`w-4 h-4 border rounded-full ${
                      paymentMethod === 'card' ? 'border-[#c9a050] bg-[#c9a050]' : 'border-[#2a2a2a]'
                    }`} />
                  </button>

                  <button
                    onClick={() => setPaymentMethod('transfer')}
                    className={`w-full flex items-center gap-4 p-4 border transition-colors ${
                      paymentMethod === 'transfer'
                        ? 'border-[#c9a050] bg-[#c9a050]/5'
                        : 'border-[#1a1a1a] hover:border-[#2a2a2a]'
                    }`}
                  >
                    <Building2 className="h-5 w-5 text-[#c9a050]" />
                    <div className="flex-1 text-left">
                      <p>Transferencia Bancaria</p>
                      <p className="text-xs text-[#5a5a5a]">Depósito o transferencia</p>
                    </div>
                    <div className={`w-4 h-4 border rounded-full ${
                      paymentMethod === 'transfer' ? 'border-[#c9a050] bg-[#c9a050]' : 'border-[#2a2a2a]'
                    }`} />
                  </button>
                </div>

                {paymentMethod === 'card' ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-[#8a8a8a] mb-2">Número de Tarjeta</label>
                      <input
                        type="text"
                        placeholder="0000 0000 0000 0000"
                        className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-[#8a8a8a] mb-2">Expiración</label>
                        <input
                          type="text"
                          placeholder="MM/AA"
                          className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-[#8a8a8a] mb-2">CVC</label>
                        <input
                          type="text"
                          placeholder="123"
                          className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 border border-[#1a1a1a] bg-[#0f0f0f]">
                    <p className="text-sm text-[#8a8a8a] mb-2">Datos bancarios:</p>
                    <p className="font-mono text-sm">Banco: BCP</p>
                    <p className="font-mono text-sm">Cuenta: 191-00000000-0-00</p>
                    <p className="font-mono text-sm">CCI: 00219100000000000000</p>
                    <p className="font-mono text-sm">Titular: Conflict Zero S.A.C.</p>
                  </div>
                )}

                <div className="flex items-center gap-4 mt-6">
                  <button
                    onClick={() => setStep('select')}
                    className="text-sm text-[#5a5a5a] hover:text-[#e8e6e3] transition-colors"
                  >
                    ← Volver
                  </button>
                  <button
                    onClick={handlePayment}
                    disabled={processing}
                    className="flex-1 bg-[#c9a050] text-[#0a0a0a] py-4 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {processing ? (
                      <>
                        <Zap className="h-4 w-4 animate-pulse" />
                        Procesando...
                      </>
                    ) : (
                      `Pagar $${selectedPlanData?.price}`
                    )}
                  </button>
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