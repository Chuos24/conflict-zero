import axios from 'axios';
import Cookies from 'js-cookie';
import type { LoginCredentials, RegisterData, TokenResponse, User, VerificationResult } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// API Gateway - para consultas de RUC (datos reales)
const apiGateway = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Backend API - para autenticación, historial, etc.
const api = axios.create({
  baseURL: `${BACKEND_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token
api.interceptors.request.use((config) => {
  const token = Cookies.get('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('token');
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const auth = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: any) =>
    api.post('/auth/register', data),
  me: () =>
    api.get('/auth/me'),
};

// Verification - Usa API Gateway para datos reales de RUC
export const verification = {
  // Consulta directa a API Gateway (datos reales de SUNAT)
  verify: (ruc: string) =>
    apiGateway.get(`/consulta-osce/${ruc}`),
  
  // Historial desde el backend
  history: () =>
    api.get('/verify/history'),
  
  // Verificación pública
  publicVerify: (ruc: string) =>
    apiGateway.get(`/consulta-osce/${ruc}`),
};

// Dashboard
export const dashboard = {
  stats: () =>
    api.get('/dashboard/stats'),
  usage: () =>
    api.get('/dashboard/usage'),
};

export default api;
