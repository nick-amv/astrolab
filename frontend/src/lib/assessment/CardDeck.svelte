<script lang="ts">
  import type { Answer, Question } from "$lib/api";
  import { fly } from "svelte/transition";
  import { cubicOut } from "svelte/easing";

  let {
    items,
    labels,
    onDone,
  }: {
    items: Question[];
    labels: { no: string; meh: string; yes: string };
    onDone: (answers: Answer[]) => void;
  } = $props();

  let i = $state(0);
  const collected: Answer[] = [];

  function pick(value: number) {
    collected.push({ question_id: items[i].id, value });
    if (i < items.length - 1) {
      i += 1;
    } else {
      onDone(collected);
    }
  }

  function key(e: KeyboardEvent) {
    if (e.key === "1") pick(0);
    else if (e.key === "2") pick(0.5);
    else if (e.key === "3") pick(1);
  }
</script>

<svelte:window onkeydown={key} />

<div class="deck">
  <div class="bar"><span style="width:{(i / items.length) * 100}%"></span></div>
  <div class="count">{i + 1} / {items.length}</div>

  {#key items[i].id}
    <div class="card" in:fly={{ y: 16, duration: 260, easing: cubicOut }}>
      {items[i].text}
    </div>
  {/key}

  <div class="opts">
    <button class="opt no" onclick={() => pick(0)}><span>{labels.no}</span></button>
    <button class="opt meh" onclick={() => pick(0.5)}><span>{labels.meh}</span></button>
    <button class="opt yes" onclick={() => pick(1)}><span>{labels.yes}</span></button>
  </div>
</div>

<style>
  .deck {
    width: 100%;
    max-width: 560px;
    margin: 0 auto;
  }
  .bar {
    height: 6px;
    background: var(--line);
    border-radius: 99px;
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    background: var(--grad);
    transition: width var(--dur) var(--ease);
  }
  .count {
    text-align: center;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    margin: 14px 0 22px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow);
    min-height: 190px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 34px;
    font-size: clamp(22px, 3.4vw, 30px);
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1.25;
  }
  .opts {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-top: 22px;
  }
  .opt {
    border: 1px solid var(--line);
    background: var(--surface);
    border-radius: 14px;
    padding: 16px 10px;
    font-family: inherit;
    font-weight: 700;
    font-size: 15px;
    color: var(--ink);
    cursor: pointer;
    transition:
      transform var(--dur) var(--ease),
      border-color var(--dur) var(--ease),
      background var(--dur) var(--ease);
  }
  .opt:hover {
    transform: translateY(-2px);
  }
  .opt:active {
    transform: translateY(0) scale(0.97);
  }
  .opt.no:hover {
    border-color: var(--c2);
  }
  .opt.yes:hover {
    border-color: var(--c3);
    background: color-mix(in oklab, var(--c3) 10%, var(--surface));
  }
  @media (prefers-reduced-motion: reduce) {
    .bar span,
    .opt {
      transition: none;
    }
  }
</style>
