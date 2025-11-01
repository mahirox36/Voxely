import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = isDev
      ? "http://localhost:25401"
      : "http://backend:25401";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  images: {
    domains: [
      "images.unsplash.com",
      "minotar.net",
      "cdn.modrinth.com",
      "minecraft-api.vercel.app",
    ],
  },
};

export default nextConfig;
