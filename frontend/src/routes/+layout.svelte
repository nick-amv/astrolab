<script lang="ts">
  import ThemeToggle from "$lib/ThemeToggle.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import { afterNavigate } from "$app/navigation";
  import "./app.css";

  let { children, data } = $props();

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
