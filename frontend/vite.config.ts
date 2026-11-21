import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

const version = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")).version;

// base "./" : l'interface fonctionne aussi derrière l'Ingress de Home Assistant (sous-chemin)
export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(version) },
  base: "./",
  build: { outDir: "../src/ocean2mqtt/frontend", emptyOutDir: true },
  server: { proxy: { "/api": { target: "ws://localhost:8080", ws: true }, "/produits": "http://localhost:8080" } },
});
