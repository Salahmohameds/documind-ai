import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal `.next/standalone` server with only the traced
  // dependencies -- required for a small, non-root Docker image (see
  // ./Dockerfile) instead of shipping the whole node_modules tree.
  output: "standalone",
};

export default nextConfig;
