import type { Reroute } from "@sveltejs/kit";
import { deLocalizeUrl } from "$lib/paraglide/runtime";

// Strips the locale prefix (/ru, /en) so both map to the same SvelteKit route.
// Runs on server and client; pairs with paraglideMiddleware in hooks.server.ts
// which sets the active locale for rendering.
export const reroute: Reroute = (request) => deLocalizeUrl(request.url).pathname;
