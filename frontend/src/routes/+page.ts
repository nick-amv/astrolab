import type { PageLoad } from "./$types";
import { getLocale } from "$lib/paraglide/runtime";

// The landing spotlight shows a real, published occupation (localized), not a
// hardcoded example — truthful and DRY. Degrades to null if unavailable.
export const load: PageLoad = async ({ fetch }) => {
  const locale = getLocale();
  const res = await fetch(`/api/occupations/data-analyst?locale=${locale}`);
  const spotlight = res.ok ? await res.json() : null;
  return { spotlight };
};
