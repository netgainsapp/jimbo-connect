/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Plus Jakarta Sans",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      colors: {
        // Brand palette from the Intro Connect kit
        primary: "#2563EB",        // Primary blue
        "primary-hover": "#1d4ed8",
        ink: "#0D1B2A",            // Deep blue (text + dark accent)
        wash: "#E6EEFF",           // Accent / soft blue background
        cream: "#F2F4F7",          // Light gray (sections)
        stone: "#6B7280",          // Mid gray (secondary text)
        line: "#E4E6EA",
      },
      borderRadius: { card: "12px", pill: "999px" },
      boxShadow: {
        card: "0 1px 3px rgba(13, 27, 42, 0.05), 0 2px 12px rgba(13, 27, 42, 0.04)",
        lift: "0 4px 24px rgba(37, 99, 235, 0.12)",
      },
    },
  },
  plugins: [],
};
