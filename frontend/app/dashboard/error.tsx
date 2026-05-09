'use client';

import { useEffect } from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Dashboard Error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] flex items-center justify-center p-8">
      <div className="max-w-md w-full border border-[#1a1a1a] p-10 text-center">
        <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-6" strokeWidth={1.5} />
        <p className="text-[#c9a050] tracking-[0.3em] text-xs uppercase mb-4">Error</p>
        <h1 className="text-xl font-light mb-4">Algo salió mal</h1>
        <p className="text-sm text-[#8a8a8a] mb-8">
          {error.message || 'Ha ocurrido un error inesperado. Intenta nuevamente.'}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 bg-[#c9a050] text-[#0a0a0a] px-6 py-3 text-sm tracking-[0.1em] uppercase font-medium hover:bg-[#d4aa5a] transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Reintentar
        </button>
      </div>
    </div>
  );
}
