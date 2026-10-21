import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: [
        "src/components/BlockNode.tsx",
        "src/components/Inspector.tsx",
        "src/components/StatusBadge.tsx",
        "src/components/TopBar.tsx",
        "src/graph.ts",
      ],
      thresholds: { lines: 90, branches: 90 },
    },
  },
});
