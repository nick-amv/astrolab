import type { PageLoad } from "./$types";
import { getLocale } from "$lib/paraglide/runtime";

// Public catalog list. SSR-rendered for SEO; only published occupations are
// returned by the API. Uses the SvelteKit fetch so relative /api works on the
// server too.
export interface CatalogItem {
  slug: string;
  title: string;
  field_tag: string | null;
  edu_duration_band: string | null;
  salary_low?: number | null;
  salary_high?: number | null;
  currency?: string | null;
  period?: string | null;
}

export const load: PageLoad = async ({ fetch }) => {
  const locale = getLocale();
  const country = locale === "en" ? "US" : "RU";
  const res = await fetch(`/api/occupations?locale=${locale}&country=${country}`);
  const data = res.ok ? await res.json() : { count: 0, items: [] };
  return { occupations: data.items as CatalogItem[] };
};
