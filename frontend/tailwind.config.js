/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7ff", 100: "#d9edff", 200: "#bce0ff", 300: "#8ecdff", 400: "#59b0ff",
          500: "#2f8fff", 600: "#1a6ef2", 700: "#1657cc", 800: "#1848a3", 900: "#193f81", 950: "#142850",
        },
        severity: { low: "#3b9c6d", medium: "#d6a417", high: "#e0692f", critical: "#c73434" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
