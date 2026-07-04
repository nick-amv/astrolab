import type { Handle } from "@sveltejs/kit";
import { paraglideMiddleware } from "$lib/paraglide/server";
import { locales, baseLocale } from "$lib/paraglide/runtime";

// Pick the best supported locale from an Accept-Language header. English
// browsers land on /en, everyone else on the default (/ru). Falls back to the
// base locale when nothing matches (DESIGN-EN §3).
function negotiateLocale(header: string | null): string {
  if (!header) return baseLocale;
  const supported = locales as readonly string[];
  const ranked = header
    .split(",")
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const qParam = params.find((p) => p.trim().startsWith("q="));
      const weight = qParam ? parseFloat(qParam.trim().slice(2)) : 1;
      return { primary: tag.trim().toLowerCase().split("-")[0], weight: Number.isNaN(weight) ? 1 : weight };
    })
    .filter((r) => r.primary)
    .sort((a, b) => b.weight - a.weight);
  for (const r of ranked) {
    if (supported.includes(r.primary)) return r.primary;
  }
  return baseLocale;
}

// The bare root has no locale prefix — negotiate one from Accept-Language so
// every rendered URL is locale-qualified (DESIGN §9). /ru and /en are then
// handled by Paraglide's URL strategy.
const handleRoot: Handle = ({ event }) => {
  const loc = negotiateLocale(event.request.headers.get("accept-language"));
  return new Response(null, { status: 307, headers: { location: `/${loc}` } });
};

const handleParaglide: Handle = ({ event, resolve }) =>
  paraglideMiddleware(event.request, ({ request, locale }) => {
    event.request = request;
    return resolve(event, {
      transformPageChunk: ({ html }) => html.replace("%lang%", locale),
    });
  });

export const handle: Handle = ({ event, resolve }) => {
  if (event.url.pathname === "/") {
    return handleRoot({ event, resolve });
  }
  return handleParaglide({ event, resolve });
};
