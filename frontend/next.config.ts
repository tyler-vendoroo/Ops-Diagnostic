import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.prod.website-files.com",
        pathname: "/658324c3275608f81f524a31/**",
      },
    ],
  },
};

export default nextConfig;
