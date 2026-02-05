import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/login", destination: "/auth/sign-in", permanent: false },
      { source: "/signup", destination: "/auth/sign-up", permanent: false },
    ];
  },
};

export default nextConfig;
