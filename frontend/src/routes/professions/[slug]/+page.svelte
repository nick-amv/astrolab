<script lang="ts">
  import { countryFor } from "$lib/geo";
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const o = $derived(data.occupation);
  const edu = $derived(data.education);
  // N4 'try it in a week' steps (curated per field; adult-neutral set on this
  // public page — the result page shows the audience-correct set).
  const steps = $derived(
    (o.next_steps ?? []) as { idx: number; text: string; url: string | null }[],
  );

  // Salary/demand facts are per-country. Show the fact for the user's country
  // (en→US, ru→RU) and nothing otherwise — never show RUB to a US visitor.
  // US facts land in EN-3, so EN currently has no fact and the block hides.
  type Fact = {
    country: string;
    salary_low: number | null;
    salary_high: number | null;
    currency: string;
    period: string | null;
    confidence: string | null;
    source: string | null; // bls-oews | rosstat-ozpp | llm-estimate
    as_of_date: string | null;
    demand_note: string | null;
  };
  const userCountry = $derived(countryFor(getLocale()));

  // Source badge: show real data (hh.ru / BLS / Rosstat / INE) distinctly from
  // a rough estimate, rather than a flat "estimate" on both. Tooltip carries
  // the method + as-of. hh facts are refreshed from live vacancies.
  function srcBadge(f: Fact): { label: string; cls: string; tip: string } {
    const on = f.as_of_date ? ` (${f.as_of_date.slice(0, 4)})` : "";
    if (f.source === "hh-vacancies")
      return { label: m.src_hh(), cls: "src-hh", tip: m.src_hh_tip() + on };
    if (f.source === "bls-oews") return { label: m.src_bls(), cls: "src-bls", tip: m.src_bls_tip() + on };
    if (f.source === "rosstat-ozpp")
      return { label: m.src_rosstat(), cls: "src-rosstat", tip: m.src_rosstat_tip() + on };
    if (f.source === "ine-ees")
      return { label: m.src_ine(), cls: "src-ine", tip: m.src_ine_tip() + on };
    if (f.source === "insee-ses")
      return { label: m.src_insee(), cls: "src-ine", tip: m.src_insee_tip() + on };
    if (f.source === "adzuna-jobs")
      return { label: m.src_adzuna(), cls: "src-adzuna", tip: m.src_adzuna_tip() + on };
    return { label: m.prof_estimate(), cls: "src-est", tip: m.src_est_tip() };
  }
  const fact = $derived(
    (o.facts as Fact[] | undefined)?.find((f) => f.country === userCountry) ?? null,
  );

  // Link out to an external catalogue of programs for a field of study (we
  // deliberately don't keep our own school DB). RU -> postupi.online by OKSO
  // code (SPO/college codes are XX.01.* / XX.02.*, higher ed is XX.03/04/05).
  // US -> College Scorecard's official Fields of Study search (its SPA has no
  // verifiable per-major deep link, so we point at the field-of-study search).
  // ES -> todofp.es (official FP portal) for fp-* domains, notasdecorte.es
  // (the de-facto cut-off-grades reference; the official QEDU portal broke in
  // the 2024 ministry reorg) for university degrees.
  // FR -> ONISEP's official formation search by diploma name (its per-formation
  // pages have no stable deep link); Parcoursup is the application portal,
  // linked once below the paths (FR-2).
  function admissionUrl(code: string, title = ""): string {
    const loc = getLocale();
    if (loc === "en") {
      return "https://collegescorecard.ed.gov/search/fos-landing/";
    }
    if (loc === "fr") {
      // search the diploma name, trimmed at the first "/" or "(" so a title like
      // "Licence / BUT Informatique" queries a clean "Licence" phrase
      const q = (title || code).split(/[/(]/)[0].trim();
      return `https://www.onisep.fr/recherche?text=${encodeURIComponent(q)}`;
    }
    if (loc === "es") {
      return code.startsWith("fp-") ? "https://www.todofp.es/" : "https://notasdecorte.es/";
    }
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
      occupationLocation: {
        "@type": "Country",
        name: { US: "United States", ES: "Spain", RU: "Russia", FR: "France" }[userCountry] ?? "Russia",
      },
      ...(fact?.salary_low
        ? {
            estimatedSalary: {
              "@type": "MonetaryAmountDistribution",
              currency: fact.currency,
              duration: fact.period === "year" ? "P1Y" : "P1M",
              minValue: fact.salary_low,
              maxValue: fact.salary_high,
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
      {#if steps.length}
        <section class="try">
          <h2>{m.next_title()}</h2>
          <ol class="try-steps">
            {#each steps as st (st.idx)}
              <li>
                <span class="try-text">{st.text}</span>
                {#if st.url}
                  <a href={st.url} target="_blank" rel="noopener noreferrer" aria-label={st.text}
                    >↗</a
                  >
                {/if}
              </li>
            {/each}
          </ol>
        </section>
      {/if}
      <a class="cta" href={localizeHref("/test")}>{m.prof_cta()} →</a>
    </div>

    <aside class="side">
      <div class="card viz">
        <RiasecRadar values={o.riasec ?? {}} labels={shortLabels} size={260} />
        <p class="cap">{m.prof_estimate_note()}</p>
      </div>

      {#if fact && (fact.salary_low || fact.demand_note)}
        <div class="card">
          <div class="k">{m.prof_salary()}</div>
          {#if fact.salary_low}
            {@const b = srcBadge(fact)}
            <p class="salary">
              {fact.salary_low.toLocaleString()}–{fact.salary_high?.toLocaleString()} {fact.currency}{#if fact.period === "year"}{m.salary_per_year()}{/if}
              <span class="src {b.cls}" title={b.tip}>{b.label}</span>
            </p>
          {/if}
          {#if fact.demand_note}<p class="demand">{fact.demand_note}</p>{/if}
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
                <!-- ES/FR domain codes are internal slugs (no user-facing
                     numeric codes like OKSO/CIP), so show only the level there -->
                {#if getLocale() === "es" || getLocale() === "fr"}
                  {#if d.level}<span class="path-code">{d.level}</span>{/if}
                {:else}
                  <span class="path-code">{d.code}{#if d.level} · {d.level}{/if}</span>
                {/if}
              </div>
              <div class="ege-label">{m.edu_ege()}</div>
              <div class="ege">
                {#each d.ege as e (e)}<span class="ege-chip">{e}</span>{/each}
              </div>
              <a
                class="path-vuz"
                href={admissionUrl(d.code, d.title)}
                target="_blank"
                rel="noopener noreferrer"
              >
                {m.edu_where()} ↗
              </a>
            </div>
          {/each}
        </div>

        {#if getLocale() === "fr"}
          <!-- France's national application portal — the "where you apply" anchor
               that complements the per-diploma ONISEP explore links above -->
          <a
            class="edu-portal"
            href="https://www.parcoursup.fr/"
            target="_blank"
            rel="noopener noreferrer"
          >
            {m.edu_parcoursup()} ↗
          </a>
        {/if}

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
  .try-steps {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .try-steps li {
    font-size: 15px;
    line-height: 1.6;
    color: var(--muted);
    max-width: 58ch;
  }
  .try-steps li::marker {
    color: var(--c3);
    font-weight: 700;
  }
  .try-text {
    color: var(--ink);
  }
  .try-steps a {
    margin-left: 6px;
    color: var(--c3);
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
  }
  .try-steps a:hover {
    text-decoration: underline;
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
  .src {
    display: inline-block;
    margin-left: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.02em;
    vertical-align: middle;
    padding: 2px 8px;
    border-radius: 99px;
    cursor: help;
  }
  .src-bls {
    color: #0a7d4b;
    background: color-mix(in oklab, #12b76a 16%, transparent);
  }
  .src-rosstat {
    color: #1560c0;
    background: color-mix(in oklab, #4f9dff 18%, transparent);
  }
  .src-hh {
    color: #b3001b;
    background: color-mix(in oklab, #ff2b4e 14%, transparent);
  }
  .src-ine {
    color: #8a5a00;
    background: color-mix(in oklab, #f0a202 18%, transparent);
  }
  .src-adzuna {
    color: #0b7a5c;
    background: color-mix(in oklab, #16c79a 16%, transparent);
  }
  .src-est {
    color: var(--muted);
    background: var(--line);
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
  .edu-portal {
    display: inline-block;
    margin-top: 16px;
    font-size: 14px;
    font-weight: 700;
    color: var(--chip-ink);
    text-decoration: none;
  }
  .edu-portal:hover {
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
