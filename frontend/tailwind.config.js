/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Core brand palette (cool, used on parent-facing screens).
        // These match the values previously redeclared per-page in
        // parent/child <style> blocks, now the single source of truth.
        hero: {
          light: '#a78bfa',
          DEFAULT: '#7c3aed',
          dark: '#5b21b6',
        },
        savings: {
          light: '#4ade80',
          DEFAULT: '#10b981',
          dark: '#047857',
        },
        reward: {
          light: '#fde047',
          DEFAULT: '#f59e0b',
          dark: '#92400e',
        },
        penalty: {
          light: '#fb7185',
          DEFAULT: '#f43f5e',
          dark: '#be123c',
        },
        // Warm child palette (child dashboard only) — intentionally
        // distinct from the cool parent palette. See docs/DESIGN.md.
        child: {
          bg: '#fffaf4',
          card: '#fffefb',
          border: '#f0e4d7',
          accent: '#ff8d59',
          'savings-bg': '#fff8e9',
          'savings-border': '#f4e3b2',
          'savings-text': '#b98612',
          'spend-bg': '#f0fbf7',
          'spend-border': '#cdeee2',
          'hold-bg': '#fff1f1',
          'hold-border': '#f0c6c6',
        },
      },
      backgroundImage: {
        'hero-pattern': "radial-gradient(circle at 2px 2px, rgba(124, 58, 237, 0.05) 1px, transparent 0)",
      }
    },
  },
  plugins: [],
}
