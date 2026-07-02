<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  // Field → gradient. Gives the grid real variety (not an identical card wall).
  const FIELD: Record<string, string> = {
    tech: "linear-gradient(135deg,#4f9dff,#8b5cf6)",
    health: "linear-gradient(135deg,#ff5f8f,#ff9d6c)",
    arts: "linear-gradient(135deg,#8b5cf6,#ff5f8f)",
    education: "linear-gradient(135deg,#4f9dff,#43d6b5)",
    engineering: "linear-gradient(135deg,#6d6790,#4f9dff)",
    business: "linear-gradient(135deg,#ff9d6c,#ffd166)",
    media: "linear-gradient(135deg,#ff5f8f,#8b5cf6)",
    hospitality: "linear-gradient(135deg,#ff9d6c,#ff5f8f)",
    law: "linear-gradient(135deg,#4f9dff,#6d6790)",
  };
  const dot = (f: string | null) => FIELD[f ?? ""] ?? "linear-gradient(135deg,#8b5cf6,#4f9dff)";
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
    <ul class="grid">
      {#each data.occupations as occ (occ.slug)}
        <li>
          <a href={localizeHref(`/professions/${occ.slug}`)}>
            <span class="dot" style="background:{dot(occ.field_tag)}"></span>
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
    padding: clamp(32px, 6vw, 60px) 0 60px;
    width: 100%;
  }
  .lede {
    max-width: 54ch;
    margin-bottom: 40px;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(34px, 5.5vw, 56px);
    letter-spacing: -0.03em;
    margin: 0 0 14px;
  }
  .intro {
    font-size: 17px;
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
  }
  .grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 14px;
  }
  .grid a {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 20px 22px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    text-decoration: none;
    color: var(--ink);
    transition:
      transform var(--dur) var(--ease),
      box-shadow var(--dur) var(--ease);
  }
  .grid a:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow);
  }
  .dot {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    flex: 0 0 auto;
    box-shadow: var(--shadow-sm);
  }
  .name {
    font-weight: 700;
    font-size: 16px;
    flex: 1;
  }
  .arrow {
    color: var(--muted);
    opacity: 0;
    transform: translateX(-4px);
    transition:
      opacity var(--dur) var(--ease),
      transform var(--dur) var(--ease),
      color var(--dur) var(--ease);
  }
  .grid a:hover .arrow {
    opacity: 1;
    transform: translateX(0);
    color: var(--c3);
  }
  .empty {
    color: var(--muted);
  }
</style>
