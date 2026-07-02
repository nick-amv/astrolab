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
  <header class="lede">
    <h1>{m.catalog_title()}</h1>
    <p class="intro">{m.catalog_intro()}</p>
  </header>

  {#if data.occupations.length === 0}
    <p class="empty">{m.catalog_empty()}</p>
  {:else}
    <ul class="index">
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
    padding: 32px 0 64px;
    width: 100%;
  }
  .lede {
    max-width: 54ch;
    margin-bottom: 44px;
  }
  h1 {
    font-size: clamp(32px, 5vw, 52px);
    font-weight: 500;
    letter-spacing: -0.02em;
    margin: 0 0 14px;
  }
  .intro {
    font-family: system-ui, sans-serif;
    font-size: 16px;
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
  }

  /* Editorial index, not a card wall: hairline rows, two columns on wide
     screens. Reads like the contents page of a serious guide. */
  .index {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: 1fr;
    column-gap: 48px;
    border-top: 1px solid var(--line);
  }
  @media (min-width: 700px) {
    .index {
      grid-template-columns: 1fr 1fr;
    }
  }
  .index li {
    border-bottom: 1px solid var(--line);
  }
  .index a {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    padding: 17px 4px 17px 0;
    text-decoration: none;
    color: var(--ink);
  }
  .name {
    font-size: 19px;
    transition: color var(--dur) var(--ease-out);
  }
  .arrow {
    font-family: system-ui, sans-serif;
    color: var(--muted);
    transform: translateX(-4px);
    opacity: 0;
    transition:
      transform var(--dur) var(--ease-out),
      opacity var(--dur) var(--ease-out),
      color var(--dur) var(--ease-out);
  }
  .index a:hover .name,
  .index a:focus-visible .name {
    color: var(--accent);
  }
  .index a:hover .arrow,
  .index a:focus-visible .arrow {
    transform: translateX(0);
    opacity: 1;
    color: var(--accent);
  }
  .empty {
    font-family: system-ui, sans-serif;
    color: var(--muted);
  }
</style>
