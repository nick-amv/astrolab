<script lang="ts">
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const o = $derived(data.occupation);

  const shortLabels = {
    R: m.riasec_r_short(),
    I: m.riasec_i_short(),
    A: m.riasec_a_short(),
    S: m.riasec_s_short(),
    E: m.riasec_e_short(),
    C: m.riasec_c_short(),
  };

  const jsonLd = $derived(
    JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Occupation",
      name: o.title,
      description: o.summary ?? undefined,
      occupationLocation: { "@type": "Country", name: "Russia" },
      ...(o.facts?.[0]?.salary_low
        ? {
            estimatedSalary: {
              "@type": "MonetaryAmountDistribution",
              currency: o.facts[0].currency,
              minValue: o.facts[0].salary_low,
              maxValue: o.facts[0].salary_high,
            },
          }
        : {}),
    }),
  );
</script>

<svelte:head>
  <title>{o.title} — {m.app_name()}</title>
  <meta name="description" content={o.summary ?? o.title} />
  {@html `<script type="application/ld+json">${jsonLd}<` + `/script>`}
</svelte:head>

<article class="prof">
  <a class="back" href={localizeHref("/professions")}>← {m.catalog_title()}</a>
  <h1>{o.title}</h1>
  {#if o.summary}<p class="summary">{o.summary}</p>{/if}

  <div class="cols">
    <div class="main">
      {#if o.day_in_life}
        <section>
          <h2>{m.prof_day()}</h2>
          <p>{o.day_in_life}</p>
        </section>
      {/if}
      {#if o.who_fits}
        <section>
          <h2>{m.prof_who()}</h2>
          <p>{o.who_fits}</p>
        </section>
      {/if}
      <a class="cta" href={localizeHref("/test")}>{m.prof_cta()} →</a>
    </div>

    <aside class="side">
      <div class="card viz">
        <RiasecRadar values={o.riasec ?? {}} labels={shortLabels} size={260} />
        <p class="cap">{m.prof_estimate_note()}</p>
      </div>

      {#if o.facts?.length}
        <div class="card">
          <div class="k">{m.prof_salary()}</div>
          {#each o.facts as f (f.country)}
            {#if f.salary_low}
              <p class="salary">
                {f.salary_low.toLocaleString()}–{f.salary_high?.toLocaleString()} {f.currency}
                {#if f.confidence === "estimate"}<span class="est">{m.prof_estimate()}</span>{/if}
              </p>
            {/if}
            {#if f.demand_note}<p class="demand">{f.demand_note}</p>{/if}
          {/each}
        </div>
      {/if}
    </aside>
  </div>
</article>

<style>
  .prof {
    padding: 28px 0 60px;
    width: 100%;
  }
  .back {
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    text-decoration: none;
  }
  .back:hover {
    color: var(--c3);
  }
  h1 {
    font-weight: 800;
    font-size: clamp(34px, 5.4vw, 54px);
    letter-spacing: -0.03em;
    margin: 16px 0 14px;
  }
  .summary {
    font-size: 19px;
    color: var(--ink);
    line-height: 1.55;
    max-width: 56ch;
    margin: 0 0 40px;
  }
  .cols {
    display: grid;
    grid-template-columns: 1fr;
    gap: 40px;
  }
  @media (min-width: 760px) {
    .cols {
      grid-template-columns: 1.5fr 1fr;
      gap: 48px;
    }
  }
  .main h2 {
    font-weight: 800;
    font-size: 21px;
    letter-spacing: -0.01em;
    margin: 0 0 10px;
  }
  .main section {
    margin-bottom: 30px;
  }
  .main p {
    font-size: 16px;
    line-height: 1.7;
    color: var(--muted);
    margin: 0;
    max-width: 58ch;
  }
  .main .cta {
    margin-top: 8px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 22px;
    margin-bottom: 16px;
  }
  .viz {
    padding-top: 26px;
  }
  .cap {
    text-align: center;
    font-size: 12px;
    color: var(--muted);
    margin: 12px 0 0;
    line-height: 1.5;
  }
  .k {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 10px;
  }
  .salary {
    font-weight: 800;
    font-size: 20px;
    margin: 0;
  }
  .demand {
    color: var(--muted);
    font-size: 14px;
    margin: 8px 0 0;
  }
</style>
