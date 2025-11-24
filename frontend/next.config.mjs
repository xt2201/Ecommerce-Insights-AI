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
};

export default nextConfig;
