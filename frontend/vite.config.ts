import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" : l'interface fonctionne aussi derrière l'Ingress de Home Assistant (sous-chemin)
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "../src/ocean2mqtt/frontend", emptyOutDir: true },
  server: { proxy: { "/api": { target: "ws://localhost:8080", ws: true }, "/produits": "http://localhost:8080" } },
});
