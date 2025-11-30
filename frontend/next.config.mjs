/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable ESLint during production build (warnings won't block build)
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Enable standalone output for Docker
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'm.media-amazon.com',
      },
      {
        protocol: 'https',
        hostname: 'images-na.ssl-images-amazon.com',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
      {
        source: '/health',
        destination: 'http://backend:8000/health',
      },
      {
        source: '/docs',
        destination: 'http://backend:8000/docs',
      },
      {
        source: '/openapi.json',
        destination: 'http://backend:8000/openapi.json',
      },
    ];
  },
};

export default nextConfig;
