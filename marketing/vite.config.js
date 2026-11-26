import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { beaconTag } from "./scripts/beacon.mjs";

// Cloudflare Web Analytics. The site token comes from CF_BEACON_TOKEN at build
// time (set it on the Render static service, then rebuild). Unset or malformed
// means no beacon at all, so nothing ships with a placeholder in it.
function cloudflareBeacon() {
  return {
    name: "cloudflare-beacon",
    transformIndexHtml(html) {
      const tag = beaconTag(process.env.CF_BEACON_TOKEN);
      return tag ? html.replace("</head>", `    ${tag}\n  </head>`) : html;
    },
  };
}

export default defineConfig({
  plugins: [react(), cloudflareBeacon()],
  server: { port: 3001 },
});
