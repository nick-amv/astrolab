import type { Handle } from "@sveltejs/kit";
import { paraglideMiddleware } from "$lib/paraglide/server";

// The bare root has no locale prefix — send it to the default locale (ru) so
// every rendered URL is locale-qualified (DESIGN §9). /ru and /en are then
// handled by Paraglide's URL strategy.
const handleRoot: Handle = ({ event, resolve }) => {
  if (event.url.pathname === "/") {
    return new Response(null, { status: 307, headers: { location: "/ru" } });
  }
  return resolve(event);
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
