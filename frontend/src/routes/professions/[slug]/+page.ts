import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const locale = getLocale();
  const res = await fetch(`/api/occupations/${params.slug}?locale=${locale}`);
  if (res.status === 404) {
    throw error(404, "not found");
  }
  if (!res.ok) {
    throw error(502, "catalog unavailable");
  }
  return { occupation: await res.json() };
};
