import createNextIntlPlugin from "next-intl/plugin";
import withPWAInit from "@ducanh2912/next-pwa";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const withPWA = withPWAInit({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
  // F31: scope the service worker to never cache API responses.
  // Authorization-bearing requests and /v1/* must always hit the network.
  runtimeCaching: [
    {
      // Never cache API calls — auth cookies/headers change between sessions.
      urlPattern: /^https?:\/\/.*\/v1\/.*/,
      handler: "NetworkOnly",
    },
    {
      // Cache static assets with a stale-while-revalidate strategy.
      urlPattern: /^https?:\/\/.*\/_next\/static\/.*/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "next-static",
        expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    {
      // Cache images from R2 / self.
      urlPattern: /^https?:\/\/.*\.(png|jpg|jpeg|svg|webp|avif|gif|ico)$/,
      handler: "CacheFirst",
      options: {
        cacheName: "images",
        expiration: { maxEntries: 100, maxAgeSeconds: 7 * 24 * 60 * 60 },
      },
    },
  ],
});

// F32: strict Content-Security-Policy. Uses nonce-based script-src via
// Next.js middleware (see src/middleware.ts). Images from self + R2.
// connect-src scoped to self + the API domain. frame-ancestors 'none'.
const API_DOMAIN =
  process.env.NEXT_PUBLIC_API_URL || "https://api.jumlaos.ma";
const R2_DOMAIN = "https://*.r2.cloudflarestorage.com";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  transpilePackages: ["@jumlaos/shared"],
  experimental: {
    typedRoutes: false,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value:
              "camera=(self), microphone=(self), geolocation=(self)",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              `img-src 'self' ${R2_DOMAIN} data:`,
              `connect-src 'self' ${API_DOMAIN}`,
              "style-src 'self' 'unsafe-inline'",
              "font-src 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default withPWA(withNextIntl(nextConfig));
