/// <reference types="vitest/config" />
import { resolve } from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "./src"),
    },
  },
  // The dev server reads the root .env.development, which `make dev` also passes to the backend.
  // Only FIREBASE_* variables reach the browser bundle, so they hold only the public web config.
  envDir: resolve(import.meta.dirname, "../../.."),
  envPrefix: "FIREBASE_",
  server: {
    // Calls to the generated services (`/<package>.v<N>.<Service>/<Method>`) go to the local backend.
    proxy: { "^/\\w+\\.v\\d+\\.": "http://localhost:8080" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["tests/framework/setup.ts"],
    coverage: {
      include: ["src/**"],
      // Generated shadcn code, and the entry point that only wires the app.
      exclude: [
        "src/components/ui/**",
        "src/components/theme-provider.tsx",
        "src/main.tsx",
        "src/env.d.ts",
        "src/**/*.test.{ts,tsx}",
      ],
      thresholds: { 100: true },
    },
  },
})
