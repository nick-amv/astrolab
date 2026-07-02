<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
</script>

<svelte:head>
  <title>{m.catalog_title()} — {m.app_name()}</title>
  <meta name="description" content={m.catalog_intro()} />
</svelte:head>

<section class="catalog">
  <header>
    <p class="eyebrow">{m.catalog_eyebrow()}</p>
    <h1>{m.catalog_title()}</h1>
    <p class="intro">{m.catalog_intro()}</p>
  </header>

  {#if data.occupations.length === 0}
    <p class="empty">{m.catalog_empty()}</p>
  {:else}
    <ul class="grid">
      {#each data.occupations as occ (occ.slug)}
        <li>
          <a href={localizeHref(`/professions/${occ.slug}`)}>
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
    padding: 40px 0 60px;
    width: 100%;
  }
  .eyebrow {
    font-family: system-ui, sans-serif;
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 16px;
  }
  h1 {
    font-size: clamp(30px, 5vw, 48px);
    font-weight: 500;
    margin: 0 0 16px;
  }
  .intro {
    font-family: system-ui, sans-serif;
    color: var(--muted);
    max-width: 52ch;
    margin: 0 0 40px;
    line-height: 1.6;
  }
  .grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }
  .grid a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--panel);
    text-decoration: none;
    color: var(--ink);
    transition: border-color 0.15s ease;
  }
  .grid a:hover {
    border-color: var(--accent);
  }
  .name {
    font-size: 17px;
  }
  .arrow {
    color: var(--muted);
  }
  .empty {
    font-family: system-ui, sans-serif;
    color: var(--muted);
  }
</style>
