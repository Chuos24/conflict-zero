'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import Cookies from 'js-cookie';
import { Shield, Search, BarChart3, History, Scale, LogOut } from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    Cookies.remove('token');
    router.push('/login');
  };

  const navItems = [
    { href: '/dashboard', label: 'Verificar', icon: Search },
    { href: '/dashboard/stats', label: 'Estadísticas', icon: BarChart3 },
    { href: '/dashboard/history', label: 'Historial', icon: History },
    { href: '/dashboard/compare', label: 'Comparar', icon: Scale },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3]">
      <header className="border-b border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-[#c9a050]" strokeWidth={1.5} />
            <span className="text-lg tracking-[0.2em] font-light uppercase">Conflict Zero</span>
          </Link>
          <div className="flex items-center gap-8">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm tracking-wide transition-colors ${
                  pathname === item.href
                    ? 'text-[#c9a050]'
                    : 'text-[#8a8a8a] hover:text-[#e8e6e3]'
                }`}
              >
                {item.label}
              </Link>
            ))}
            <button
              onClick={handleLogout}
              className="text-sm tracking-wide text-[#8a8a8a] hover:text-[#e8e6e3] transition-colors flex items-center gap-2"
            >
              <LogOut className="h-4 w-4" />
              Salir
            </button>
          </div>
        </div>
      </header>

      <main>{children}</main>
    </div>
  );
}
