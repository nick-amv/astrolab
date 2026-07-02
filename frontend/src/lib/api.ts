// Thin client for the assessment API. Relative /api works both in SvelteKit
// load (pass event.fetch) and in the browser (default fetch), same origin.

type Fetch = typeof fetch;

export interface StartBody {
  age_band: string;
  locale: string;
  education_stage?: string;
}

export interface Question {
  id: string;
  dimension: string;
  text: string;
}

export interface QuestionSet {
  blocks: { A: Question[]; B: Question[]; C: Question[] };
}

export interface Answer {
  question_id: string;
  value: number;
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

export async function getResult(f: Fetch, sessionId: string, locale: string) {
  const r = await f(`/api/assessment/${sessionId}/result?locale=${locale}`);
  if (r.status === 409) return null;
  if (!r.ok) throw new Error("result failed");
  return r.json();
}
