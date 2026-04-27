import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/shared/src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        arabic: ["var(--font-cairo)", "Tahoma", "Arial", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#fef9ed",
          100: "#fdeec9",
          200: "#fbdb8e",
          300: "#f8c053",
          400: "#f5a32a",
          500: "#e88812",
          600: "#cc6a0c",
          700: "#a94e0e",
          800: "#8a3e13",
          900: "#723413",
        },
      },
    },
  },
  plugins: [],
};

export default config;
