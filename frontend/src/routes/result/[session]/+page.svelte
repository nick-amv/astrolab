<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { claimSession, createShare, enrichResult, type Result } from "$lib/api";
  import ResultView from "$lib/ResultView.svelte";
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const sid = $derived(data.sessionId);
  const user = $derived($page.data.user);

  // Show the deterministic result instantly; the LLM "why you" + re-rank arrives
  // asynchronously so the user never waits on the shared LLM (DESIGN §4.4).
  let enriched = $state<Result | null>(null);
  let enriching = $state(true);
  const result = $derived(enriched ?? data.result);

  onMount(async () => {
    // Only call the (slow) LLM if this result hasn't been enriched yet — avoids
    // re-running it on every reload/share.
    if (data.result.buckets.core.some((o) => o.why)) {
      enriching = false;
      return;
    }
    const r = await enrichResult(data.sessionId, getLocale());
    if (r) enriched = r;
    enriching = false;
  });

  let copied = $state(false);
  let sharing = $state(false);

  // Save result to an account (claim). Minors (14-16) must confirm consent.
  const isMinor = $derived(result.age_band === "14-16");
  let saved = $state(false);
  let saving = $state(false);
  let consent = $state(false);

  async function save() {
    if (saving || saved) return;
    if (!user) {
      // remember which result to attach, then send them to sign in
      try {
        localStorage.setItem("astrolab_claim", sid);
      } catch {
        /* ignore */
      }
      await goto(localizeHref("/login"));
      return;
    }
    saving = true;
    const { ok } = await claimSession(sid, consent);
    saving = false;
    if (ok) saved = true;
  }

  async function share() {
    if (sharing) return;
    sharing = true;
    const token = await createShare(sid);
    sharing = false;
    if (!token) return;
    const url = location.origin + localizeHref(`/r/${token}`);
    await navigator.clipboard?.writeText(url);
    copied = true;
    setTimeout(() => (copied = false), 2200);
  }
</script>

<svelte:head><title>{m.result_title()} — {m.app_name()}</title></svelte:head>

<section class="result">
  <h1>{m.result_title()}</h1>
  {#if enriching}<p class="enriching">{m.result_enriching()}</p>{/if}
  <ResultView {result} />

  <div class="save">
    {#if saved}
      <span class="saved">✓ {m.result_saved()}</span>
    {:else}
      {#if user && isMinor}
        <label class="consent">
          <input type="checkbox" bind:checked={consent} />
          <span>{m.result_consent()}</span>
        </label>
      {/if}
      <button
        class="ghost"
        onclick={save}
        disabled={saving || (!!user && isMinor && !consent)}
      >
        {user ? m.result_save() : m.result_save_login()}
      </button>
    {/if}
  </div>

  <div class="actions">
    <a class="cta" href={localizeHref(`/test/${sid}/interview`)}>{m.result_interview_cta()} →</a>
    <button class="ghost" onclick={share} disabled={sharing}>
      {copied ? m.result_share_done() : m.result_share()}
    </button>
    <a class="ghost" href={localizeHref("/test")}>{m.result_retake()}</a>
  </div>
</section>

<style>
  .result {
    padding: clamp(28px, 5vw, 56px) 0 60px;
    width: 100%;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(32px, 5vw, 52px);
    letter-spacing: -0.03em;
    margin: 0 0 12px;
  }
  .enriching {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--chip-ink);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 6px 14px;
    margin: 0 0 24px;
  }
  .save {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    margin: 8px 0 22px;
  }
  .saved {
    font-weight: 700;
    font-size: 15px;
    color: var(--c3);
  }
  .consent {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--muted);
    cursor: pointer;
    max-width: 42ch;
  }
  .consent input {
    accent-color: var(--c3);
    width: 18px;
    height: 18px;
    flex: none;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }
  .ghost {
    font-family: inherit;
    font-weight: 700;
    font-size: 15px;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 12px 22px;
    text-decoration: none;
    cursor: pointer;
    transition: border-color var(--dur) var(--ease);
  }
  .ghost:hover {
    border-color: var(--c3);
    color: var(--c3);
  }
  .ghost:disabled {
    opacity: 0.6;
  }
</style>
