import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8001",
      "/v1": "http://127.0.0.1:8001",
      "/ui": "http://127.0.0.1:8001",
    },
  },
  // The launcher rewrites HTML URLs for the portal. Lazy chunks and their CSS
  // must resolve from the importing asset so they use the same portal prefix.
  experimental: {
    renderBuiltUrl: (_filename, { hostType }) => ({ relative: hostType !== "html" }),
  },
  build: { outDir: "dist" },
});
