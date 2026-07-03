<script lang="ts">
  import ThemeToggle from "$lib/ThemeToggle.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import "./app.css";

  let { children } = $props();
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
