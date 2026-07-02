<script lang="ts">
  import { createShare } from "$lib/api";
  import ResultView from "$lib/ResultView.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const sid = $derived(data.sessionId);

  let copied = $state(false);
  let sharing = $state(false);

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
  <ResultView result={data.result} />
  <div class="actions">
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
    margin: 0 0 28px;
  }
  .actions {
    display: flex;
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
