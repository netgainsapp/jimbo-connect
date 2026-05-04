/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Calibri", "Segoe UI", "system-ui", "sans-serif"],
      },
      colors: {
        primary: "#0A66C2",
        "primary-hover": "#084d92",
        "bg-secondary": "#F7F8FA",
        "border-default": "#E4E6EA",
        "text-primary": "#0A0C10",
        "text-secondary": "#3D4454",
        "text-muted": "#6B7280",
      },
      borderRadius: {
        card: "8px",
        pill: "24px",
      },
      boxShadow: {
        card: "0 2px 8px rgba(0,0,0,0.06)",
      },
    },
  },
  plugins: [],
};
