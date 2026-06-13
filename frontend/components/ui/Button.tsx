import { ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  isLoading?: boolean;
  className?: string;
  icon?: ReactNode;
}

export default function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  isLoading = false,
  className = '',
  icon,
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center gap-2 text-sm tracking-[0.1em] uppercase font-medium transition-colors disabled:opacity-50';
  
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-6 py-3',
    lg: 'px-8 py-4',
  };

  const variants = {
    primary: 'bg-[#c9a050] text-[#0a0a0a] hover:bg-[#d4aa5a]',
    secondary: 'border border-[#2a2a2a] text-[#e8e6e3] hover:border-[#c9a050]',
    danger: 'bg-red-900/20 border border-red-900/50 text-red-400 hover:bg-red-900/30',
    outline: 'border border-[#2a2a2a] text-[#e8e6e3] hover:border-[#c9a050] hover:text-[#c9a050]',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {isLoading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}
