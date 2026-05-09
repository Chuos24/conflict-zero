'use client';

import { useState, useEffect, useCallback } from 'react';
import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';
import { auth } from '@/lib/api';
import type { User, TokenResponse } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export function useAuth() {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const initAuth = useCallback(async () => {
    const token = Cookies.get('token');
    if (!token) {
      setState(prev => ({ ...prev, isLoading: false }));
      return;
    }

    try {
      const response = await auth.me();
      setState({
        user: response.data,
        token,
        isLoading: false,
        isAuthenticated: true,
      });
    } catch {
      Cookies.remove('token');
      setState({
        user: null,
        token: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, []);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const response = await auth.login(email, password);
    const data: TokenResponse = response.data;
    
    Cookies.set('token', data.access_token, { expires: 1 });
    
    // Fetch user data
    const meResponse = await auth.me();
    
    setState({
      user: meResponse.data,
      token: data.access_token,
      isLoading: false,
      isAuthenticated: true,
    });
  }, []);

  const logout = useCallback(() => {
    Cookies.remove('token');
    setState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    });
    router.push('/login');
  }, [router]);

  const refreshUser = useCallback(async () => {
    try {
      const response = await auth.me();
      setState(prev => ({
        ...prev,
        user: response.data,
      }));
    } catch {
      logout();
    }
  }, [logout]);

  return {
    ...state,
    login,
    logout,
    refreshUser,
  };
}
