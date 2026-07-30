import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: { port: 3000, host: true },
    define: {
      "process.env.REACT_APP_BACKEND_URL": JSON.stringify(
        env.REACT_APP_BACKEND_URL || env.VITE_BACKEND_URL || "http://localhost:8001"
      ),
      // The marketing site lives on a different origin to this app, so public
      // pages served here (the Agenda Builder) must link to it absolutely.
      // Defaulted rather than required: the value is stable, so no Render env
      // change is needed, but it stays overridable for preview environments.
      "process.env.REACT_APP_MARKETING_URL": JSON.stringify(
        env.REACT_APP_MARKETING_URL || "https://intro-connect.com"
      ),
    },
  };
});
