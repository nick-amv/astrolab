<script lang="ts">
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  const shortLabels = {
    R: m.riasec_r_short(),
    I: m.riasec_i_short(),
    A: m.riasec_a_short(),
    S: m.riasec_s_short(),
    E: m.riasec_e_short(),
    C: m.riasec_c_short(),
  };
  const spot = $derived(data.spotlight);
  const fact = $derived(spot?.facts?.[0]);

  const steps = [
    { t: m.home_how_1_t(), d: m.home_how_1_d() },
    { t: m.home_how_2_t(), d: m.home_how_2_d() },
    { t: m.home_how_3_t(), d: m.home_how_3_d() },
  ];
  const gets = [m.home_get_1(), m.home_get_2(), m.home_get_3(), m.home_get_4()];
  const honesty = [m.home_honesty_1(), m.home_honesty_2(), m.home_honesty_3()];
  const whom = [
    { c: "var(--c2)", t: m.home_whom_teen() },
    { c: "var(--c3)", t: m.home_whom_adult() },
    { c: "var(--c4)", t: m.home_whom_parent() },
  ];
</script>

<svelte:head>
  <title>{m.app_name()} — {m.home_title()}</title>
  <meta name="description" content={m.home_lead()} />
</svelte:head>

<!-- Hero -->
<section class="hero">
  <span class="chip">✦ {m.home_chip()}</span>
  <h1>{m.home_title()}</h1>
  <p class="lead">{m.home_lead()}</p>
  <div class="actions">
    <a class="cta" href={localizeHref("/test")}>{m.home_cta()} →</a>
    <a class="ghost" href={localizeHref("/professions")}>{m.home_browse()}</a>
  </div>
</section>

