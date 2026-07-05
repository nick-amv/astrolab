<script lang="ts">
  import { goto, invalidateAll } from "$app/navigation";
  import { page } from "$app/stores";
  import { deleteAccount, logout, togglePlanStep, type PlanGroup } from "$lib/api";
  import { m } from "$lib/paraglide/messages";
  import { getLocale, localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
  const email = $derived(($page.data.user?.email as string | undefined) ?? "");
  let busy = $state(false);

  // N4: saved 'try it this week' plans, checkboxes toggle done (optimistic).
  let plans = $state<PlanGroup[]>(data.plans ?? []);
  async function toggle(g: PlanGroup, idx: number) {
    const step = g.steps.find((s) => s.idx === idx);
    if (!step) return;
    step.done = !step.done;
    const res = await togglePlanStep(g.slug, idx, g.audience);
    if (res !== null) step.done = res;
  }

  function fmt(iso: string | null): string {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString(getLocale(), {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return "";
    }
  }

  async function doLogout() {
    if (busy) return;
    busy = true;
    await logout();
    await invalidateAll();
    await goto(localizeHref("/"));
  }

  async function doDelete() {
    if (busy) return;
    if (!window.confirm(m.me_delete_confirm())) return;
    busy = true;
    await deleteAccount();
    await invalidateAll();
    await goto(localizeHref("/"));
  }
</script>

<svelte:head><title>{m.me_title()} — {m.app_name()}</title></svelte:head>

<section class="me">
  <header class="head">
    <div>
      <h1>{m.me_title()}</h1>
      {#if email}<p class="email">{email}</p>{/if}
    </div>
    <button class="ghost" onclick={doLogout} disabled={busy}>{m.me_logout()}</button>
  </header>

  {#if data.results.length === 0}
    <div class="empty">
      <p>{m.me_empty()}</p>
      <a class="cta" href={localizeHref("/test")}>{m.me_take_test()} →</a>
    </div>
  {:else}
    <ul class="list">
      {#each data.results as r (r.session_id)}
        <li>
          <a href={localizeHref(`/result/${r.session_id}`)}>
            <span class="top">{r.top.length ? r.top.join(" · ") : m.result_title()}</span>
            <span class="date">{fmt(r.finished_at)}</span>
          </a>
        </li>
      {/each}
    </ul>
  {/if}

  {#if plans.length}
    <section class="plan">
      <h2>{m.me_plan_title()}</h2>
      {#each plans as g (g.slug)}
        <div class="plan-group">
          <a class="plan-occ" href={localizeHref(`/professions/${g.slug}`)}>{g.title}</a>
          <ul>
            {#each g.steps as st (st.idx)}
              <li>
                <label>
                  <input type="checkbox" checked={st.done} onchange={() => toggle(g, st.idx)} />
                  <span class:done={st.done}>{st.text}</span>
                </label>
                {#if st.url}
                  <a
                    class="plan-link"
                    href={st.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={st.text}>↗</a
                  >
                {/if}
              </li>
            {/each}
          </ul>
        </div>
      {/each}
    </section>
  {/if}

  <button class="danger" onclick={doDelete} disabled={busy}>{m.me_delete()}</button>
</section>

<style>
  .me {
    max-width: 620px;
    margin: 0 auto;
    padding: clamp(28px, 5vw, 52px) 0 60px;
  }
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 28px;
  }
  h1 {
    font-size: clamp(28px, 5vw, 40px);
    letter-spacing: -0.02em;
    margin: 0;
  }
  .email {
    color: var(--muted);
    font-size: 14px;
    margin: 6px 0 0;
  }
  .empty {
    text-align: center;
    padding: 32px 0;
  }
  .empty p {
    color: var(--muted);
    font-size: 16px;
    margin: 0 0 20px;
  }
  .list {
    list-style: none;
    margin: 0 0 32px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .list a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 16px 20px;
    text-decoration: none;
    transition:
      transform var(--dur) var(--ease),
      border-color var(--dur) var(--ease);
  }
  .list a:hover {
    transform: translateY(-2px);
    border-color: var(--c3);
  }
  .top {
    font-weight: 700;
    font-size: 16px;
    color: var(--ink);
  }
  .date {
    color: var(--muted);
    font-size: 13px;
    flex: none;
  }
  .ghost {
    font-family: inherit;
    font-weight: 700;
    font-size: 14px;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 10px 18px;
    cursor: pointer;
    flex: none;
  }
  .ghost:hover {
    border-color: var(--c3);
    color: var(--c3);
  }
  .plan {
    margin: 0 0 32px;
  }
  .plan h2 {
    font-size: 20px;
    letter-spacing: -0.01em;
    margin: 0 0 16px;
  }
  .plan-group {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r);
    box-shadow: var(--shadow-sm);
    padding: 16px 20px;
    margin-bottom: 12px;
  }
  .plan-occ {
    font-weight: 700;
    font-size: 15px;
    color: var(--ink);
    text-decoration: none;
  }
  .plan-occ:hover {
    color: var(--c3);
  }
  .plan-group ul {
    list-style: none;
    margin: 12px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .plan-group li {
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }
  .plan-group label {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 14px;
    line-height: 1.5;
    color: var(--muted);
    cursor: pointer;
  }
  .plan-group input {
    accent-color: var(--c3);
    width: 16px;
    height: 16px;
    margin-top: 2px;
    flex: none;
  }
  .plan-group .done {
    text-decoration: line-through;
    opacity: 0.7;
  }
  .plan-link {
    flex: none;
    color: var(--c3);
    font-weight: 700;
    text-decoration: none;
  }
  .danger {
    font-family: inherit;
    font-weight: 600;
    font-size: 13px;
    color: var(--muted);
    background: none;
    border: none;
    cursor: pointer;
    text-decoration: underline;
    padding: 4px;
  }
  .danger:hover {
    color: #cc3a66;
  }
  .ghost:disabled,
  .danger:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
