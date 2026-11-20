/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  devIndicators: false, // the dev "N" badge covered buttons on phones
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Dev server only: let phones/tablets on the LAN load the app (docker-compose.lan.yml sets LAN_IP). No effect in builds.
  ...(process.env.LAN_IP ? { allowedDevOrigins: [process.env.LAN_IP] } : {}),
};

export default nextConfig;
