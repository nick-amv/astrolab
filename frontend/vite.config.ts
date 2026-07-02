import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    // Compiles ./messages/*.json into $lib/paraglide with URL-based locale
    // routing. baseLocale (ru) and en are both prefixed (/ru, /en) per DESIGN §9;
    // the bare root is redirected to /ru in hooks.server.ts.
    paraglideVitePlugin({
      project: "./project.inlang",
      outdir: "./src/lib/paraglide",
      strategy: ["url", "cookie", "baseLocale"],
      urlPatterns: [
        {
          pattern: "/:path(.*)?",
          localized: [
            ["ru", "/ru/:path(.*)?"],
            ["en", "/en/:path(.*)?"],
          ],
        },
      ],
    }),
    sveltekit(),
  ],
});
