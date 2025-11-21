import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `https://unobtrusively-transelementary-ladonna.ngrok-free.dev/api/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://unobtrusively-transelementary-ladonna.ngrok-free.dev/api/',
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'unobtrusively-transelementary-ladonna.ngrok-free.dev',
        pathname: '/media/**',
      },
    ],
  },
};

export default nextConfig;