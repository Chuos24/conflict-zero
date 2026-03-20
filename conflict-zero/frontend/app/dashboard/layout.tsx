'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import Cookies from 'js-cookie';
import {
  Shield, Search, History, BarChart3, Settings, LogOut,
  User, ChevronDown, Moon, Sun
} from 'lucide-react';
import { useState, useEffect } from 'react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    // Check if we're on the stats page and auto-enable dark mode
    if (pathname === '/dashboard/stats') {
      setIsDarkMode(true);
    } else {
      setIsDarkMode(false);
    }
  }, [pathname]);

  const handleLogout = () => {
    Cookies.remove('token');
    router.push('/');
  };

  const navItems = [
    { href: '/dashboard', icon: Search, label: 'Verificar' },
    { href: '/dashboard/history', icon: History, label: 'Historial' },
    { href: '/dashboard/stats', icon: BarChart3, label: 'Estadísticas' },
  ];

  const isStatsPage = pathname === '/dashboard/stats';

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isStatsPage ? 'bg-[#0d1b2a]' : 'bg-slate-50'}`}>
      {/* Header */}
      <header className={`border-b sticky top-0 z-50 transition-colors duration-300 ${
        isStatsPage 
          ? 'bg-[#0d1b2a]/95 backdrop-blur-md border-[#c9a227]/20' 
          : 'bg-white border-slate-200'
      }`}>
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Shield className={`h-8 w-8 ${isStatsPage ? 'text-[#c9a227]' : 'text-blue-600'}`} />
            <span className={`text-xl font-bold ${isStatsPage ? 'text-white' : ''}`}>
              Conflict Zero
            </span>
          </Link>

          {/* Navigation - Desktop */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    isStatsPage
                      ? isActive
                        ? 'text-[#c9a227] bg-[#c9a227]/10'
                        : 'text-[#778da9] hover:text-[#c9a227] hover:bg-[#c9a227]/5'
                      : isActive
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-4">
            <div className="relative group">
              <button className={`flex items-center gap-2 text-sm font-medium ${isStatsPage ? 'text-[#778da9]' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  isStatsPage ? 'bg-[#c9a227]/20' : 'bg-blue-100'
                }`}>
                  <User className={`h-4 w-4 ${isStatsPage ? 'text-[#c9a227]' : 'text-blue-600'}`} />
                </div>
                <ChevronDown className={`h-4 w-4 ${isStatsPage ? 'text-[#778da9]' : ''}`} />
              </button>

              <div className={`absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all ${
                isStatsPage 
                  ? 'bg-[#1b263b] border-[#c9a227]/20' 
                  : 'bg-white border-slate-200'
              }`}>
                <button
                  onClick={handleLogout}
                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-colors ${
                    isStatsPage
                      ? 'text-red-400 hover:bg-red-500/10'
                      : 'text-red-600 hover:bg-red-50'
                  }`}
                >
                  <LogOut className="h-4 w-4" />
                  Cerrar sesión
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <div className={`md:hidden border-b ${isStatsPage ? 'bg-[#0d1b2a] border-[#c9a227]/10' : 'bg-white border-slate-200'}`}>
        <div className="container mx-auto px-4 py-2">
          <nav className="flex justify-around">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isStatsPage
                      ? isActive
                        ? 'text-[#c9a227]'
                        : 'text-[#778da9]'
                      : isActive
                        ? 'text-blue-600'
                        : 'text-slate-600'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className={`container mx-auto px-4 py-8 ${isStatsPage ? 'max-w-7xl' : ''}`}>
        {/* Desktop Sidebar Layout (only for non-stats pages) */}
        {!isStatsPage ? (
          <div className="flex flex-col md:flex-row gap-8">
            {/* Sidebar - Desktop */}
            <aside className="hidden md:block w-64 shrink-0">
              <nav className="space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-600'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </aside>

            {/* Main Content */}
            <main className="flex-1 min-w-0">{children}</main>
          </div>
        ) : (
          /* Full-width layout for stats page */
          <main className="min-w-0">{children}</main>
        )}
      </div>
    </div>
  );
}
