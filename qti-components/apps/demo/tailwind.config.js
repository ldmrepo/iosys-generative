/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    '../../packages/ui/src/**/*.{js,ts,jsx,tsx}',
    '../../packages/viewer/src/**/*.{js,ts,jsx,tsx}',
    '../../packages/assessment/src/**/*.{js,ts,jsx,tsx}',
    '../../packages/editor/src/**/*.{js,ts,jsx,tsx}',
  ],
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
    },
  },
  plugins: [],
}
