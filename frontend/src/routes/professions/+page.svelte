<script lang="ts">
  import { browser } from "$app/environment";
  import { replaceState } from "$app/navigation";
  import { page } from "$app/stores";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { CatalogItem } from "./+page";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  // Field → gradient. Gives the grid real variety (not an identical card wall).
  const FIELD: Record<string, string> = {
    tech: "linear-gradient(135deg,#4f9dff,#8b5cf6)",
    health: "linear-gradient(135deg,#ff5f8f,#ff9d6c)",
    arts: "linear-gradient(135deg,#8b5cf6,#ff5f8f)",
    education: "linear-gradient(135deg,#4f9dff,#43d6b5)",
    engineering: "linear-gradient(135deg,#6d6790,#4f9dff)",
    business: "linear-gradient(135deg,#ff9d6c,#ffd166)",
    media: "linear-gradient(135deg,#ff5f8f,#8b5cf6)",
    hospitality: "linear-gradient(135deg,#ff9d6c,#ff5f8f)",
    law: "linear-gradient(135deg,#4f9dff,#6d6790)",
  };
  const dot = (f: string | null) => FIELD[f ?? ""] ?? "linear-gradient(135deg,#8b5cf6,#4f9dff)";

  const FIELD_LABEL: Record<string, () => string> = {
    tech: m.field_tech, health: m.field_health, arts: m.field_arts, business: m.field_business,
    engineering: m.field_engineering, science: m.field_science, trades: m.field_trades,
    media: m.field_media, finance: m.field_finance, education: m.field_education, law: m.field_law,
    hospitality: m.field_hospitality, marketing: m.field_marketing, social: m.field_social,
    language: m.field_language, sports: m.field_sports,
  };
  const fieldLabel = (t: string) => FIELD_LABEL[t]?.() ?? t;

  const items = $derived(data.occupations as CatalogItem[]);

  // field chips: only tags actually present, most common first
  const fields = $derived.by(() => {
    const c = new Map<string, number>();
    for (const o of items) if (o.field_tag) c.set(o.field_tag, (c.get(o.field_tag) ?? 0) + 1);
    return [...c.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t);
  });

  // salary brackets depend on the country's currency and pay convention:
  // US = annual USD, ES = annual EUR (Spanish levels: group p75 tops out
  // around 80k, so bands sit far lower than the US ones), RU = monthly RUB.
  const currency = $derived(items.find((o) => o.currency)?.currency);
  const salBands = $derived(
    currency === "USD"
      ? [
          { key: "lo", label: "≤ $60k", lo: 0, hi: 60000 },
          { key: "mid", label: "$60–100k", lo: 60000, hi: 100000 },
          { key: "hi", label: "$100k+", lo: 100000, hi: Infinity },
        ]
      : currency === "EUR"
        ? [
            { key: "lo", label: "≤ 25k €", lo: 0, hi: 25000 },
            { key: "mid", label: "25–40k €", lo: 25000, hi: 40000 },
            { key: "hi", label: "40–60k €", lo: 40000, hi: 60000 },
            { key: "top", label: "60k+ €", lo: 60000, hi: Infinity },
          ]
        : [
            { key: "lo", label: "≤ 70k ₽", lo: 0, hi: 70000 },
            { key: "mid", label: "70–120k ₽", lo: 70000, hi: 120000 },
            { key: "hi", label: "120k+ ₽", lo: 120000, hi: Infinity },
          ],
  );

  // Filters live in the URL (?f=…&nouni=1&s=…&q=…): open a profession, hit
  // "back" — the browser restores the URL and the filters survive; filtered
  // views are also shareable. replaceState keeps typing out of history.
  const initial = $page.url.searchParams;
  let field = $state<string | null>(initial.get("f"));
  let noUni = $state(initial.get("nouni") === "1");
  let salBand = $state<string | null>(initial.get("s"));
  let q = $state(initial.get("q") ?? "");

  $effect(() => {
    const qs = new URLSearchParams();
    if (field) qs.set("f", field);
    if (noUni) qs.set("nouni", "1");
    if (salBand) qs.set("s", salBand);
    if (q.trim()) qs.set("q", q.trim());
    if (browser && qs.toString() !== $page.url.searchParams.toString()) {
      replaceState(qs.size ? `?${qs}` : $page.url.pathname, {});
    }
  });

  const NO_UNI = new Set(["short", "vocational"]);
  const midpoint = (o: CatalogItem) =>
    o.salary_low != null && o.salary_high != null ? (o.salary_low + o.salary_high) / 2 : null;

  const filtered = $derived.by(() => {
    const needle = q.trim().toLowerCase();
    const band = salBands.find((b) => b.key === salBand);
    return items.filter((o) => {
      if (field && o.field_tag !== field) return false;
      if (noUni && !NO_UNI.has(o.edu_duration_band ?? "")) return false;
      if (band) {
        const mp = midpoint(o);
        if (mp == null || mp < band.lo || mp >= band.hi) return false;
      }
      if (needle && !o.title.toLowerCase().includes(needle)) return false;
      return true;
    });
  });

  const active = $derived(field !== null || noUni || salBand !== null || q.trim() !== "");
  function clearAll() {
    field = null;
    noUni = false;
    salBand = null;
    q = "";
  }
