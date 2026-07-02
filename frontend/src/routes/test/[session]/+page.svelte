<script lang="ts">
  import { goto } from "$app/navigation";
  import { type Answer, saveAnswers, scoreSession } from "$lib/api";
  import CardDeck from "$lib/assessment/CardDeck.svelte";
  import SubjectGrid from "$lib/assessment/SubjectGrid.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const sid = $derived(data.sessionId);
  const blocks = $derived(data.questions.blocks);

  // A (interests) → B (subjects) → C (values) → scoring
  let stage = $state<"A" | "B" | "C" | "scoring">("A");

  async function done(answers: Answer[], next: "B" | "C" | "scoring") {
    await saveAnswers(sid, answers);
    if (next === "scoring") {
      stage = "scoring";
      await scoreSession(sid);
      await goto(localizeHref(`/result/${sid}`));
    } else {
      stage = next;
      window.scrollTo({ top: 0 });
    }
  }
</script>

<svelte:head><title>{m.test_title()} — {m.app_name()}</title></svelte:head>

<section class="flow">
  {#if stage === "A"}
    <header class="block-head">
      <span class="chip">{m.block_a_title()}</span>
      <p>{m.block_a_intro()}</p>
    </header>
    <CardDeck
      items={blocks.A}
      labels={{ no: m.ans_no(), meh: m.ans_meh(), yes: m.ans_yes() }}
      onDone={(a) => done(a, "B")}
    />
  {:else if stage === "B"}
    <header class="block-head">
      <span class="chip">{m.block_b_title()}</span>
      <p>{m.block_b_intro()}</p>
    </header>
    <SubjectGrid
      items={blocks.B}
      labels={{
        like: m.subj_like(),
        good: m.subj_good(),
        no: m.ans_no(),
        meh: m.ans_meh(),
        yes: m.ans_yes(),
        low: m.lvl_low(),
        mid: m.lvl_mid(),
        high: m.lvl_high(),
        next: m.test_next(),
      }}
      onDone={(a) => done(a, "C")}
    />
  {:else if stage === "C"}
    <header class="block-head">
      <span class="chip">{m.block_c_title()}</span>
      <p>{m.block_c_intro()}</p>
    </header>
    <CardDeck
      items={blocks.C}
      labels={{ no: m.val_no(), meh: m.val_meh(), yes: m.val_yes() }}
      onDone={(a) => done(a, "scoring")}
    />
  {:else}
    <div class="computing">
      <div class="spinner"></div>
      <p>{m.test_computing()}</p>
    </div>
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
