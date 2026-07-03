import type { RequestHandler } from "./$types";

// SEO sitemap: content pages + every published occupation. RU-only for now
// (the UI is Russian-only; EN routes exist but aren't linked/promoted).
export const GET: RequestHandler = async ({ fetch, url }) => {
  const origin = url.origin;
  const loc = "ru";

  const res = await fetch("/api/occupations?locale=ru");
  const data = res.ok ? await res.json() : { items: [] };
  const slugs: string[] = data.items.map((i: { slug: string }) => i.slug);

  const urls: string[] = [
    `${origin}/${loc}`,
    `${origin}/${loc}/method`,
    `${origin}/${loc}/professions`,
    `${origin}/${loc}/test`,
    `${origin}/${loc}/tos`,
    `${origin}/${loc}/privacy`,
    ...slugs.map((slug) => `${origin}/${loc}/professions/${slug}`),
  ];

  const body =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    urls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n") +
    `\n</urlset>\n`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml", "Cache-Control": "max-age=3600" },
  });
};
