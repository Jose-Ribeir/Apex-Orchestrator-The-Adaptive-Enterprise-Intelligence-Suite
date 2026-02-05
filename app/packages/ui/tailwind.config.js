/* eslint-env node */
/**
 * Tailwind v4 – This package does not build CSS.
 * Consuming apps (e.g. apps/web) use @source in their globals.css to scan
 * this package (e.g. @source "../../../packages/ui/src").
 * This config is for tooling (e.g. shadcn) that may run from this directory.
 *
 * @type {import('tailwindcss').Config}
 */
// eslint-disable-next-line no-undef -- Node CommonJS
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: {} },
  plugins: [],
};
