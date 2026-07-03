import type { PageLoad } from "./$types";
import { redirect } from "@sveltejs/kit";
import { getMyResults } from "$lib/api";
import { localizeHref } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch }) => {
  const results = await getMyResults(fetch);
  if (results === null) throw redirect(307, localizeHref("/login")); // not signed in
  return { results };
};
