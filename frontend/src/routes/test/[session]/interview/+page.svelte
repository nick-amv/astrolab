<script lang="ts">
  import { goto } from "$app/navigation";
  import { type Answer, saveInterview } from "$lib/api";
  import CardDeck from "$lib/assessment/CardDeck.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  let saving = $state(false);

  const textById = $derived(new Map(data.statements.map((s) => [s.id, s.text])));

  async function done(answers: Answer[]) {
    if (saving) return;
    saving = true;
    // Echo the statement text back so the transcript works for LLM-generated
    // statements (their ids aren't in any static table).
    const items = answers.map((a) => ({
      text: textById.get(a.question_id) ?? "",
      value: a.value,
    }));
    await saveInterview(data.sessionId, items);
    await goto(localizeHref(`/result/${data.sessionId}`));
  }
</script>

<svelte:head><title>{m.interview_title()} — {m.app_name()}</title></svelte:head>

<section class="flow">
  <header class="block-head">
    <span class="chip">{m.interview_title()}</span>
    <p>{m.interview_intro()}</p>
  </header>
  {#if saving}
    <div class="computing">
      <div class="spinner"></div>
      <p>{m.test_computing()}</p>
    </div>
  {:else}
    <CardDeck
      items={data.statements}
      labels={{ no: m.val_no(), meh: m.val_meh(), yes: m.val_yes() }}
      onDone={done}
    />
  {/if}
</section>

<style>
  .flow {
    padding: clamp(24px, 5vw, 48px) 0 60px;
    width: 100%;
  }
  .block-head {
    text-align: center;
    max-width: 560px;
    margin: 0 auto 26px;
  }
  .block-head p {
    color: var(--muted);
    font-size: 16px;
    margin: 12px 0 0;
  }
  .computing {
    text-align: center;
    padding: 80px 0;
    color: var(--muted);
  }
  .spinner {
    width: 40px;
    height: 40px;
    margin: 0 auto 18px;
    border-radius: 50%;
    border: 3px solid var(--line);
    border-top-color: var(--c3);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation-duration: 2s;
    }
  }
</style>
