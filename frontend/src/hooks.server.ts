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

const LOCALE_COOKIE = "PARAGLIDE_LOCALE";

// The bare root has no locale prefix — an explicit earlier choice (cookie)
// wins, then Accept-Language, so switching to /es survives coming back via
// the bare domain instead of silently resetting to the browser default.
const handleRoot: Handle = ({ event }) => {
  const remembered = event.cookies.get(LOCALE_COOKIE);
  const loc =
    remembered && (locales as readonly string[]).includes(remembered)
      ? remembered
      : negotiateLocale(event.request.headers.get("accept-language"));
  return new Response(null, { status: 307, headers: { location: `/${loc}` } });
};

const handleParaglide: Handle = ({ event, resolve }) =>
  paraglideMiddleware(event.request, ({ request, locale }) => {
    event.request = request;
    // Persist the visited locale: the switcher is plain links (no setLocale()
    // call), so without this the cookie is never written and the language
    // "resets" whenever the URL loses its prefix.
    if (event.cookies.get(LOCALE_COOKIE) !== locale) {
      event.cookies.set(LOCALE_COOKIE, locale, {
        path: "/",
        maxAge: 60 * 60 * 24 * 365,
        sameSite: "lax",
        httpOnly: false, // the paraglide client runtime reads it too
      });
    }
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
