'use client';

import { Shield } from 'lucide-react';

interface LoadingProps {
  message?: string;
  fullScreen?: boolean;
}

export default function Loading({ message = 'Cargando', fullScreen = false }: LoadingProps) {
  const content = (
    <div className="text-center">
      <div className="relative w-12 h-12 mx-auto mb-6">
        <div className="absolute inset-0 border-2 border-[#2a2a2a] rounded-full" />
        <div className="absolute inset-0 border-2 border-[#c9a050] border-t-transparent rounded-full animate-spin" />
        <Shield className="absolute inset-0 m-auto h-5 w-5 text-[#c9a050]" strokeWidth={1.5} />
      </div>
      <p className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a]">{message}</p>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] flex items-center justify-center">
        {content}
      </div>
    );
  }

  return (
    <div className="py-12">
      {content}
    </div>
  );
}
