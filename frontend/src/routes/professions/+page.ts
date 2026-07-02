import type { PageLoad } from "./$types";
import { getLocale } from "$lib/paraglide/runtime";

// Public catalog list. SSR-rendered for SEO; only published occupations are
// returned by the API. Uses the SvelteKit fetch so relative /api works on the
// server too.
export const load: PageLoad = async ({ fetch }) => {
  const locale = getLocale();
  const res = await fetch(`/api/occupations?locale=${locale}`);
  const data = res.ok ? await res.json() : { count: 0, items: [] };
  return { occupations: data.items as { slug: string; title: string }[] };
};
