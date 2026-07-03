import type { LayoutLoad } from "./$types";
import { getMe } from "$lib/api";

// Auth state for the header (and any page via $page.data.user). SvelteKit's
// fetch forwards the session cookie during SSR.
export const load: LayoutLoad = async ({ fetch }) => {
  const user = await getMe(fetch);
  return { user };
};
