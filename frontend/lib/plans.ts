// Configuración de Planes - Conflict Zero
// Define las limitaciones y características de cada plan

export type PlanType = 'essential' | 'professional' | 'enterprise';

export interface PlanConfig {
  name: string;
  price: number;
  maxRequests: number;           // Consultas mensuales
  maxHistoryDays: number;        // Días de historial disponible
  maxCompareRUCs: number;        // Máximo RUCs en comparación
  features: {
    apiAccess: boolean;          // Acceso a API REST
    bulkUpload: boolean;         // Carga masiva Excel/CSV
    webhooks: boolean;           // Webhooks Enterprise
    pdfCertificates: boolean;    // Certificados PDF
    prioritySupport: boolean;    // Soporte prioritario
    dedicatedManager: boolean;   // Manager dedicado
    customScore: boolean;        // Score personalizado
  };
}

export const PLANS: Record<PlanType, PlanConfig> = {
  essential: {
    name: 'Essential',
    price: 400,
    maxRequests: 1000,
    maxHistoryDays: 90,
    maxCompareRUCs: 2,
    features: {
      apiAccess: false,
      bulkUpload: false,
      webhooks: false,
      pdfCertificates: true,
      prioritySupport: false,
      dedicatedManager: false,
      customScore: false,
    },
  },
  professional: {
    name: 'Professional',
    price: 800,
    maxRequests: 5000,
    maxHistoryDays: 3650,  // ~10 años (ilimitado práctico)
    maxCompareRUCs: 5,
    features: {
      apiAccess: true,
      bulkUpload: true,
      webhooks: false,
      pdfCertificates: true,
      prioritySupport: true,
      dedicatedManager: false,
      customScore: true,
    },
  },
  enterprise: {
    name: 'Enterprise',
    price: 2500,
    maxRequests: -1,  // Ilimitado
    maxHistoryDays: -1,  // Ilimitado
    maxCompareRUCs: 10,
    features: {
      apiAccess: true,
      bulkUpload: true,
      webhooks: true,
      pdfCertificates: true,
      prioritySupport: true,
      dedicatedManager: true,
      customScore: true,
    },
  },
};

// Helper para verificar si una característica está disponible
export function hasFeature(plan: PlanType, feature: keyof PlanConfig['features']): boolean {
  return PLANS[plan].features[feature];
}

// Helper para verificar límites
export function checkLimit(plan: PlanType, limitType: 'requests' | 'historyDays' | 'compareRUCs', current: number): boolean {
  const planConfig = PLANS[plan];
  
  switch (limitType) {
    case 'requests':
      return planConfig.maxRequests === -1 || current < planConfig.maxRequests;
    case 'historyDays':
      return planConfig.maxHistoryDays === -1 || current <= planConfig.maxHistoryDays;
    case 'compareRUCs':
      return current <= planConfig.maxCompareRUCs;
    default:
      return false;
  }
}

// Mensajes de upgrade
export const UPGRADE_MESSAGES: Record<PlanType, string> = {
  essential: 'Upgrade a Professional para acceso ilimitado',
  professional: 'Upgrade a Enterprise para características avanzadas',
  enterprise: 'Contacte a su manager de cuenta',
};
