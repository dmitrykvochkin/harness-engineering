import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // localhost and 127.0.0.1 are different origins to the dev server.
  // Without this, opening the app at 127.0.0.1 blocks the client runtime,
  // so the page paints but hover handlers never attach.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
