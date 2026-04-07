/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:       '#0d0f14',
        panel:    '#151820',
        border:   '#2a2d3a',
        text:     '#e8eaf0',
        muted:    '#8a8fa8',
        crisis:   '#e53e3e',
        high:     '#dd6b20',
        elevated: '#d69e2e',
        watch:    '#48bb78',
        stable:   '#38a169',
        accent:   '#4299e1',
      },
      fontFamily: {
        mono: ['"Share Tech Mono"', 'monospace'],
        display: ['"Exo 2"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
