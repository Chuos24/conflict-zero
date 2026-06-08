'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  footer?: ReactNode;
  noPadding?: boolean;
}

export default function Card({
  children,
  className,
  title,
  subtitle,
  icon,
  footer,
  noPadding = false,
}: CardProps) {
  return (
    <div
      className={cn(
        'bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden',
        className
      )}
    >
      {(title || icon) && (
        <div className={cn('border-b border-slate-100', !noPadding && 'px-6 py-4')}>
          <div className="flex items-center gap-3">
            {icon && (
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-50 text-slate-600">
                {icon}
              </div>
            )}
            <div>
              {title && (
                <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
              )}
              {subtitle && (
                <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>
        </div>
      )}
      <div className={cn(!noPadding && 'p-6')}>{children}</div>
      {footer && (
        <div className="border-t border-slate-100 px-6 py-3 bg-slate-50/50">
          {footer}
        </div>
      )}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: ReactNode;
  className?: string;
}

export function StatCard({
  title,
  value,
  change,
  changeType = 'neutral',
  icon,
  className,
}: StatCardProps) {
  const changeColors = {
    positive: 'text-emerald-600 bg-emerald-50',
    negative: 'text-rose-600 bg-rose-50',
    neutral: 'text-slate-600 bg-slate-50',
  };

  return (
    <Card className={className} noPadding>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-50 text-slate-600">
              {icon}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600">{title}</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            </div>
          </div>
          {change && (
            <span
              className={cn(
                'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                changeColors[changeType]
              )}
            >
              {change}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
