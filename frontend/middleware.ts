import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = [
  '/',
  '/login',
  '/register',
  '/pricing',
  '/blog',
  '/contacto',
  '/terminos',
  '/privacidad',
  '/checkout',
  '/verificar',
];

const PROTECTED_PREFIXES = [
  '/dashboard',
  '/api/protected',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('token')?.value;

  // Check if path is protected
  const isProtected = PROTECTED_PREFIXES.some(prefix => pathname.startsWith(prefix));
  const isPublic = PUBLIC_PATHS.some(path => pathname === path || pathname.startsWith('/_next'));

  // Redirect unauthenticated users from protected routes to login
  if (isProtected && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from login/register
  if ((pathname === '/login' || pathname === '/register') && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
