import type { RequestHandler } from "./$types";

// SEO sitemap: static pages + every published occupation, in both locales.
export const GET: RequestHandler = async ({ fetch, url }) => {
  const origin = url.origin;
  const locales = ["ru", "en"];

  const res = await fetch("/api/occupations?locale=ru");
  const data = res.ok ? await res.json() : { items: [] };
  const slugs: string[] = data.items.map((i: { slug: string }) => i.slug);

  const urls: string[] = [];
  for (const loc of locales) {
    urls.push(`${origin}/${loc}`);
    urls.push(`${origin}/${loc}/professions`);
    for (const slug of slugs) {
      urls.push(`${origin}/${loc}/professions/${slug}`);
    }
  }

  const body =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    urls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n") +
    `\n</urlset>\n`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml", "Cache-Control": "max-age=3600" },
  });
};
