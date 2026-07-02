import type { RequestHandler } from "./$types";

export const GET: RequestHandler = async ({ url }) => {
  const body = `User-agent: *\nAllow: /\nSitemap: ${url.origin}/sitemap.xml\n`;
  return new Response(body, {
    headers: { "Content-Type": "text/plain", "Cache-Control": "max-age=86400" },
  });
};
