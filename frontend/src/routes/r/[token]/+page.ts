import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getReport } from "$lib/api";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const result = await getReport(fetch, params.token, getLocale());
  if (!result) throw error(404, "not found");
  return { result };
};
