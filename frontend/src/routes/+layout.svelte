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
    loc === "ru" ? m.nav_ru() : loc === "es" ? m.nav_es() : m.nav_en();

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
      {#if data.user}
        <a class="section" href={localizeHref("/me")}>{m.nav_account()}</a>
      {:else}
        <a class="section" href={localizeHref("/login")}>{m.nav_login()}</a>
      {/if}
      <span class="lang" aria-label="Language">
        {#each locales as loc (loc)}
          <a
            class="lang-opt"
            class:on={getLocale() === loc}
            href={localizeHref(barePath, { locale: loc })}
            hreflang={loc}
            aria-current={getLocale() === loc ? "true" : undefined}
            data-sveltekit-reload>{langLabel(loc)}</a
          >
        {/each}
      </span>
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
  .lang {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 2px;
    border: 1px solid var(--hair, rgba(0, 0, 0, 0.12));
    border-radius: 999px;
  }
  .lang-opt {
    display: inline-flex;
    align-items: center;
    padding: 2px 9px;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0.02em;
    color: var(--muted);
    border-radius: 999px;
    text-decoration: none;
    transition: color 0.15s ease, background-color 0.15s ease;
  }
  .lang-opt:hover {
    color: var(--ink);
  }
  .lang-opt.on {
    color: var(--chip-ink, #fff);
    background: var(--accent, #ff5f8f);
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
