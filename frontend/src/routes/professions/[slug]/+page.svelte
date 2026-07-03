<script lang="ts">
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const o = $derived(data.occupation);
  const edu = $derived(data.education);

  // Link out to an external catalogue of universities/colleges for a field of
  // study, keyed by its OKSO code (we deliberately don't keep our own vuz DB).
  // SPO (college) codes are XX.01.* / XX.02.*; higher ed is XX.03/04/05.
  function admissionUrl(code: string): string {
    const mid = code.split(".")[1] ?? "";
    const spo = mid === "01" || mid === "02";
    return spo
      ? `https://postupi.online/specialnost-spo/${code}/`
      : `https://postupi.online/specialnost/${code}/vuzi/`;
  }

  // Localized short month from a "MM-DD" rule — no hardcoded month strings.
  function monthLabel(rule: string): string {
    const [mm, dd] = rule.split("-").map((n) => parseInt(n, 10));
    if (!mm) return "";
    const d = new Date(2000, mm - 1, dd || 1);
    return new Intl.DateTimeFormat(getLocale(), { month: "short" }).format(d);
  }

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

  {#if edu}
    <section class="howto">
      <h2 class="howto-h">{m.prof_howto()}</h2>
      {#if !edu.available || (edu.domains.length === 0 && edu.milestones.length === 0)}
        <p class="edu-none">{m.edu_none()}</p>
      {:else}
        <div class="paths">
          {#each edu.domains as d (d.code)}
            <div class="path">
              <div class="path-top">
                <span class="path-title">{d.title}</span>
                <span class="path-code">{d.code}{#if d.level} · {d.level}{/if}</span>
              </div>
              <div class="ege-label">{m.edu_ege()}</div>
              <div class="ege">
                {#each d.ege as e (e)}<span class="ege-chip">{e}</span>{/each}
              </div>
              <a
                class="path-vuz"
                href={admissionUrl(d.code)}
                target="_blank"
                rel="noopener noreferrer"
              >
                {m.edu_where()} ↗
              </a>
            </div>
          {/each}
        </div>

        {#if edu.milestones.length}
          <div class="timeline">
            <div class="tl-label">{m.edu_deadlines()}</div>
            <ol>
              {#each edu.milestones as ms (ms.date_rule)}
                <li>
                  <span class="tl-when">{monthLabel(ms.date_rule)}</span>
                  <span class="tl-title">{ms.title}</span>
                </li>
              {/each}
            </ol>
          </div>
        {/if}

        <p class="edu-disclaimer">{m.edu_disclaimer()}</p>
      {/if}
    </section>
  {/if}
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

  /* How to get there */
  .howto {
    margin-top: 48px;
    border-top: 1px solid var(--line);
    padding-top: 36px;
  }
  .howto-h {
    font-weight: 800;
    font-size: clamp(24px, 3.4vw, 32px);
    letter-spacing: -0.02em;
    margin: 0 0 22px;
  }
  .paths {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }
  @media (min-width: 640px) {
    .paths {
      grid-template-columns: 1fr 1fr;
    }
  }
  .path {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 20px 22px;
  }
  .path-top {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-bottom: 14px;
  }
  .path-title {
    font-weight: 700;
    font-size: 17px;
  }
  .path-code {
    font-size: 13px;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .ege-label,
  .tl-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .ege {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
  }
  .ege-chip {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 6px 11px;
  }
  .path-vuz {
    display: inline-block;
    margin-top: 14px;
    font-size: 14px;
    font-weight: 700;
    color: var(--chip-ink);
    text-decoration: none;
  }
  .path-vuz:hover {
    text-decoration: underline;
  }
  .timeline {
    margin-top: 26px;
  }
  .timeline ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 10px;
  }
  .timeline li {
    display: flex;
    align-items: baseline;
    gap: 14px;
  }
  .tl-when {
    flex: 0 0 44px;
    font-weight: 800;
    font-size: 13px;
    color: var(--c3);
    text-transform: lowercase;
  }
  .tl-title {
    font-size: 15px;
    line-height: 1.5;
  }
  .edu-disclaimer,
  .edu-none {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
    max-width: 62ch;
    margin-top: 22px;
  }
</style>
