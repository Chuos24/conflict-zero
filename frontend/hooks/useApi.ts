'use client';

import { useState, useCallback } from 'react';
import type { ApiError } from '@/types';

interface UseApiOptions {
  onError?: (error: ApiError) => void;
  onSuccess?: <T>(data: T) => void;
}

export function useApi<T>(options: UseApiOptions = {}) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const execute = useCallback(
    async (apiCall: () => Promise<{ data: T }>) => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await apiCall();
        setData(response.data);
        options.onSuccess?.(response.data);
        return response.data;
      } catch (err: any) {
        const apiError: ApiError = {
          detail: err.response?.data?.detail || 'Error desconocido',
          status: err.response?.status,
        };
        setError(apiError);
        options.onError?.(apiError);
        throw apiError;
      } finally {
        setIsLoading(false);
      }
    },
    [options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    data,
    isLoading,
    error,
    execute,
    reset,
  };
}
