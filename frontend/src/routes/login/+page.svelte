<script lang="ts">
  import { requestMagicLink } from "$lib/api";
  import { m } from "$lib/paraglide/messages";
  import { getLocale } from "$lib/paraglide/runtime";

  let email = $state("");
  let sent = $state(false);
  let busy = $state(false);
  const valid = $derived(/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim()));

  async function submit(e: Event) {
    e.preventDefault();
    if (!valid || busy) return;
    busy = true;
    await requestMagicLink(email.trim(), getLocale());
    busy = false;
    sent = true;
  }
</script>

<svelte:head><title>{m.login_title()} — {m.app_name()}</title></svelte:head>

<section class="auth">
  {#if sent}
    <div class="sent">
      <div class="mark" aria-hidden="true">✓</div>
      <h1>{m.login_sent_t()}</h1>
      <p>{m.login_sent_d()}</p>
    </div>
  {:else}
    <h1>{m.login_title()}</h1>
    <p class="intro">{m.login_intro()}</p>
    <form onsubmit={submit}>
      <input
        type="email"
        bind:value={email}
        placeholder={m.login_email_ph()}
        autocomplete="email"
        inputmode="email"
      />
      <button class="cta" type="submit" disabled={!valid || busy}>
        {busy ? m.login_sending() : m.login_submit()}
      </button>
    </form>
    <p class="note">{m.login_note()}</p>
  {/if}
</section>

<style>
  .auth {
    max-width: 440px;
    margin: 0 auto;
    padding: clamp(36px, 8vw, 72px) 0 60px;
  }
  h1 {
    font-size: clamp(28px, 5vw, 40px);
    letter-spacing: -0.02em;
    margin: 0 0 12px;
  }
  .intro {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.5;
    margin: 0 0 24px;
  }
  form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  input {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    padding: 15px 18px;
    font-family: inherit;
    font-size: 16px;
    color: var(--ink);
    transition: border-color var(--dur) var(--ease);
  }
  input:focus {
    outline: none;
    border-color: var(--c3);
  }
  .note {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
    margin: 16px 2px 0;
  }
  .sent {
    text-align: center;
    padding: 20px 0;
  }
  .sent .mark {
    width: 56px;
    height: 56px;
    margin: 0 auto 18px;
    border-radius: 50%;
    background: var(--grad);
    box-shadow: var(--shadow-c2);
    color: #fff;
    font-size: 26px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .sent p {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.55;
    max-width: 34ch;
    margin: 10px auto 0;
  }
</style>
