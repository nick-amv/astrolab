import type { PageLoad } from "./$types";
import { error } from "@sveltejs/kit";
import { getQuestions } from "$lib/api";
import { getLocale } from "$lib/paraglide/runtime";

export const load: PageLoad = async ({ fetch, params }) => {
  try {
    const questions = await getQuestions(fetch, params.session, getLocale());
    return { sessionId: params.session, questions };
  } catch {
    throw error(404, "session not found");
  }
};
