import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    // Render exposes the deployed commit; it lets /version prove which build is actually served.
    BUILD_COMMIT: process.env.RENDER_GIT_COMMIT ?? "development",
    BUILD_TIME: new Date().toISOString(),
  },
};

export default nextConfig;
