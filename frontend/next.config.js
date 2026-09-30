/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone" removed — causes EPERM symlink errors on Windows.
  // Vercel handles its own output format; local dev uses the default server.
  reactStrictMode: true,
};

module.exports = nextConfig;
