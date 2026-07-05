<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const v = $derived(data.view);
  const axisNames = $derived(v.axes.map((a) => a.label).join(" · "));
</script>

<svelte:head>
  <title>{m.parent_title()} — {m.app_name()}</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<article class="parent">
  <header class="head">
    <span class="eyebrow">{m.app_name()}</span>
    <h1>{m.parent_title()}</h1>
    <p class="intro">{m.parent_intro()}</p>
  </header>

  <section class="block">
    <h2>{m.parent_axes_h()}</h2>
    <p class="axes">{axisNames}</p>
    <ul class="strengths">
      {#each v.strengths as s (s)}
        <li>{s}</li>
      {/each}
    </ul>
  </section>

  <section class="block support">
    <h2>{m.parent_support_h()}</h2>
    <ol>
      {#each v.support as tip (tip)}
        <li>{tip}</li>
      {/each}
    </ol>
  </section>

  {#if v.professions.length}
    <section class="block">
      <h2>{m.parent_prof_h()}</h2>
      <div class="profs">
        {#each v.professions as p (p.slug)}
          <div class="prof">
            <span class="prof-name">{p.title}</span>
            {#if p.why}<p class="prof-why">{p.why}</p>{/if}
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <p class="foot">{m.parent_footer()}</p>
  <a class="cta" href={localizeHref("/")}>{m.app_name()} →</a>
</article>

<style>
  .parent {
    max-width: 680px;
    margin: 0 auto;
    padding: clamp(28px, 5vw, 56px) 0 60px;
  }
  .head {
    margin-bottom: 36px;
  }
  .eyebrow {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--c3);
  }
  h1 {
    font-weight: 800;
    font-size: clamp(28px, 4.6vw, 44px);
    letter-spacing: -0.03em;
    margin: 10px 0 14px;
  }
  .intro {
    font-size: 17px;
    line-height: 1.6;
    color: var(--ink);
    max-width: 56ch;
    margin: 0;
  }
  .block {
    margin-bottom: 34px;
  }
  .block h2 {
    font-weight: 800;
    font-size: 20px;
    letter-spacing: -0.01em;
    margin: 0 0 14px;
  }
  .axes {
    font-weight: 700;
    font-size: 16px;
    color: var(--c3);
    margin: 0 0 14px;
  }
  .strengths {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .strengths li {
    position: relative;
    padding-left: 26px;
    font-size: 16px;
    line-height: 1.55;
    color: var(--ink);
  }
  .strengths li::before {
    content: "✦";
    position: absolute;
    left: 0;
    color: var(--c3);
  }
  .support {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 24px 26px;
  }
  .support ol {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .support li {
    font-size: 16px;
    line-height: 1.6;
    color: var(--ink);
    padding-left: 4px;
  }
  .support li::marker {
    color: var(--c3);
    font-weight: 700;
  }
  .profs {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .prof {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 18px 20px;
  }
  .prof-name {
    font-weight: 700;
    font-size: 16px;
  }
  .prof-why {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.55;
    margin: 8px 0 0;
  }
  .foot {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    max-width: 60ch;
    margin: 8px 0 24px;
  }
  .cta {
    display: inline-block;
  }
</style>