<!-- How it works: a real 3-step sequence -->
<section class="how">
  <h2 class="sec-h">{m.home_how_title()}</h2>
  <div class="steps">
    {#each steps as s, i (s.t)}
      <div class="step">
        <span class="num">{i + 1}</span>
        <div class="step-t">{s.t}</div>
        <p class="step-d">{s.d}</p>
      </div>
    {/each}
  </div>
</section>

<!-- What you get: checklist + a real result preview -->
<section class="get">
  <div class="get-text">
    <h2 class="sec-h">{m.home_get_title()}</h2>
    <ul>
      {#each gets as g (g)}
        <li>
          <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
            <path d="M4 10.5l4 4 8-9" fill="none" stroke="url(#chk)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            <defs><linearGradient id="chk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--c2)" /><stop offset="1" stop-color="var(--c3)" /></linearGradient></defs>
          </svg>
          <span>{g}</span>
        </li>
      {/each}
    </ul>
  </div>
  {#if spot}
    <div class="preview">
      <span class="chip alt">{m.home_spot()}</span>
      <div class="preview-name">{spot.title}</div>
      <RiasecRadar values={spot.riasec} labels={shortLabels} size={230} />
      {#if fact?.salary_low}
        <div class="preview-fact">
          <b>{fact.salary_low.toLocaleString()}–{fact.salary_high?.toLocaleString()} {fact.currency}</b>
          {#if fact.confidence === "estimate"}<span class="est">{m.prof_estimate()}</span>{/if}
        </div>
      {/if}
    </div>
  {/if}
</section>

<!-- Honesty as a feature -->
<section class="honesty">
  <div class="honesty-inner">
    <h2 class="sec-h light">{m.home_honesty_title()}</h2>
    <ul>
      {#each honesty as h (h)}
        <li>{h}</li>
      {/each}
    </ul>
  </div>
</section>

<!-- Who it's for -->
<section class="whom">
  <h2 class="sec-h">{m.home_whom_t()}</h2>
  <div class="whom-rows">
    {#each whom as w (w.t)}
      <div class="whom-row">
        <span class="dot" style="background:{w.c}"></span>
        <span>{w.t}</span>
      </div>
    {/each}
  </div>
</section>

<!-- Final CTA -->
<section class="final">
  <h2>{m.home_final_t()}</h2>
  <p>{m.home_final_d()}</p>
  <a class="cta" href={localizeHref("/test")}>{m.home_cta()} →</a>
</section>

<style>
  .hero {
    padding: clamp(48px, 9vw, 100px) 0 60px;
    max-width: 680px;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(40px, 7vw, 78px);
    line-height: 1.02;
    letter-spacing: -0.03em;
    margin: 22px 0 20px;
  }
  .lead {
    font-size: 19px;
    line-height: 1.6;
    color: var(--muted);
    max-width: 34ch;
    margin: 0 0 32px;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 22px;
    flex-wrap: wrap;
  }
  .ghost {
    font-weight: 700;
    font-size: 15px;
    color: var(--ink);
    text-decoration: none;
    border-bottom: 2px solid var(--c3);
    padding-bottom: 2px;
  }
  .ghost:hover {
    color: var(--c3);
  }

  .sec-h {
    font-weight: 800;
    font-size: clamp(26px, 4vw, 38px);
    letter-spacing: -0.02em;
    margin: 0 0 32px;
  }

  /* How it works */
  .how {
    padding: 40px 0 60px;
  }
  .steps {
    display: grid;
    grid-template-columns: 1fr;
    gap: 28px;
  }
  @media (min-width: 760px) {
    .steps {
      grid-template-columns: repeat(3, 1fr);
      gap: 32px;
    }
  }
  .step {
    position: relative;
  }
  .num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: var(--grad);
    color: #fff;
    font-weight: 800;
    font-size: 18px;
    box-shadow: var(--shadow-c2);
    margin-bottom: 16px;
  }
  .step-t {
    font-weight: 700;
    font-size: 19px;
    margin-bottom: 8px;
  }
  .step-d {
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
    max-width: 34ch;
  }

  /* What you get */
  .get {
    display: grid;
    grid-template-columns: 1fr;
    gap: 40px;
    align-items: center;
    padding: 40px 0 60px;
  }
  @media (min-width: 820px) {
    .get {
      grid-template-columns: 1.1fr 0.9fr;
      gap: 56px;
    }
  }
  .get-text ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 16px;
  }
  .get-text li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 17px;
    line-height: 1.45;
  }
  .get-text li svg {
    flex: 0 0 auto;
    margin-top: 1px;
  }
  .preview {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow);
    padding: 26px;
    text-align: center;
  }
  .chip.alt {
    color: var(--c2);
  }
  .preview-name {
    font-weight: 800;
    font-size: 22px;
    letter-spacing: -0.01em;
    margin: 12px 0 8px;
  }
  .preview-fact {
    margin-top: 8px;
    font-size: 15px;
    color: var(--muted);
  }
  .preview-fact b {
    color: var(--ink);
  }

  /* Honesty — tinted panel, works in both themes */
  .honesty {
    padding: 8px 0 60px;
  }
  .honesty-inner {
    background:
      linear-gradient(135deg, rgba(255, 95, 143, 0.1), rgba(139, 92, 246, 0.1)),
      var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: clamp(28px, 4vw, 44px);
  }
  .honesty-inner ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 14px;
    max-width: 60ch;
  }
  .honesty-inner li {
    font-size: 17px;
    line-height: 1.5;
    padding-left: 26px;
    position: relative;
  }
  .honesty-inner li::before {
    content: "";
    position: absolute;
    left: 0;
    top: 9px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--grad);
  }
  .sec-h.light {
    margin-bottom: 22px;
  }

  /* Who it's for */
  .whom {
    padding: 8px 0 60px;
  }
  .whom-rows {
    display: grid;
    gap: 14px;
    max-width: 60ch;
  }
  .whom-row {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 18px;
    padding: 14px 0;
    border-bottom: 1px solid var(--line);
  }
  .whom-row .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex: 0 0 auto;
  }

  /* Final CTA */
  .final {
    text-align: center;
    padding: 40px 0 90px;
  }
  .final h2 {
    font-weight: 800;
    font-size: clamp(28px, 5vw, 46px);
    letter-spacing: -0.03em;
    margin: 0 0 12px;
  }
  .final p {
    color: var(--muted);
    font-size: 18px;
    margin: 0 0 28px;
  }
</style>
