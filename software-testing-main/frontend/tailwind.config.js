/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'navy-bg': '#0B101E',
        'navy-panel': '#131B2F',
        'cyan-accent': '#00E5FF',
        'critical-red': '#FF3366',
        'secure-green': '#00E676',
        'warn-amber': '#FFAB00'
      }
    },
  },
  plugins: [],
}
