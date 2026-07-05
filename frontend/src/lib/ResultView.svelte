<script lang="ts">
  import { submitFeedback, type Result, type Verdict } from "$lib/api";
  import RiasecRadar from "$lib/RiasecRadar.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";

  // sid present = this is the owner's own result -> show the feedback chips.
  // Absent (public /r/<token> share view) -> read-only, no chips.
  let { result, sid }: { result: Result; sid?: string } = $props();

  const FB: { v: Verdict; label: () => string }[] = [
    { v: "fits", label: m.fb_fits },
    { v: "partial", label: m.fb_partial },
    { v: "not_me", label: m.fb_not_me },
  ];
  let verdicts = $state<Record<string, Verdict>>({});
  function rate(slug: string, v: Verdict) {
    if (!sid) return;
    verdicts[slug] = v; // optimistic; low-stakes, don't block on the network
    void submitFeedback(sid, slug, v);
  }

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
    Object.entries((result.profile.values ?? {}) as Record<string, number>).sort(
      (a, b) => b[1] - a[1],
    ),
  );
  const buckets = $derived(
    [
      { key: "core", title: m.result_core(), sub: m.result_core_sub(), items: result.buckets.core },
      { key: "near", title: m.result_near(), sub: m.result_near_sub(), items: result.buckets.near },
      {
        key: "dark",
        title: m.result_dark(),
        sub: m.result_dark_sub(),
        items: result.buckets.dark_horse,
      },
    ].filter((b) => b.items.length > 0),
  );
</script>

<div class="profile">
  <div class="card radar-card">
    <div class="k">{m.result_profile()}</div>
    <RiasecRadar values={result.profile.riasec ?? {}} labels={shortLabels} size={280} />
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
          <li class="occ-item">
            <a href={localizeHref(`/professions/${occ.slug}`)}>
              <div class="occ-top">
                <span class="occ-name">{occ.title}</span><span class="arrow" aria-hidden="true">→</span>
              </div>
              {#if occ.why}<p class="why">{occ.why}</p>{/if}
            </a>
            {#if sid}
              <div class="fb" role="group" aria-label={m.fb_prompt()}>
                <span class="fb-q">{m.fb_prompt()}</span>
                {#each FB as opt (opt.v)}
                  <button
                    type="button"
                    class="fb-chip"
                    class:on={verdicts[occ.slug] === opt.v}
                    aria-pressed={verdicts[occ.slug] === opt.v}
                    onclick={() => rate(occ.slug, opt.v)}>{opt.label()}</button
                  >
                {/each}
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    </section>
  {/each}
{/if}

<p class="disclaimer">{m.result_disclaimer()}</p>

<style>
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
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .occ-item {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 18px 20px;
    transition:
      border-color var(--dur) var(--ease),
      box-shadow var(--dur) var(--ease);
  }
  .occ-item:hover {
    border-color: var(--c3);
    box-shadow: var(--shadow);
  }
  .occ-item > a {
    display: block;
    text-decoration: none;
    color: var(--ink);
  }
  .fb {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
  }
  .fb-q {
    font-size: 12px;
    color: var(--muted);
    margin-right: 2px;
  }
  .fb-chip {
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 4px 10px;
    cursor: pointer;
    transition:
      color var(--dur) var(--ease),
      background var(--dur) var(--ease),
      border-color var(--dur) var(--ease);
  }
  .fb-chip:hover {
    color: var(--ink);
    border-color: var(--c3);
  }
  .fb-chip.on {
    color: var(--chip-ink, #fff);
    background: var(--c3);
    border-color: var(--c3);
  }
  .occ-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .occ-name {
    font-weight: 700;
    font-size: 16px;
  }
  .arrow {
    color: var(--c3);
  }
  .why {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.5;
    margin: 8px 0 0;
  }
  .disclaimer {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    max-width: 60ch;
    margin: 8px 0 24px;
  }
  .empty {
    color: var(--muted);
  }
</style>
