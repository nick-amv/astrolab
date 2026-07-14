import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { countryFor } from "$lib/geo";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const locale = getLocale();
  // Facts and admission data are curated per country (ru->RU, en->US, es->ES).
  const country = countryFor(locale);
  const [res, eduRes] = await Promise.all([
    // country-scoped so the page (and its cached fetch payload) only ever
    // carries the user's country facts — no RUB on a US page.
    fetch(`/api/occupations/${params.slug}?locale=${locale}&country=${country}`),
    fetch(`/api/occupations/${params.slug}/education?country=${country}`),
  ]);
  if (res.status === 404) {
    throw error(404, "not found");
  }
  if (!res.ok) {
    throw error(502, "catalog unavailable");
  }
  const education = eduRes.ok ? await eduRes.json() : null;
  return { occupation: await res.json(), education };
};
