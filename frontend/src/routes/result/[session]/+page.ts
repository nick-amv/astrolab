import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getResult } from "$lib/api";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const result = await getResult(fetch, params.session, getLocale());
  if (!result) throw error(404, "no result");
  return { sessionId: params.session, result };
};
