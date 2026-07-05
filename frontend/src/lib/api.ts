// Thin client for the assessment API. Relative /api works both in SvelteKit
// load (pass event.fetch) and in the browser (default fetch), same origin.

type Fetch = typeof fetch;

export interface StartBody {
  age_band: string;
  locale: string;
  education_stage?: string;
  country_live?: string;
  country_study?: string;
}

export interface Question {
  id: string;
  dimension: string;
  text: string;
}

export interface QuestionSet {
  blocks: { A: Question[]; B: Question[]; C: Question[] };
  adult: boolean;
}

export interface Answer {
  question_id: string;
  value: number;
}

// N4: one curated 'try it this week' step. url is a search link (may be null).
export interface NextStep {
  idx: number;
  text: string;
  url: string | null;
}

export interface OccItem {
  slug: string;
  title: string;
  score: number;
  why: string | null;
  next_steps?: NextStep[];
}

export interface Result {
  profile: {
    riasec: Record<string, number>;
    klimov: Record<string, number>;
    values: Record<string, number>;
    subjects: Record<string, number>;
  };
  age_band: string | null;
  buckets: { core: OccItem[]; near: OccItem[]; dark_horse: OccItem[] };
  shared?: boolean;
}

export async function startAssessment(body: StartBody): Promise<{ session_id: string }> {
  const r = await fetch("/api/assessment/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("start failed");
  return r.json();
}

export async function getQuestions(
  f: Fetch,
  sessionId: string,
  locale: string,
): Promise<QuestionSet> {
  const r = await f(`/api/assessment/${sessionId}/questions?locale=${locale}`);
  if (!r.ok) throw new Error("questions failed");
  return r.json();
}

export async function saveAnswers(sessionId: string, answers: Answer[]): Promise<void> {
  await fetch(`/api/assessment/${sessionId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
}

export async function scoreSession(sessionId: string): Promise<void> {
  await fetch(`/api/assessment/${sessionId}/score`, { method: "POST" });
}

export async function getResult(
  f: Fetch,
  sessionId: string,
  locale: string,
): Promise<Result | null> {
  const r = await f(`/api/assessment/${sessionId}/result?locale=${locale}`);
  if (r.status === 409) return null;
  if (!r.ok) throw new Error("result failed");
  return r.json();
}

export async function getReport(
  f: Fetch,
  token: string,
  locale: string,
): Promise<Result | null> {
  const r = await f(`/api/report/${token}?locale=${locale}`);
  if (!r.ok) return null;
  return r.json();
}

export async function getInterview(f: Fetch, sessionId: string): Promise<Question[]> {
  const r = await f(`/api/assessment/${sessionId}/interview`);
  if (!r.ok) return [];
  const data = await r.json();
  return data.statements as Question[];
}

export async function saveInterview(
  sessionId: string,
  items: { text: string; value: number }[],
): Promise<void> {
  await fetch(`/api/assessment/${sessionId}/interview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

// Adult flow (Wave 5): paste a resume / experience; the backend extracts context
// (degradable — returns {ok:false} if the LLM is unavailable, and the result
// still works without it).
export async function saveCv(sessionId: string, text: string): Promise<boolean> {
  const r = await fetch(`/api/assessment/${sessionId}/cv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) return false;
  const data = await r.json();
  return Boolean(data.ok);
}

export async function enrichResult(
  sessionId: string,
  locale: string,
): Promise<Result | null> {
  const r = await fetch(`/api/assessment/${sessionId}/enrich?locale=${locale}`, {
    method: "POST",
  });
  if (!r.ok) return null;
  return r.json();
}

// N2: the user's reaction to a matched occupation ("that's me / partly / not me").
export type Verdict = "fits" | "partial" | "not_me";
export async function submitFeedback(
  sessionId: string,
  slug: string,
  verdict: Verdict,
): Promise<boolean> {
  const r = await fetch(`/api/assessment/${sessionId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, verdict }),
  });
  return r.ok;
}

// --- Accounts (magic-link) --------------------------------------------------
export interface Me {
  id: string;
  email: string | null;
}

export interface SavedResult {
  session_id: string;
  finished_at: string | null;
  age_band: string | null;
  top: string[];
}

export async function requestMagicLink(email: string, locale: string): Promise<boolean> {
  const r = await fetch("/api/auth/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, locale }),
  });
  return r.ok;
}

export async function verifyMagicLink(token: string): Promise<Me | null> {
  const r = await fetch("/api/auth/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!r.ok) return null;
  return (await r.json()).user as Me;
}

export async function getMe(f: Fetch): Promise<Me | null> {
  const r = await f("/api/auth/me");
  if (!r.ok) return null;
  return (await r.json()).user as Me | null;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

export async function claimSession(
  sessionId: string,
  parentalConsent = false,
): Promise<{ ok: boolean; needsConsent: boolean }> {
  const r = await fetch("/api/auth/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, parental_consent: parentalConsent }),
  });
  return { ok: r.ok, needsConsent: r.status === 422 };
}

export async function getMyResults(f: Fetch): Promise<SavedResult[] | null> {
  const r = await f("/api/me/results");
  if (r.status === 401) return null;
  if (!r.ok) return [];
  return (await r.json()).results as SavedResult[];
}

export async function deleteAccount(): Promise<boolean> {
  const r = await fetch("/api/me/delete", { method: "POST" });
  return r.ok;
}

// N4: save/toggle a 'try it this week' step (logged-in only). Returns the new
// done state, or null if not signed in / failed.
export async function togglePlanStep(
  slug: string,
  stepIdx: number,
  audience: string,
): Promise<boolean | null> {
  const r = await fetch("/api/me/plan/toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, step_idx: stepIdx, audience }),
  });
  if (!r.ok) return null;
  return Boolean((await r.json()).done);
}

export interface PlanGroup {
  slug: string;
  title: string;
  audience: string;
  steps: (NextStep & { done: boolean })[];
}

export async function getPlan(f: Fetch, locale: string): Promise<PlanGroup[]> {
  const r = await f(`/api/me/plan?locale=${locale}`);
  if (!r.ok) return [];
  return (await r.json()).plans as PlanGroup[];
}

export async function createShare(sessionId: string): Promise<string | null> {
  const r = await fetch(`/api/assessment/${sessionId}/share`, { method: "POST" });
  if (!r.ok) return null;
  const data = await r.json();
  return data.token as string;
}

// N5: parent report (teens only; the backend 422s for adult sessions).
export interface ParentView {
  axes: { axis: string; label: string }[];
  strengths: string[];
  support: string[];
  professions: { slug: string; title: string; why: string | null }[];
}

export async function createParentShare(sessionId: string): Promise<string | null> {
  const r = await fetch(`/api/assessment/${sessionId}/parent-share`, { method: "POST" });
  if (!r.ok) return null;
  return (await r.json()).token as string;
}

export async function getParentReport(
  f: Fetch,
  token: string,
  locale: string,
): Promise<ParentView | null> {
  const r = await f(`/api/parent/${token}?locale=${locale}`);
  if (!r.ok) return null;
  return r.json();
}
