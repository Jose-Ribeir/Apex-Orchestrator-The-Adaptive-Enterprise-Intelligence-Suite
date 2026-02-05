import type { NextConfig } from "next";
import path from "node:path";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4200";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  async rewrites() {
    return [
      {
        source: "/auth/:path*",
        destination: `${apiUrl}/auth/:path*`,
      },
    ];
  },
};

export default nextConfig;
