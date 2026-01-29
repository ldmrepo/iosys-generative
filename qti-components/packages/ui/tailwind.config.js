/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        qti: {
          primary: '#3b82f6',
          secondary: '#64748b',
          success: '#22c55e',
          warning: '#f59e0b',
          error: '#ef4444',
          correct: '#22c55e',
          incorrect: '#ef4444',
          partial: '#f59e0b',
        },
      },
      fontFamily: {
        sans: [
          'Pretendard',
          '-apple-system',
          'BlinkMacSystemFont',
          'system-ui',
          'Roboto',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
