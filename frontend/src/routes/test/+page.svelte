<script lang="ts">
  import { goto } from "$app/navigation";
  import { startAssessment } from "$lib/api";
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";

  const ages = [
    { v: "14-16", l: m.age_14_16() },
    { v: "17-19", l: m.age_17_19() },
    { v: "20-23", l: m.age_20_23() },
    { v: "24+", l: m.age_24() },
  ];
  const stages = [
    { v: "school", l: m.stage_school() },
    { v: "college", l: m.stage_college() },
    { v: "university", l: m.stage_university() },
    { v: "working", l: m.stage_working() },
  ];

  let age = $state("");
  let stage = $state("");
  let busy = $state(false);

  async function begin() {
    if (!age || busy) return;
    busy = true;
    try {
      const country = getLocale() === "en" ? "US" : "RU";
      const { session_id } = await startAssessment({
        age_band: age,
        locale: getLocale(),
        education_stage: stage || undefined,
        country_live: country,
        country_study: country,
      });
      await goto(localizeHref(`/test/${session_id}`));
    } catch {
      busy = false;
    }
  }
</script>

<svelte:head><title>{m.test_title()} — {m.app_name()}</title></svelte:head>

<section class="onb">
  <h1>{m.test_title()}</h1>
  <p class="intro">{m.test_intro()}</p>

  <div class="q">
    <div class="q-label">{m.test_age_q()}</div>
    <div class="choices">
      {#each ages as a (a.v)}
        <button class:on={age === a.v} onclick={() => (age = a.v)}>{a.l}</button>
      {/each}
    </div>
  </div>

  <div class="q">
    <div class="q-label">{m.test_stage_q()}</div>
    <div class="choices">
      {#each stages as s (s.v)}
        <button class:on={stage === s.v} onclick={() => (stage = s.v)}>{s.l}</button>
      {/each}
    </div>
  </div>

  <button class="cta start" disabled={!age || busy} onclick={begin}>
    {busy ? "…" : m.test_start()} →
  </button>
  <p class="note">{m.test_anon_note()}</p>
</section>

<style>
  .onb {
    padding: clamp(32px, 6vw, 64px) 0 60px;
    max-width: 560px;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(30px, 5vw, 46px);
    letter-spacing: -0.03em;
    margin: 0 0 14px;
  }
  .intro {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.6;
    margin: 0 0 36px;
  }
  .q {
    margin-bottom: 28px;
  }
  .q-label {
    font-weight: 700;
    margin-bottom: 12px;
  }
  .choices {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .choices button {
    border: 1px solid var(--line);
    background: var(--surface);
    border-radius: 99px;
    padding: 11px 20px;
    font-family: inherit;
    font-weight: 600;
    font-size: 15px;
    color: var(--ink);
    cursor: pointer;
    transition:
      border-color var(--dur) var(--ease),
      transform var(--dur) var(--ease);
  }
  .choices button:hover {
    transform: translateY(-1px);
  }
  .choices button.on {
    border-color: var(--c3);
    background: color-mix(in oklab, var(--c3) 12%, var(--surface));
  }
  .start {
    margin-top: 12px;
    border: 0;
    cursor: pointer;
    font-family: inherit;
  }
  .start:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .note {
    color: var(--muted);
    font-size: 13px;
    margin: 16px 0 0;
  }
</style>
