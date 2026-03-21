/** @type {import('next').NextConfig} */
const nextConfig = {
  // Export static for Netlify
  output: 'export',
  distDir: 'out',
  
  // Environment variables
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY || '',
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod',
  },
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // TypeScript
  typescript: {
    ignoreBuildErrors: true,
  },
  
  // ESLint
  eslint: {
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
