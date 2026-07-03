import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getInterview } from "$lib/api";

export const load: PageLoad = async ({ fetch, params }) => {
  const statements = await getInterview(fetch, params.session);
  if (statements.length === 0) throw error(404, "no interview");
  return { sessionId: params.session, statements };
};
