<script lang="ts">
  import type { Answer, Question } from "$lib/api";

  let {
    items,
    labels,
    onDone,
  }: {
    items: Question[];
    labels: {
      like: string;
      good: string;
      no: string;
      meh: string;
      yes: string;
      low: string;
      mid: string;
      high: string;
      next: string;
    };
    onDone: (answers: Answer[]) => void;
  } = $props();

  // undefined = untouched. Values 0 / 0.5 / 1.
  const like = $state<Record<string, number | undefined>>({});
  const good = $state<Record<string, number | undefined>>({});

  function finish() {
    const answers: Answer[] = [];
    for (const q of items) {
      const l = like[q.id];
      const g = good[q.id];
      if (l === undefined && g === undefined) continue; // skip untouched
      answers.push({ question_id: q.id, value: (l ?? 0.5) * (g ?? 0.5) });
    }
    onDone(answers);
  }
</script>

<div class="grid">
  {#each items as q (q.id)}
    <div class="subj">
      <div class="name">{q.text}</div>
      <div class="rows">
        <div class="seg-row">
          <span class="lbl">{labels.like}</span>
          <div class="seg">
            <button class:on={like[q.id] === 0} onclick={() => (like[q.id] = 0)}>{labels.no}</button>
            <button class:on={like[q.id] === 0.5} onclick={() => (like[q.id] = 0.5)}>{labels.meh}</button>
            <button class:on={like[q.id] === 1} onclick={() => (like[q.id] = 1)}>{labels.yes}</button>
          </div>
        </div>
        <div class="seg-row">
          <span class="lbl">{labels.good}</span>
          <div class="seg">
            <button class:on={good[q.id] === 0} onclick={() => (good[q.id] = 0)}>{labels.low}</button>
            <button class:on={good[q.id] === 0.5} onclick={() => (good[q.id] = 0.5)}>{labels.mid}</button>
            <button class:on={good[q.id] === 1} onclick={() => (good[q.id] = 1)}>{labels.high}</button>
          </div>
        </div>
      </div>
    </div>
  {/each}
</div>

<div class="foot">
  <button class="cta" onclick={finish}>{labels.next} →</button>
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    max-width: 620px;
    margin: 0 auto;
  }
  @media (min-width: 640px) {
    .grid {
      grid-template-columns: 1fr 1fr;
    }
  }
  .subj {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 16px 18px;
  }
  .name {
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 12px;
  }
  .seg-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 6px 0;
  }
  .lbl {
    flex: 0 0 62px;
    font-size: 12px;
    color: var(--muted);
    font-weight: 600;
  }
  .seg {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 4px;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 3px;
  }
  .seg button {
    border: 0;
    background: transparent;
    border-radius: 7px;
    padding: 7px 4px;
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    transition:
      background var(--dur) var(--ease),
      color var(--dur) var(--ease);
  }
  .seg button.on {
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow-sm);
  }
  .foot {
    display: flex;
    justify-content: center;
    margin-top: 26px;
  }
</style>
