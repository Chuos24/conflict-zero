export interface User {
  id: string;
  email: string;
  full_name: string;
  company_name?: string;
  ruc?: string;
  plan_type: 'red' | 'essential' | 'professional' | 'enterprise';
  monthly_limit: number;
  monthly_requests: number;
  is_active: boolean;
  is_admin: boolean;
  api_key?: string;
  created_at?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  company_name?: string;
  ruc?: string;
  plan: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}

export interface VerificationResult {
  success: boolean;
  data?: {
    ruc: string;
    razon_social: string;
    estado_sunat: string;
    condicion: string;
    direccion?: string;
    distrito?: string;
    provincia?: string;
    departamento?: string;
  };
  score?: number;
  risk_level?: string;
  error?: string;
}

export interface CompareResult {
  ruc: string;
  razon_social: string;
  score: number;
  risk_level: string;
  sanciones_count: number;
  estado_sunat: string;
}

export interface PlanConfig {
  id: string;
  name: string;
  price: number;
  monthly_limit: number;
  max_history_days: number;
  max_compare_rucs: number;
  features: string[];
}

export interface DashboardStats {
  total_verifications: number;
  monthly_usage: number;
  monthly_limit: number;
  plan_type: string;
  recent_searches: RecentSearch[];
}

export interface RecentSearch {
  ruc: string;
  razon_social: string;
  score: number;
  searched_at: string;
}

// Network / Mi Red - Supplier Watchlist types
export interface Supplier {
  id: string;
  ruc: string;
  supplier_name: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  score: number;
  added_at: string;
  last_checked: string | null;
  osce_sanciones: number;
  tce_sanciones: number;
}

export interface SupplierAlert {
  id: string;
  supplier_ruc: string;
  supplier_name: string | null;
  change_type: string;
  previous_status: string | null;
  new_status: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  is_read: boolean;
  email_sent: boolean;
  created_at: string;
}

export interface NetworkListResponse {
  suppliers: Supplier[];
  total: number;
  alerts_unread: number;
}

export interface AlertsResponse {
  alerts: SupplierAlert[];
  total: number;
  unread_count: number;
}

// Certificates types
export interface Certificate {
  id: string;
  code: string;
  ruc: string;
  company_name?: string;
  score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'expired' | 'revoked';
  generated_at: string;
  expires_at?: string;
  pdf_url?: string;
}

export interface GenerateCertificateRequest {
  ruc: string;
  company_name?: string;
  score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  sunat_status?: string;
  osce_sanctions_count?: number;
  tce_sanctions_count?: number;
  verification_data?: Record<string, unknown>;
}
