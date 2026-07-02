<script lang="ts">
  import { m } from "$lib/paraglide/messages";
</script>

<svelte:head>
  <title>{m.app_name()} — {m.tagline()}</title>
  <meta name="description" content={m.intro()} />
</svelte:head>

<section class="hero">
  <p class="eyebrow">{m.coming_soon()}</p>
  <h1>{m.tagline()}</h1>
  <p class="intro">{m.intro()}</p>
</section>

<style>
  .hero {
    padding: 40px 0 60px;
  }
  .eyebrow {
    font-family: system-ui, sans-serif;
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 20px;
  }
  h1 {
    font-size: clamp(34px, 6vw, 60px);
    line-height: 1.05;
    font-weight: 500;
    margin: 0 0 24px;
    max-width: 14ch;
  }
  .intro {
    font-family: system-ui, sans-serif;
    font-size: 17px;
    line-height: 1.6;
    color: var(--muted);
    max-width: 52ch;
    margin: 0;
  }
</style>
