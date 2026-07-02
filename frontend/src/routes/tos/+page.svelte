<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
</script>

<svelte:head>
  <title>{m.tos_title()} — {m.app_name()}</title>
</svelte:head>

<article class="doc">
  <h1>{m.tos_title()}</h1>
  <p>{m.tos_body()}</p>
  <a href={localizeHref("/")}>{m.back_home()}</a>
</article>

<style>
  .doc {
    padding: 40px 0;
    max-width: 60ch;
  }
  h1 {
    font-weight: 500;
    margin: 0 0 18px;
  }
  p {
    font-family: system-ui, sans-serif;
    line-height: 1.6;
    color: var(--muted);
  }
  a {
    font-family: system-ui, sans-serif;
    font-size: 14px;
    color: var(--accent);
    text-decoration: none;
  }
</style>
