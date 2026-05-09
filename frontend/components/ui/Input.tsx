interface InputProps {
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  maxLength?: number;
  error?: string;
  className?: string;
}

export default function Input({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  required = false,
  maxLength,
  error,
  className = '',
}: InputProps) {
  return (
    <div className={className}>
      <label className="block text-xs tracking-[0.2em] uppercase text-[#8a8a8a] mb-3">
        {label}
        {required && <span className="text-[#c9a050] ml-1">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        required={required}
        className="w-full bg-transparent border border-[#2a2a2a] px-4 py-3 text-[#e8e6e3] focus:border-[#c9a050] focus:outline-none transition-colors placeholder:text-[#3a3a3a]"
      />
      {error && (
        <p className="mt-2 text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
