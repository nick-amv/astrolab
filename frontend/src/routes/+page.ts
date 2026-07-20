import type { PageLoad } from "./$types";
import { countryFor } from "$lib/geo";
import { getLocale } from "$lib/paraglide/runtime";

// The landing spotlight shows a real, published occupation (localized), not a
// hardcoded example — truthful and DRY. Degrades to null if unavailable.
export const load: PageLoad = async ({ fetch }) => {
  const locale = getLocale();
  // Country-scoped like the profession pages (ru->RU, en->US, es->ES) so the
  // spotlight's salary fact matches the visitor's country — no RUB on a US/ES page.
  const country = countryFor(locale);
  const res = await fetch(`/api/occupations/data-analyst?locale=${locale}&country=${country}`);
  const spotlight = res.ok ? await res.json() : null;
  return { spotlight };
};
