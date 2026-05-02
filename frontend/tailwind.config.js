/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        hero: {
          light: '#a78bfa',
          DEFAULT: '#7c3aed',
          dark: '#5b21b6',
        },
        savings: {
          light: '#4ade80',
          DEFAULT: '#16a34a',
          dark: '#166534',
        },
        reward: {
          light: '#fde047',
          DEFAULT: '#ca8a04',
          dark: '#854d0e',
        },
        penalty: {
          light: '#fb7185',
          DEFAULT: '#e11d48',
          dark: '#9f1239',
        }
      },
      backgroundImage: {
        'hero-pattern': "radial-gradient(circle at 2px 2px, rgba(124, 58, 237, 0.05) 1px, transparent 0)",
      }
    },
  },
  plugins: [],
}
