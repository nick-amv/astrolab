import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    // Compiles ./messages/*.json into $lib/paraglide with URL-based locale
    // routing. EVERY locale (incl. base ru) is prefixed (/ru, /en, /es, /fr) per
    // DESIGN §9; the bare root is negotiated in hooks.server.ts.
    // ⚠ When adding a locale: project.inlang/settings.json AND this list.
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
            ["es", "/es/:path(.*)?"],
            ["fr", "/fr/:path(.*)?"],
            ["de", "/de/:path(.*)?"],
          ],
        },
      ],
    }),
    sveltekit(),
  ],
});