</script>

<svelte:head>
  <title>{m.catalog_title()} — {m.app_name()}</title>
  <meta name="description" content={m.catalog_intro()} />
</svelte:head>

<section class="catalog">
  <header class="lede">
    <h1>{m.catalog_title()}</h1>
    <p class="intro">{m.catalog_intro()}</p>
  </header>

  <div class="filters">
    <input class="search" type="search" placeholder={m.catalog_search_ph()} bind:value={q} />
    <div class="chips">
      <button class="chip strong" class:on={noUni} onclick={() => (noUni = !noUni)}
        >{m.catalog_no_uni()}</button
      >
      {#each salBands as b (b.key)}
        <button class="chip" class:on={salBand === b.key}
          onclick={() => (salBand = salBand === b.key ? null : b.key)}>{b.label}</button
        >
      {/each}
    </div>
    <div class="chips">
      {#each fields as f (f)}
        <button class="chip" class:on={field === f}
          onclick={() => (field = field === f ? null : f)}>{fieldLabel(f)}</button
        >
      {/each}
    </div>
    <div class="meta">
      <span class="count">{m.catalog_count({ shown: filtered.length, total: items.length })}</span>
      {#if active}<button class="clear" onclick={clearAll}>{m.catalog_clear()}</button>{/if}
    </div>
  </div>

  {#if items.length === 0}
    <p class="empty">{m.catalog_empty()}</p>
  {:else if filtered.length === 0}
    <p class="empty">{m.catalog_none()}</p>
  {:else}
    <ul class="grid">
      {#each filtered as occ (occ.slug)}
        <li>
          <a href={localizeHref(`/professions/${occ.slug}`)}>
            <span class="dot" style="background:{dot(occ.field_tag)}"></span>
            <span class="name">{occ.title}</span>
            <span class="arrow" aria-hidden="true">→</span>
          </a>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .catalog {
    padding: clamp(32px, 6vw, 60px) 0 60px;
    width: 100%;
  }
  .lede {
    max-width: 54ch;
    margin-bottom: 24px;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(34px, 5.5vw, 56px);
    letter-spacing: -0.03em;
    margin: 0 0 14px;
  }
  .intro {
    font-size: 17px;
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
  }
  .filters {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 26px;
  }
  .search {
    font-family: inherit;
    font-size: 15px;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 11px 16px;
    max-width: 340px;
  }
  .search:focus {
    outline: none;
    border-color: var(--c3);
  }
  .chips {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  @media (max-width: 620px) {
    .chips {
      flex-wrap: nowrap;
      overflow-x: auto;
      padding-bottom: 4px;
      -webkit-overflow-scrolling: touch;
    }
  }
  .chip {
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 6px 13px;
    cursor: pointer;
    transition:
      color var(--dur) var(--ease),
      background var(--dur) var(--ease),
      border-color var(--dur) var(--ease);
  }
  .chip:hover {
    color: var(--ink);
    border-color: var(--c3);
  }
  .chip.on {
    color: var(--chip-ink, #fff);
    background: var(--c3);
    border-color: var(--c3);
  }
  .chip.strong {
    color: var(--ink);
  }
  .chip.strong.on {
    color: var(--chip-ink, #fff);
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-top: 2px;
  }
  .count {
    font-size: 13px;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .clear {
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    color: var(--c3);
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
  }
  .clear:hover {
    text-decoration: underline;
  }
  .grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 14px;
  }
  .grid a {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 20px 22px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    text-decoration: none;
    color: var(--ink);
    transition:
      transform var(--dur) var(--ease),
      box-shadow var(--dur) var(--ease);
  }
  .grid a:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow);
  }
  .dot {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    flex: 0 0 auto;
    box-shadow: var(--shadow-sm);
  }
  .name {
    font-weight: 700;
    font-size: 16px;
    flex: 1;
  }
  .arrow {
    color: var(--muted);
    opacity: 0;
    transform: translateX(-4px);
    transition:
      opacity var(--dur) var(--ease),
      transform var(--dur) var(--ease),
      color var(--dur) var(--ease);
  }
  .grid a:hover .arrow {
    opacity: 1;
    transform: translateX(0);
    color: var(--c3);
  }
  .empty {
    color: var(--muted);
  }
</style>
