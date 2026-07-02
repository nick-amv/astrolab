<script lang="ts">
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const r = $derived(data.result);

  const shortLabels = {
    R: m.riasec_r_short(),
    I: m.riasec_i_short(),
    A: m.riasec_a_short(),
    S: m.riasec_s_short(),
    E: m.riasec_e_short(),
    C: m.riasec_c_short(),
  };

  const valueLabels: Record<string, string> = {
    achievement: m.val_achievement(),
    autonomy: m.val_autonomy(),
    recognition: m.val_recognition(),
    relationships: m.val_relationships(),
    stability: m.val_stability(),
    conditions: m.val_conditions(),
  };
  const valuesSorted = $derived(
    Object.entries((r.profile.values ?? {}) as Record<string, number>).sort(
      (a, b) => b[1] - a[1],
    ),
  );

  const buckets = $derived(
    [
      { key: "core", title: m.result_core(), sub: m.result_core_sub(), items: r.buckets.core },
      { key: "near", title: m.result_near(), sub: m.result_near_sub(), items: r.buckets.near },
      {
        key: "dark",
        title: m.result_dark(),
        sub: m.result_dark_sub(),
        items: r.buckets.dark_horse,
      },
    ].filter((b) => b.items.length > 0),
  );

  let copied = $state(false);
  function share() {
    navigator.clipboard?.writeText(location.href).then(() => {
      copied = true;
      setTimeout(() => (copied = false), 2000);
    });
  }
</script>

<svelte:head><title>{m.result_title()} — {m.app_name()}</title></svelte:head>

<section class="result">
  <h1>{m.result_title()}</h1>

  <div class="profile">
    <div class="card radar-card">
      <div class="k">{m.result_profile()}</div>
      <RiasecRadar values={r.profile.riasec ?? {}} labels={shortLabels} size={280} />
    </div>
    <div class="card">
      <div class="k">{m.result_values()}</div>
      <div class="values">
        {#each valuesSorted as [axis, v] (axis)}
          <div class="vrow">
            <span class="vlbl">{valueLabels[axis] ?? axis}</span>
            <span class="vtrack"><span class="vfill" style="width:{Math.round(v * 100)}%"></span></span>
          </div>
        {/each}
      </div>
    </div>
  </div>

  {#if buckets.length === 0}
    <p class="empty">{m.result_empty()}</p>
  {:else}
    {#each buckets as b (b.key)}
      <section class="bucket">
        <div class="bhead">
          <h2>{b.title}</h2>
          <span class="bsub">{b.sub}</span>
        </div>
        <ul class="occ">
          {#each b.items as occ (occ.slug)}
            <li>
              <a href={localizeHref(`/professions/${occ.slug}`)}>
                <span>{occ.title}</span><span class="arrow" aria-hidden="true">→</span>
              </a>
            </li>
          {/each}
        </ul>
      </section>
    {/each}
  {/if}

  <p class="disclaimer">{m.result_disclaimer()}</p>
  <div class="actions">
    <button class="ghost" onclick={share}>{copied ? m.result_share_done() : m.result_share()}</button>
    <a class="ghost" href={localizeHref("/test")}>{m.result_retake()}</a>
  </div>
</section>

<style>
  .result {
    padding: clamp(28px, 5vw, 56px) 0 60px;
    width: 100%;
  }
  h1 {
    font-weight: 800;
    font-size: clamp(32px, 5vw, 52px);
    letter-spacing: -0.03em;
    margin: 0 0 28px;
  }
  .profile {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
    margin-bottom: 40px;
  }
  @media (min-width: 720px) {
    .profile {
      grid-template-columns: 1fr 1fr;
    }
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 24px;
  }
  .radar-card {
    display: flex;
    flex-direction: column;
  }
  .k {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 16px;
  }
  .values {
    display: flex;
    flex-direction: column;
    gap: 12px;
    justify-content: center;
    height: 100%;
  }
  .vrow {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .vlbl {
    flex: 0 0 40%;
    font-size: 14px;
    font-weight: 600;
  }
  .vtrack {
    flex: 1;
    height: 8px;
    background: var(--line);
    border-radius: 99px;
    overflow: hidden;
  }
  .vfill {
    display: block;
    height: 100%;
    background: var(--grad);
    border-radius: 99px;
  }
  .bucket {
    margin-bottom: 30px;
  }
  .bhead {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }
  .bhead h2 {
    font-weight: 800;
    font-size: 24px;
    letter-spacing: -0.02em;
    margin: 0;
  }
  .bsub {
    color: var(--muted);
    font-size: 14px;
  }
  .occ {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
  }
  .occ a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 18px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    text-decoration: none;
    color: var(--ink);
    font-weight: 700;
    transition:
      transform var(--dur) var(--ease),
      box-shadow var(--dur) var(--ease);
  }
  .occ a:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow);
  }
  .occ .arrow {
    color: var(--c3);
  }
  .disclaimer {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    max-width: 60ch;
    margin: 8px 0 24px;
  }
  .actions {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }
  .ghost {
    font-family: inherit;
    font-weight: 700;
    font-size: 15px;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 12px 22px;
    text-decoration: none;
    cursor: pointer;
    transition: border-color var(--dur) var(--ease);
  }
  .ghost:hover {
    border-color: var(--c3);
    color: var(--c3);
  }
</style>
