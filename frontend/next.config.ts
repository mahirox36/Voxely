import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // TODO: Change the minotar to crafthead 
      { protocol: 'https', hostname: 'images.unsplash.com', port:'', pathname: "/**" },
      { protocol: 'https', hostname: 'minotar.net', port:'', pathname: "/**" },
      { protocol: 'https', hostname: 'cdn.modrinth.com', port:'', pathname: "/**" },
      { protocol: 'https', hostname: 'minecraft-api.vercel.app', port:'', pathname: "/**" },
    ],
  },
};

export default nextConfig;