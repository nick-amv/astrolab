import type { PageLoad } from "./$types";
import { redirect } from "@sveltejs/kit";
import { getMyResults, getPlan } from "$lib/api";
import { getLocale, localizeHref } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch }) => {
  const locale = getLocale();
  const [results, plans] = await Promise.all([
    getMyResults(fetch, locale),
    getPlan(fetch, locale),
  ]);
  if (results === null) throw redirect(307, localizeHref("/login")); // not signed in
  return { results, plans };
};
