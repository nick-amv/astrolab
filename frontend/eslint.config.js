import js from "@eslint/js";
import ts from "typescript-eslint";

// Scope: TS/JS only. Svelte components are type-checked by `svelte-check`
// (npm run check) in CI; generated Paraglide output and build artifacts are
// ignored. This keeps `eslint .` fast and deterministic.
export default ts.config(
  {
    ignores: [
      "build/",
      ".svelte-kit/",
      "src/lib/paraglide/",
      "node_modules/",
      "**/*.svelte",
    ],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
    },
  },
);
