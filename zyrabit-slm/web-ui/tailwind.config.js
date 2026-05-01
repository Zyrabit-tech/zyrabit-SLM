/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        zyrabit: {
          primary: '#3f5a6d',
          secondary: '#6090b4',
          bg: '#fdfdfd',
          surface: '#e2ecf4',
          muted: '#a9c4d9',
          ring: '#6090b4',
          border: '#a9c4d9',
          text: '#323439',
          subtext: '#3f5a6d',
        }
      }
    },
  },
  plugins: [],
}
