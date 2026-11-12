/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#080d1a',
          800: '#0d1225',
          700: '#141b35',
          600: '#1c2645',
          500: '#243050',
        },
        accent: { 500: '#00d4ff', 400: '#33ddff', 600: '#00aacc' },
        danger: { 500: '#ff3333', 400: '#ff5555' },
        warn: { 500: '#ff8800', 400: '#ffaa33' },
        success: { 500: '#00cc66', 400: '#33dd88' },
      },
      fontFamily: { mono: ['JetBrains Mono', 'Fira Code', 'monospace'] },
    },
  },
  plugins: [],
}
