'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Cookies from 'js-cookie';
import { 
  Shield, 
  Eye, 
  EyeOff, 
  Lock, 
  Mail, 
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  ChevronRight
} from 'lucide-react';
import { auth } from '@/lib/api';

interface LoginFormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true);
    setError('');

    try {
      const response = await auth.login(data.email, data.password);
      const expires = data.rememberMe ? 7 : 1;
      Cookies.set('token', response.data.access_token, { expires });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-[55%] xl:w-[60%] relative overflow-hidden">
        {/* Animated Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628] via-[#0f2240] to-[#1a365d]">
          {/* Animated Orbs */}
          <div className="absolute top-20 left-20 w-96 h-96 bg-[#c9a227]/10 rounded-full blur-[100px] animate-pulse" />
          <div className="absolute bottom-40 right-20 w-[500px] h-[500px] bg-[#1e4976]/30 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#c9a227]/5 rounded-full blur-[150px] animate-pulse" style={{ animationDelay: '2s' }} />
          
          {/* Grid Pattern Overlay */}
          <div 
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: `linear-gradient(rgba(201, 162, 39, 0.3) 1px, transparent 1px),
                               linear-gradient(90deg, rgba(201, 162, 39, 0.3) 1px, transparent 1px)`,
              backgroundSize: '60px 60px'
            }}
          />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between p-12 xl:p-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-[#c9a227] blur-lg opacity-40 group-hover:opacity-60 transition-opacity duration-500" />
              <Shield className="h-12 w-12 text-[#c9a227] relative z-10" strokeWidth={1.5} />
            </div>
            <div className="flex flex-col">
              <span className="text-2xl xl:text-3xl font-light tracking-[0.2em] text-white">
                CONFLICT<span className="font-semibold text-[#c9a227]">ZERO</span>
              </span>
              <span className="text-[10px] xl:text-[11px] tracking-[0.3em] text-[#c9a227]/60 uppercase">
                Enterprise Risk Intelligence
              </span>
            </div>
          </Link>

          {/* Main Message */}
          <div className="max-w-xl">
            <div className="mb-6">
              <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#c9a227]/10 border border-[#c9a227]/20 text-[#c9a227] text-xs tracking-[0.2em] uppercase">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Trusted by Fortune 500
              </span>
            </div>
            <h1 className="text-4xl xl:text-5xl font-light text-white leading-tight mb-6">
              Secure Your Business
              <span className="block text-[#c9a227] font-semibold mt-2">Against Conflict Risk</span>
            </h1>
            <p className="text-lg text-slate-300/80 leading-relaxed font-light">
              Advanced verification systems for ultra-high-net-worth enterprises. 
              Real-time sanctions screening, PEP monitoring, and comprehensive due diligence.
            </p>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-8 mt-12 pt-12 border-t border-white/10">
              <div>
                <div className="text-3xl xl:text-4xl font-light text-[#c9a227]">99.9%</div>
                <div className="text-xs text-slate-400 mt-1 tracking-wider uppercase">Accuracy Rate</div>
              </div>
              <div>
                <div className="text-3xl xl:text-4xl font-light text-[#c9a227]">&lt;2s</div>
                <div className="text-xs text-slate-400 mt-1 tracking-wider uppercase">Response Time</div>
              </div>
              <div>
                <div className="text-3xl xl:text-4xl font-light text-[#c9a227]">200+</div>
                <div className="text-xs text-slate-400 mt-1 tracking-wider uppercase">Data Sources</div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>© 2026 Conflict Zero. All rights reserved.</span>
            <div className="flex items-center gap-6">
              <Link href="#" className="hover:text-[#c9a227] transition-colors">Privacy Policy</Link>
              <Link href="#" className="hover:text-[#c9a227] transition-colors">Terms of Service</Link>
            </div>
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#c9a227]/30 to-transparent" />
        <div className="absolute top-0 right-0 w-px h-full bg-gradient-to-b from-transparent via-[#c9a227]/20 to-transparent" />
      </div>

      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center bg-[#fafbfc] relative">
        {/* Subtle Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #0a1628 1px, transparent 0)`,
            backgroundSize: '32px 32px'
          }}
        />

        <div className="w-full max-w-md px-8 py-12 relative z-10">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <Shield className="h-10 w-10 text-[#0a1628]" strokeWidth={1.5} />
            <div className="flex flex-col">
              <span className="text-xl font-light tracking-[0.15em] text-[#0a1628]">
                CONFLICT<span className="font-semibold text-[#c9a227]">ZERO</span>
              </span>
            </div>
          </div>

          {/* Form Card */}
          <div className="bg-white rounded-2xl shadow-[0_8px_60px_-15px_rgba(10,22,40,0.12)] p-8 xl:p-10 border border-slate-100">
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-[#0a1628] mb-2">Welcome Back</h2>
              <p className="text-slate-500 text-sm">
                Sign in to access your enterprise dashboard
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                <span className="text-sm text-red-600">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Email Field */}
              <div>
                <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="email"
                    autoComplete="email"
                    className={`w-full pl-12 pr-4 py-3.5 bg-slate-50 border rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0a1628]/10 focus:border-[#0a1628] transition-all duration-200 ${
                      errors.email ? 'border-red-300 focus:border-red-500 focus:ring-red-100' : 'border-slate-200'
                    }`}
                    placeholder="name@company.com"
                    {...register('email', {
                      required: 'Email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Invalid email address',
                      },
                    })}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1.5 text-xs text-red-500">{errors.email.message}</p>
                )}
              </div>

              {/* Password Field */}
              <div>
                <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className={`w-full pl-12 pr-12 py-3.5 bg-slate-50 border rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0a1628]/10 focus:border-[#0a1628] transition-all duration-200 ${
                      errors.password ? 'border-red-300 focus:border-red-500 focus:ring-red-100' : 'border-slate-200'
                    }`}
                    placeholder="Enter your password"
                    {...register('password', {
                      required: 'Password is required',
                      minLength: {
                        value: 6,
                        message: 'Password must be at least 6 characters',
                      },
                    })}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1.5 text-xs text-red-500">{errors.password.message}</p>
                )}
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-slate-300 text-[#0a1628] focus:ring-[#0a1628]/20 cursor-pointer"
                    {...register('rememberMe')}
                  />
                  <span className="text-sm text-slate-600 group-hover:text-slate-800 transition-colors">
                    Remember me
                  </span>
                </label>
                <Link 
                  href="#" 
                  className="text-sm text-[#c9a227] hover:text-[#a88520] font-medium transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Login Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#0a1628] text-white py-4 rounded-xl font-medium text-sm tracking-wide hover:bg-[#141f35] focus:outline-none focus:ring-4 focus:ring-[#0a1628]/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 group"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-white px-4 text-xs text-slate-400 uppercase tracking-wider">
                  Or continue with
                </span>
              </div>
            </div>

            {/* Social Login */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                className="flex items-center justify-center gap-2 px-4 py-3 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <span className="text-sm text-slate-600">Google</span>
              </button>
              <button
                type="button"
                className="flex items-center justify-center gap-2 px-4 py-3 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
              >
                <svg className="h-5 w-5" fill="#0077B5" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                <span className="text-sm text-slate-600">LinkedIn</span>
              </button>
            </div>
          </div>

          {/* Register Link */}
          <p className="text-center mt-8 text-sm text-slate-500">
            Don't have an enterprise account?{' '}
            <Link 
              href="/register" 
              className="text-[#0a1628] font-semibold hover:text-[#c9a227] transition-colors inline-flex items-center gap-1"
            >
              Request Access
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </p>

          {/* Security Badge */}
          <div className="flex items-center justify-center gap-2 mt-6 text-xs text-slate-400">
            <Lock className="h-3.5 w-3.5" />
            <span>Secured with 256-bit encryption</span>
          </div>
        </div>
      </div>
    </div>
  );
}
