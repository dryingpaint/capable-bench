import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    root: path.resolve(__dirname),
  },
  experimental: {
    turbopackMemoryLimit: 1024 * 1024 * 1024,
  },
};

export default nextConfig;
