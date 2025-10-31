import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:25401/api/:path*',
      },
    ];
  },
  images: {
    domains: ['images.unsplash.com', "minotar.net", "cdn.modrinth.com", "minecraft-api.vercel.app"],
  },
};

export default nextConfig;
