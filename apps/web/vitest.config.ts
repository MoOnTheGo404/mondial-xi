import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "@kickoff/shared": path.resolve(__dirname, "../../packages/shared/src"),
      "@kickoff/ui": path.resolve(__dirname, "../../packages/ui/src"),
    },
  },
  test: {
    environment: "jsdom",
    include: ["__tests__/**/*.test.ts?(x)"],
    setupFiles: ["__tests__/setup.ts"],
  },
});
