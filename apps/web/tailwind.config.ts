import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6ff",
          100: "#d9eaff",
          200: "#bcd9ff",
          300: "#8ec0ff",
          400: "#599cff",
          500: "#3377ff",
          600: "#1f57f5",
          700: "#1843e1",
          800: "#1a39b6",
          900: "#1b358f",
        },
      },
    },
  },
  plugins: [],
};

export default config;
