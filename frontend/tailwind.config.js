/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // WARD Brand Colors (preserve original identity!)
        ward: {
          green: '#5EBBA8',
          'green-light': '#72CFB8',
          'green-dark': '#4A9D8A',
          silver: '#DFDFDF',
          dark: '#2C3E50',
          darker: '#1A252F',
        },
        // Modern semantic colors
        primary: {
          DEFAULT: '#5EBBA8', // WARD Green
          50: '#F0FAF8',
          100: '#D9F3ED',
          200: '#B3E7DB',
          300: '#8DDBC9',
          400: '#72CFB8',
          500: '#5EBBA8',
          600: '#4A9D8A',
          700: '#397A69',
          800: '#2C5D51',
          900: '#1E3F36',
        },
        success: '#10B981',
        danger: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6',
      },
      fontFamily: {
        sans: ['Roboto', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        lg: '12px',
        md: '8px',
        sm: '6px',
      },
      boxShadow: {
        'ward': '0 4px 6px -1px rgba(94, 187, 168, 0.1), 0 2px 4px -1px rgba(94, 187, 168, 0.06)',
        'ward-lg': '0 10px 15px -3px rgba(94, 187, 168, 0.1), 0 4px 6px -2px rgba(94, 187, 168, 0.05)',
      },
    },
  },
  plugins: [],
}
