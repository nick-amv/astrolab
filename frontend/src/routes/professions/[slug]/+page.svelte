<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const o = $derived(data.occupation);

  const RIASEC = ["R", "I", "A", "S", "E", "C"] as const;
  const riasecLabel: Record<string, () => string> = {
    R: m.riasec_r,
    I: m.riasec_i,
    A: m.riasec_a,
    S: m.riasec_s,
    E: m.riasec_e,
    C: m.riasec_c,
  };

  // schema.org Occupation for rich results / AI citation.
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
    </div>

    <aside class="side">
      <section class="riasec">
        <h2>{m.prof_riasec()}</h2>
        {#each RIASEC as axis (axis)}
          <div class="bar-row">
            <span class="bar-label">{riasecLabel[axis]()}</span>
            <span class="bar-track">
              <span class="bar-fill" style="width: {Math.round((o.riasec?.[axis] ?? 0) * 100)}%"
              ></span>
            </span>
          </div>
        {/each}
        {#if o.riasec_source === "llm"}
          <p class="note">{m.prof_estimate_note()}</p>
        {/if}
      </section>

      {#if o.facts?.length}
        <section class="facts">
          <h2>{m.prof_salary()}</h2>
          {#each o.facts as f (f.country)}
            <p class="salary">
              {#if f.salary_low}
                {f.salary_low.toLocaleString()}–{f.salary_high?.toLocaleString()}
                {f.currency}
              {/if}
              {#if f.confidence === "estimate"}
                <span class="estimate">{m.prof_estimate()}</span>
              {/if}
            </p>
            {#if f.demand_note}<p class="demand">{f.demand_note}</p>{/if}
          {/each}
        </section>
      {/if}
    </aside>
  </div>

  <a class="cta" href={localizeHref("/")}>{m.prof_cta()}</a>
</article>

<style>
  .prof {
    padding: 32px 0 60px;
    width: 100%;
  }
  .back {
    font-family: system-ui, sans-serif;
    font-size: 13px;
    color: var(--muted);
    text-decoration: none;
  }
  .back:hover {
    color: var(--accent);
  }
  h1 {
    font-size: clamp(30px, 5vw, 46px);
    font-weight: 500;
    margin: 16px 0 12px;
  }
  .summary {
    font-family: system-ui, sans-serif;
    font-size: 18px;
    color: var(--ink);
    max-width: 60ch;
    line-height: 1.55;
    margin: 0 0 32px;
  }
  .cols {
    display: grid;
    grid-template-columns: 1fr;
    gap: 32px;
  }
  @media (min-width: 720px) {
    .cols {
      grid-template-columns: 1.6fr 1fr;
    }
  }
  h2 {
    font-size: 14px;
    font-family: system-ui, sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin: 0 0 10px;
  }
  .main section {
    margin-bottom: 26px;
  }
  .main p {
    font-family: system-ui, sans-serif;
    line-height: 1.65;
    color: var(--ink);
    margin: 0;
    max-width: 56ch;
  }
  .side section {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 16px;
  }
  .bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 8px 0;
    font-family: system-ui, sans-serif;
    font-size: 13px;
  }
  .bar-label {
    flex: 0 0 42%;
    color: var(--muted);
  }
  .bar-track {
    flex: 1;
    height: 6px;
    background: var(--line);
    border-radius: 3px;
    overflow: hidden;
  }
  .bar-fill {
    display: block;
    height: 100%;
    background: var(--accent);
  }
  .note,
  .demand {
    font-family: system-ui, sans-serif;
    font-size: 12px;
    color: var(--muted);
    margin: 10px 0 0;
  }
  .salary {
    font-family: system-ui, sans-serif;
    font-size: 17px;
    color: var(--ink);
    margin: 0;
  }
  .estimate {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 1px 6px;
    margin-left: 6px;
    vertical-align: middle;
  }
  .cta {
    display: inline-block;
    margin-top: 36px;
    padding: 13px 22px;
    border-radius: 8px;
    background: var(--accent);
    color: #08122a;
    font-family: system-ui, sans-serif;
    font-weight: 600;
    text-decoration: none;
  }
</style>
