/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4F46E5',
          light: '#818CF8',
          dark: '#4338CA',
        },
        secondary: {
          DEFAULT: '#EC4899',
          light: '#F472B6',
          dark: '#DB2777',
        },
        accent: {
          DEFAULT: '#06B6D4',
          light: '#67E8F9',
          dark: '#0891B2',
        },
        theme: {
          bg: 'var(--background)',
          card: 'var(--card-background)',
          border: 'var(--border-color)',
          text: 'var(--text)',
          'text-secondary': 'var(--text-secondary)',
          primary: 'var(--primary)',
          secondary: 'var(--secondary)',
          accent: 'var(--accent)',
        }
      },
      backgroundColor: {
        'theme-primary': 'var(--background-primary)',
        'theme-secondary': 'var(--background-secondary)',
        'theme-dark': 'var(--background-dark)',
      },
      gradientColorStops: {
        'theme-primary': 'var(--background-primary)',
        'theme-secondary': 'var(--background-secondary)',
        'theme-dark': 'var(--background-dark)',
      },
      backgroundImage: {
        'gradient-bg': 'linear-gradient(to bottom right, var(--gradient-bg))',
        'gradient-primary': 'linear-gradient(to right, var(--gradient-primary))',
        'gradient-secondary': 'linear-gradient(to right, var(--gradient-secondary))',
        'gradient-accent': 'linear-gradient(to right, var(--gradient-accent))',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'scale-in': 'scaleIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

