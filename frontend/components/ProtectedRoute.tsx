'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import Loading from '@/components/ui/Loading';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = Cookies.get('token');

  useEffect(() => {
    if (!token) {
      router.push('/login');
    }
  }, [token, router]);

  if (!token) {
    return <Loading fullScreen message="Verificando sesión..." />;
  }

  return <>{children}</>;
}
