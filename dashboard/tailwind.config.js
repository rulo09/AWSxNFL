/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 700: '#1e3a5f', 800: '#152a47', 900: '#0f1f3a' },
      },
    },
  },
  plugins: [],
}
