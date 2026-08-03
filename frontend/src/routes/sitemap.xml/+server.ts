import type { RequestHandler } from "./$types";

// SEO sitemap: content pages + every published occupation, in every locale.
// Each URL carries hreflang alternates (ru, en, es, fr, x-default) so search
// engines serve the right language per user (DESIGN-EN §3).
export const GET: RequestHandler = async ({ fetch, url }) => {
  const origin = url.origin;
  const locs = ["ru", "en", "es", "fr", "de"] as const;

  // Slugs are language-neutral ids shared across locales, so one fetch is enough.
  const res = await fetch("/api/occupations?locale=ru");
  const data = res.ok ? await res.json() : { items: [] };
  const slugs: string[] = data.items.map((i: { slug: string }) => i.slug);

  const paths: string[] = [
    "",
    "/method",
    "/professions",
    "/test",
    "/tos",
    "/privacy",
    ...slugs.map((slug) => `/professions/${slug}`),
  ];

  const alternates = (p: string): string =>
    locs
      .map((l) => `<xhtml:link rel="alternate" hreflang="${l}" href="${origin}/${l}${p}"/>`)
      .join("") + `<xhtml:link rel="alternate" hreflang="x-default" href="${origin}/ru${p}"/>`;

  const entries: string[] = [];
  for (const loc of locs) {
    for (const p of paths) {
      entries.push(`  <url><loc>${origin}/${loc}${p}</loc>${alternates(p)}</url>`);
    }
  }

  // Journal — static HTML under /blog/ (ru flat, others /blog/<locale>/…). URLs
  // and per-locale hreflang come from the blog manifest so new articles appear
  // automatically. The manifest lives in the static dir, fetched same-origin.
  // Slugs are localized per locale, so the URL must come from the manifest
  // entry itself — deriving it from the article id would emit the old
  // transliterated paths, which now only exist as 301s.
  type BlogArticle = { slug: string; i18n?: Record<string, { url?: string }> };
  const blogUrl = (a: BlogArticle, loc: string): string | null => {
    const path = a.i18n?.[loc]?.url;
    return path ? `${origin}${path}` : null;
  };
  const blogAlternates = (a: BlogArticle): string =>
    locs
      .map((l) => {
        const href = blogUrl(a, l);
        return href ? `<xhtml:link rel="alternate" hreflang="${l}" href="${href}"/>` : "";
      })
      .join("") +
    (blogUrl(a, "en")
      ? `<xhtml:link rel="alternate" hreflang="x-default" href="${blogUrl(a, "en")}"/>`
      : "");
  try {
    const bres = await fetch("/blog/index.json");
    if (bres.ok) {
      const articles: BlogArticle[] = await bres.json();
      entries.push(`  <url><loc>${origin}/blog/</loc></url>`);
      for (const a of articles) {
        for (const loc of locs) {
          const href = blogUrl(a, loc);
          if (href) entries.push(`  <url><loc>${href}</loc>${blogAlternates(a)}</url>`);
        }
      }
    }
  } catch {
    // no manifest yet — skip the blog section, keep the rest of the sitemap valid
  }

  const body =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" ` +
    `xmlns:xhtml="http://www.w3.org/1999/xhtml">\n` +
    entries.join("\n") +
    `\n</urlset>\n`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml", "Cache-Control": "max-age=3600" },
  });
};
