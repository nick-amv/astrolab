<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";

  const basis = [
    {
      t: m.method_riasec_t(),
      d: m.method_riasec_d(),
      links: [
        { label: m.method_src_holland(), href: "https://en.wikipedia.org/wiki/Holland_Codes" },
        { label: m.method_src_onet(), href: "https://www.onetonline.org/" },
      ],
    },
    {
      t: m.method_klimov_t(),
      d: m.method_klimov_d(),
      links: [{ label: m.method_src_klimov(), href: m.method_klimov_href() }],
    },
    { t: m.method_values_t(), d: m.method_values_d(), links: [] },
    { t: m.method_subjects_t(), d: m.method_subjects_d(), links: [] },
  ];
  const scoring = [
    { t: m.method_det_t(), d: m.method_det_d() },
    { t: m.method_age_t(), d: m.method_age_d() },
    { t: m.method_ai_t(), d: m.method_ai_d() },
  ];
  const limits = [m.method_limit_1(), m.method_limit_2(), m.method_limit_3(), m.method_limit_4()];
  // Where the salary numbers come from — country-scoped like the facts
  // themselves: each locale only sees its own country's sources
  // (ru -> RU, en -> US, es -> ES).
  const DATA_SOURCES: Record<string, { t: string; d: string; links: { label: string; href: string }[] }[]> = {
    en: [
      {
        t: m.method_data_us_t(),
        d: m.method_data_us_d(),
        links: [{ label: m.src_bls(), href: "https://www.bls.gov/oes/" }],
      },
    ],
    es: [
      {
        t: m.method_data_es_t(),
        d: m.method_data_es_d(),
        links: [
          { label: m.src_adzuna(), href: "https://www.adzuna.es/" },
          { label: m.src_ine(), href: "https://www.ine.es/" },
        ],
      },
    ],
    fr: [
      {
        t: m.method_data_fr_t(),
        d: m.method_data_fr_d(),
        links: [
          { label: m.src_adzuna(), href: "https://www.adzuna.fr/" },
          { label: m.src_insee(), href: "https://www.insee.fr/" },
        ],
      },
    ],
    ru: [
      {
        t: m.method_data_ru_t(),
        d: m.method_data_ru_d(),
        links: [
          { label: m.src_hh(), href: "https://hh.ru" },
          { label: m.src_rosstat(), href: "https://rosstat.gov.ru/compendium/document/60671" },
        ],
      },
    ],
  };
  const dataSources = DATA_SOURCES[getLocale()] ?? DATA_SOURCES.ru;
</script>

<svelte:head>
  <title>{m.method_title()} — {m.app_name()}</title>
  <meta name="description" content={m.method_lede()} />
</svelte:head>

<article class="doc">
  <header class="lede">
    <span class="chip">{m.nav_method()}</span>
    <h1>{m.method_title()}</h1>
    <p class="sub">{m.method_lede()}</p>
  </header>

  <section>
    <h2>{m.method_s1_t()}</h2>
    <div class="cards">
      {#each basis as item (item.t)}
        <div class="card">
          <h3>{item.t}</h3>
          <p>{item.d}</p>
          {#if item.links.length}
            <div class="srcs">
              {#each item.links as l (l.label)}
                {#if l.href}
                  <a href={l.href} target="_blank" rel="noopener noreferrer">{l.label} ↗</a>
                {:else}
                  <span class="src-plain">{l.label}</span>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <section>
    <h2>{m.method_s2_t()}</h2>
    <div class="cards">
      {#each scoring as item (item.t)}
        <div class="card">
          <h3>{item.t}</h3>
          <p>{item.d}</p>
        </div>
      {/each}
    </div>
  </section>

  <section class="honest">
    <h2>{m.method_s3_t()}</h2>
    <ul>
      {#each limits as line (line)}
        <li>{line}</li>
      {/each}
    </ul>
  </section>

  <section>
    <h2>{m.method_data_t()}</h2>
    <div class="cards">
      {#each dataSources as item (item.t)}
        <div class="card">
          <h3>{item.t}</h3>
          <p>{item.d}</p>
          <div class="srcs">
            {#each item.links as l (l.label)}
              <a href={l.href} target="_blank" rel="noopener noreferrer">{l.label} ↗</a>
            {/each}
          </div>
        </div>
      {/each}
    </div>
    <p class="badge-note">{m.method_data_badge_d()}</p>
  </section>

  <section class="data">
    <h2>{m.method_s4_t()}</h2>
    <p>
      {m.method_s4_d()}
      <a href={localizeHref("/privacy")}>{m.privacy_link()}</a>.
    </p>
  </section>

  <div class="foot">
    <a class="cta" href={localizeHref("/test")}>{m.method_cta()} →</a>
  </div>
</article>

<style>
  .doc {
    padding: clamp(24px, 5vw, 44px) 0 64px;
    max-width: 780px;
    margin: 0 auto;
  }
  .lede {
    margin-bottom: 40px;
  }
  .lede h1 {
    font-size: clamp(30px, 6vw, 46px);
    letter-spacing: -0.02em;
    line-height: 1.05;
    margin: 16px 0 14px;
  }
  .sub {
    color: var(--muted);
    font-size: clamp(16px, 2.2vw, 19px);
    line-height: 1.55;
    max-width: 60ch;
  }
  section {
    margin: 34px 0;
  }
  h2 {
    font-size: 22px;
    letter-spacing: -0.01em;
    margin: 0 0 18px;
  }
  .cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }
  @media (min-width: 640px) {
    .cards {
      grid-template-columns: 1fr 1fr;
    }
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 20px 22px;
  }
  .card h3 {
    font-size: 16px;
    font-weight: 800;
    margin: 0 0 8px;
  }
  .card p {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.5;
    margin: 0;
  }
  .srcs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: 14px;
  }
  .srcs a {
    font-size: 13px;
    font-weight: 600;
    color: var(--chip-ink);
    text-decoration: none;
  }
  .srcs a:hover {
    text-decoration: underline;
  }
  .src-plain {
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
  }
  .honest {
    background: var(--grad-soft, color-mix(in oklab, var(--c3) 8%, var(--surface)));
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 24px 26px;
  }
  .honest h2 {
    margin-bottom: 12px;
  }
  .honest ul {
    margin: 0;
    padding-left: 20px;
  }
  .honest li {
    color: var(--ink);
    font-size: 15px;
    line-height: 1.55;
    margin: 8px 0;
  }
  .badge-note {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.55;
    margin: 14px 0 0;
    max-width: 64ch;
  }
  .data p {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.55;
  }
  .data a {
    color: var(--chip-ink);
    font-weight: 600;
  }
  .foot {
    margin-top: 36px;
  }
</style>
