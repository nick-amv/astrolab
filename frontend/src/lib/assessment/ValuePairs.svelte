<script lang="ts">
  import type { Answer, Question } from "$lib/api";
  import { fly } from "svelte/transition";
  import { cubicOut } from "svelte/easing";

  type Axis = { name: string; desc: string };

  let {
    items,
    axes,
    q,
    onDone,
  }: {
    items: Question[]; // each dimension is "axisA|axisB"
    axes: Record<string, Axis>;
    q: string;
    onDone: (answers: Answer[]) => void;
  } = $props();

  let i = $state(0);
  const collected: Answer[] = [];

  const pair = $derived((items[i]?.dimension ?? "|").split("|"));
  const left = $derived(axes[pair[0]] ?? { name: pair[0], desc: "" });
  const right = $derived(axes[pair[1]] ?? { name: pair[1], desc: "" });

  // value 1.0 = first axis chosen, 0.0 = second (see scoring._values_forced_choice)
  function pick(value: number) {
    collected.push({ question_id: items[i].id, value });
    if (i < items.length - 1) i += 1;
    else onDone(collected);
  }
</script>

<div class="deck">
  <div class="bar"><span style="width:{(i / items.length) * 100}%"></span></div>
  <div class="count">{i + 1} / {items.length}</div>
  <div class="q">{q}</div>

  {#key items[i].id}
    <div class="pair" in:fly={{ y: 16, duration: 240, easing: cubicOut }}>
      <button class="opt" onclick={() => pick(1)}>
        <span class="name">{left.name}</span>
        <span class="desc">{left.desc}</span>
      </button>
      <div class="vs">/</div>
      <button class="opt" onclick={() => pick(0)}>
        <span class="name">{right.name}</span>
        <span class="desc">{right.desc}</span>
      </button>
    </div>
  {/key}
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
    margin: 14px 0 6px;
  }
  .q {
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin-bottom: 20px;
  }
  .pair {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: stretch;
    gap: 10px;
  }
  .vs {
    align-self: center;
    color: var(--muted);
    font-weight: 700;
    font-size: 15px;
  }
  .opt {
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 22px 20px;
    min-height: 150px;
    cursor: pointer;
    font-family: inherit;
    transition:
      transform var(--dur) var(--ease),
      border-color var(--dur) var(--ease),
      box-shadow var(--dur) var(--ease);
  }
  .opt:hover {
    transform: translateY(-3px);
    border-color: var(--c3);
    box-shadow: var(--shadow);
  }
  .opt:active {
    transform: translateY(0) scale(0.98);
  }
  .name {
    font-weight: 800;
    font-size: 19px;
    letter-spacing: -0.01em;
  }
  .desc {
    font-size: 14px;
    line-height: 1.4;
    color: var(--muted);
  }
  @media (prefers-reduced-motion: reduce) {
    .bar span,
    .opt {
      transition: none;
    }
  }
</style>
