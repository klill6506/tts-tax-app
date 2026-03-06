/**
 * Vite config for the React web SPA.
 * Output: client/dist-web/  (served by Django + WhiteNoise in production)
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  root: "src/renderer",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: path.resolve(__dirname, "dist-web"),
    emptyOutDir: true,
  },
});
