import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getParentReport } from "$lib/api";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  const view = await getParentReport(fetch, params.token, getLocale());
  if (!view) throw error(404, "not found");
  return { view };
};
