import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const locale = getLocale();
  // Admission data is curated per country. EN users get US (no data yet in
  // EN-1 → the API returns an honest "no verified data" state; US admission
  // lands in EN-2). RU users get the Russian system.
  const country = locale === "en" ? "US" : "RU";
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
