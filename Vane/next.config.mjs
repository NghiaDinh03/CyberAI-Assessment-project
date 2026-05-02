import path from 'node:path';
import pkg from './package.json' with { type: 'json' };

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        hostname: 's2.googleusercontent.com',
      },
    ],
  },
  serverExternalPackages: [
    'pdf-parse',
    'playwright',
    'officeparser',
    'file-type',
  ],
  outputFileTracingIncludes: {
    '/api/**': [
      './node_modules/@napi-rs/canvas/**',
      './node_modules/@napi-rs/canvas-linux-x64-gnu/**',
      './node_modules/@napi-rs/canvas-linux-x64-musl/**',
    ],
  },
  env: {
    NEXT_PUBLIC_VERSION: pkg.version,
  },
  turbopack: {
    root: process.cwd(),
  },
  // Proxy CyberAI backend API calls
  async rewrites() {
    return [
      {
        source: '/api/health',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/health`,
      },
      {
        source: '/api/system/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/system/:path*`,
      },
      {
        source: '/api/iso27001/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/iso27001/:path*`,
      },
      {
        source: '/api/standards/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/standards/:path*`,
      },
      {
        source: '/api/benchmark/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/benchmark/:path*`,
      },
      {
        source: '/api/ollama/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/ollama/:path*`,
      },
      {
        source: '/api/prompts/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/prompts/:path*`,
      },
      {
        source: '/api/docs/:path*',
        destination: `${process.env.API_URL || 'http://cyberai-backend:8000'}/api/docs/:path*`,
      },
    ];
  },
};

export default nextConfig;
