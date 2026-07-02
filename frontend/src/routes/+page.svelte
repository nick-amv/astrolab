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
</script>

<svelte:head>
  <title>{m.app_name()} — {m.home_title()}</title>
  <meta name="description" content={m.home_lead()} />
</svelte:head>

<section class="hero">
  <span class="chip">✦ {m.home_chip()}</span>
  <h1>{m.home_title()}</h1>
  <p class="lead">{m.home_lead()}</p>
  <div class="actions">
    <a class="cta" href={localizeHref("/professions")}>{m.home_cta()} →</a>
    <a class="ghost" href={localizeHref("/professions")}>{m.home_browse()}</a>
  </div>
</section>

{#if spot}
  <section class="spot">
    <div class="spot-text">
      <span class="chip alt">{m.home_spot()}</span>
      <h2>{spot.title}</h2>
      {#if spot.summary}<p>{spot.summary}</p>{/if}
      <div class="tags">
        {#if fact?.salary_low}
          <span class="tag">
            <b>{fact.salary_low.toLocaleString()}–{fact.salary_high?.toLocaleString()} {fact.currency}</b>
            {#if fact.confidence === "estimate"}<span class="est">{m.prof_estimate()}</span>{/if}
          </span>
        {/if}
        <a class="tag link" href={localizeHref(`/professions/${spot.slug}`)}>{m.catalog_title()} →</a>
      </div>
    </div>
    <div class="spot-viz">
      <RiasecRadar values={spot.riasec} labels={shortLabels} size={300} />
      <p class="cap">{m.riasec_caption()}</p>
    </div>
  </section>
{/if}

<style>
  .hero {
    padding: clamp(48px, 9vw, 104px) 0 40px;
    max-width: 20ch;
  }
  .chip.alt {
    color: var(--c2);
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
    max-width: 32ch;
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

  .spot {
    display: grid;
    grid-template-columns: 1fr;
    gap: 32px;
    align-items: center;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow);
    padding: clamp(24px, 4vw, 40px);
    margin: 20px 0 48px;
  }
  @media (min-width: 780px) {
    .spot {
      grid-template-columns: 1.05fr 0.95fr;
    }
  }
  .spot-text h2 {
    font-weight: 800;
    font-size: clamp(26px, 3.4vw, 38px);
    letter-spacing: -0.02em;
    margin: 12px 0 10px;
  }
  .spot-text p {
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
    max-width: 40ch;
  }
  .tags {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 22px;
  }
  .tag {
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 11px 15px;
    font-size: 14px;
    color: var(--muted);
  }
  .tag b {
    color: var(--ink);
  }
  .tag.link {
    text-decoration: none;
    color: var(--c3);
    font-weight: 700;
    transition:
      transform var(--dur) var(--ease),
      border-color var(--dur) var(--ease);
  }
  .tag.link:hover {
    border-color: var(--c3);
    transform: translateY(-1px);
  }
  .cap {
    text-align: center;
    font-size: 12px;
    color: var(--muted);
    margin: 12px 0 0;
    font-weight: 600;
  }
</style>
