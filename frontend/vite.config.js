import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), "frontend/package.json"), "utf-8"));

export default defineConfig({
  base: "./",
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
  },
  plugins: [react()],
  build: {
    outDir: "dist",
    minify: true,
  },
  server: {
    port: 5173,
  },
});
