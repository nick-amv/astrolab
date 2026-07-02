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
  </footer>
</div>

<style>
  .section {
    color: var(--ink) !important;
  }
</style>
