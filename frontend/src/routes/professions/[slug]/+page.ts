import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const locale = getLocale();
  const [res, eduRes] = await Promise.all([
    fetch(`/api/occupations/${params.slug}?locale=${locale}`),
    fetch(`/api/occupations/${params.slug}/education?country=RU`),
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
