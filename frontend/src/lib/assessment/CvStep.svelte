<script lang="ts">
  import { fly } from "svelte/transition";
  import { cubicOut } from "svelte/easing";

  let {
    labels,
    onDone,
  }: {
    labels: {
      title: string;
      intro: string;
      placeholder: string;
      submit: string;
      skip: string;
      note: string;
    };
    // text is "" when the user skips
    onDone: (text: string) => void;
  } = $props();

  let text = $state("");
  let busy = $state(false);
  const ready = $derived(text.trim().length >= 20);

  function submit() {
    if (busy) return;
    busy = true;
    onDone(text.trim());
  }
  function skip() {
    if (busy) return;
    busy = true;
    onDone("");
  }
</script>

<div class="cv" in:fly={{ y: 16, duration: 260, easing: cubicOut }}>
  <textarea
    bind:value={text}
    placeholder={labels.placeholder}
    rows="8"
    disabled={busy}
  ></textarea>
  <p class="note">{labels.note}</p>
  <div class="opts">
    <button class="ghost" onclick={skip} disabled={busy}>{labels.skip}</button>
    <button class="cta" onclick={submit} disabled={!ready || busy}>
      {labels.submit} →
    </button>
  </div>
</div>

<style>
  .cv {
    width: 100%;
    max-width: 560px;
    margin: 0 auto;
  }
  textarea {
    width: 100%;
    resize: vertical;
    min-height: 190px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 18px 20px;
    font-family: inherit;
    font-size: 16px;
    line-height: 1.5;
    color: var(--ink);
    transition: border-color var(--dur) var(--ease);
  }
  textarea:focus {
    outline: none;
    border-color: var(--c3);
  }
  textarea::placeholder {
    color: var(--muted);
  }
  .note {
    color: var(--muted);
    font-size: 13px;
    margin: 12px 2px 0;
  }
  .opts {
    display: flex;
    gap: 10px;
    justify-content: space-between;
    align-items: center;
    margin-top: 22px;
  }
  .ghost {
    border: 1px solid var(--line);
    background: var(--surface);
    border-radius: 14px;
    padding: 14px 22px;
    font-family: inherit;
    font-weight: 700;
    font-size: 15px;
    color: var(--muted);
    cursor: pointer;
    transition:
      transform var(--dur) var(--ease),
      color var(--dur) var(--ease);
  }
  .ghost:hover:not(:disabled) {
    color: var(--ink);
    transform: translateY(-2px);
  }
  .cta:disabled,
  .ghost:disabled {
    opacity: 0.5;
    cursor: default;
  }
  @media (prefers-reduced-motion: reduce) {
    textarea,
    .ghost {
      transition: none;
    }
  }
</style>
