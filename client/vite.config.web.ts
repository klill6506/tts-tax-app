/**
 * Vite config for building the React app as a standard web SPA (no Electron).
 * Usage: npx vite build --config vite.config.web.ts
 * Output: client/dist-web/  (served by Django + WhiteNoise in production)
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  root: "src/renderer",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: path.resolve(__dirname, "dist-web"),
    emptyOutDir: true,
  },
});
