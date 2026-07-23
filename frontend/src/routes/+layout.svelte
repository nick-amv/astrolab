<script lang="ts">
  import ThemeToggle from "$lib/ThemeToggle.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref, deLocalizeHref, getLocale, locales } from "$lib/paraglide/runtime";
  import { afterNavigate } from "$app/navigation";
  import { page } from "$app/stores";
  import "./app.css";

  let { children, data } = $props();

  // Same page, other language: strip the locale prefix, then re-localize.
  const barePath = $derived(deLocalizeHref($page.url.pathname));
  const langLabel = (loc: string) =>
    loc === "ru" ? m.nav_ru() : loc === "es" ? m.nav_es() : loc === "fr" ? m.nav_fr() : loc === "de" ? m.nav_de() : m.nav_en();

  // Display order of the language switcher (RU sits between FR and DE, not first —
  // the RU audience reaches the site less directly). Falls back to any locale the
  // runtime adds that isn't listed here.
  const langOrder = $derived([
    ...(["en", "es", "fr", "ru", "de"] as const).filter((l) => (locales as readonly string[]).includes(l)),
    ...locales.filter((l) => !(["en", "es", "fr", "ru", "de"] as readonly string[]).includes(l)),
  ]);

  // Native language names (locale-independent) for the switcher dropdown.
  const LANG_NAMES: Record<string, string> = {
    en: "English", es: "Español", fr: "Français", ru: "Русский", de: "Deutsch", // cyrillic-ok: native language endonyms
  };

  // Close the <details> language dropdown when clicking outside it.
  function closeOnOutside(node: HTMLDetailsElement) {
    const handler = (e: MouseEvent) => {
      if (node.open && !node.contains(e.target as Node)) node.open = false;
    };
    document.addEventListener("click", handler, true);
    return { destroy: () => document.removeEventListener("click", handler, true) };
  }

  // GoatCounter: count.js records the initial page load; count client-side
  // route changes here so in-app navigation (test → result → professions)
  // is tracked too. Skip the initial "enter" to avoid double-counting.
  afterNavigate((nav) => {
    if (nav.type === "enter") return;
    const gc = (window as any).goatcounter;
    if (gc && typeof gc.count === "function") {
      gc.count({ path: location.pathname + location.search });
    }
  });
</script>

<svelte:head>
  <!-- Self-referential canonical (was missing site-wide): pairs with the hreflang
       set below so search/AI engines treat the 5 locale URLs as one page in 5
       languages instead of competing duplicates. -->
  <link rel="canonical" href={$page.url.origin + $page.url.pathname} />
  {#each locales as loc (loc)}
    <link rel="alternate" hreflang={loc} href={$page.url.origin + localizeHref(barePath, { locale: loc })} />
  {/each}
  <link rel="alternate" hreflang="x-default" href={$page.url.origin + localizeHref(barePath, { locale: "ru" })} />
</svelte:head>

<div class="aurora" aria-hidden="true"></div>

<div class="shell">
  <header>
    <a class="brand" href={localizeHref("/")}>
      <span class="mark"></span>{m.app_name()}
    </a>
    <nav>
      <a class="section" href={localizeHref("/method")}>{m.nav_method()}</a>
      <a class="section" href={localizeHref("/professions")}>{m.nav_catalog()}</a>
      <!-- Journal is served as static HTML at /blog/ (locale-aware client-side),
           outside the SvelteKit locale routing, so it's a plain href. -->
      <a class="section" href="/blog/" data-sveltekit-reload>{m.nav_journal()}</a>
      {#if data.user}
        <a class="section" href={localizeHref("/me")}>{m.nav_account()}</a>
      {:else}
        <a class="section" href={localizeHref("/login")}>{m.nav_login()}</a>
      {/if}
      <!-- translate="no": browser auto-translate must not mangle the language names -->
      <details class="lang-dd" use:closeOnOutside translate="no">
        <summary aria-label={m.nav_language()}>
          <svg class="globe" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="M2 12h20" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
          <span class="lc">{langLabel(getLocale())}</span>
          <svg class="chev" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </summary>
        <div class="lang-menu">
          {#each langOrder as loc (loc)}
            <a
              class:on={getLocale() === loc}
              href={localizeHref(barePath, { locale: loc })}
              hreflang={loc}
              aria-current={getLocale() === loc ? "true" : undefined}
              data-sveltekit-reload>{LANG_NAMES[loc] ?? loc.toUpperCase()}</a
            >
          {/each}
        </div>
      </details>
      <ThemeToggle />
    </nav>
  </header>

  <main>
    {@render children()}
  </main>

  <footer>
    <a href={localizeHref("/tos")}>{m.tos_link()}</a>
    <span aria-hidden="true">·</span>
    <a href={localizeHref("/privacy")}>{m.privacy_link()}</a>
    <span class="by">
      {m.footer_by()}
      <a href="https://nikam.dev" target="_blank" rel="noopener">nikam.dev</a>
    </span>
  </footer>
</div>

<style>
  .section {
    color: var(--ink) !important;
  }
  /* Language dropdown (native <details>, no JS). Same look shared with the blog. */
  .lang-dd {
    position: relative;
  }
  .lang-dd summary {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 6px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--muted);
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    cursor: pointer;
    list-style: none;
    user-select: none;
    transition: color 0.15s ease, background-color 0.15s ease;
  }
  .lang-dd summary::-webkit-details-marker {
    display: none;
  }
  .lang-dd summary:hover {
    color: var(--ink);
    background: var(--surface);
  }
  .lang-dd .chev {
    transition: transform 0.18s var(--ease);
  }
  .lang-dd[open] summary .chev {
    transform: rotate(180deg);
  }
  .lang-dd[open] summary {
    color: var(--ink);
  }
  .lang-menu {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    z-index: 20;
    min-width: 148px;
    display: flex;
    flex-direction: column;
    padding: 6px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    box-shadow: var(--shadow);
  }
  .lang-menu a {
    padding: 9px 12px;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--muted);
    text-decoration: none;
    border-radius: 10px;
    transition: color 0.15s ease, background-color 0.15s ease;
  }
  .lang-menu a:hover {
    color: var(--ink);
    background: color-mix(in oklab, var(--c3) 8%, var(--surface));
  }
  .lang-menu a.on {
    color: var(--ink);
    font-weight: 800;
  }
  .lang-menu a.on::before {
    content: "✓ ";
    color: var(--chip-ink);
  }
  @media (max-width: 620px) {
    .lang-menu a {
      padding: 11px 12px;
    }
  }
  .by {
    margin-left: auto;
    color: var(--muted);
  }
  .by a {
    color: var(--chip-ink);
    font-weight: 600;
    text-decoration: none;
  }
  .by a:hover {
    text-decoration: underline;
  }
  @media (max-width: 520px) {
    .by {
      margin-left: 0;
      flex-basis: 100%;
    }
  }
</style>
