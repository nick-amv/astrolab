import { defineConfig } from "vitest/config";

// Kept separate from vite.config.ts so SvelteKit's build type-checking never
// sees the `test` key. Unit tests here cover locale-agnostic utilities; they
// don't need the SvelteKit/Paraglide plugins.
export default defineConfig({
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "node",
  },
});
