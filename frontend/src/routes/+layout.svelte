<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";
  import "./app.css";

  let { children } = $props();
  const locale = getLocale();
</script>

<div class="shell">
  <header>
    <a class="brand" href={localizeHref("/")}>{m.app_name()}</a>
    <nav>
      <a class="section" href={localizeHref("/professions")}>{m.nav_catalog()}</a>
      <span class="sep" aria-hidden="true">·</span>
      <a class:active={locale === "ru"} href={localizeHref("/", { locale: "ru" })}>{m.nav_ru()}</a>
      <a class:active={locale === "en"} href={localizeHref("/", { locale: "en" })}>{m.nav_en()}</a>
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
