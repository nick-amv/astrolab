<script lang="ts">
  import { onMount } from "svelte";
  import { goto, invalidateAll } from "$app/navigation";
  import { page } from "$app/stores";
  import { claimSession, verifyMagicLink } from "$lib/api";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";

  let status = $state<"wait" | "ok" | "fail">("wait");

  onMount(async () => {
    const token = $page.url.searchParams.get("token");
    if (!token) {
      status = "fail";
      return;
    }
    const me = await verifyMagicLink(token);
    if (!me) {
      status = "fail";
      return;
    }
    // Attach a result the user started before signing in (same device).
    try {
      const pending = localStorage.getItem("astrolab_claim");
      if (pending) {
        await claimSession(pending);
        localStorage.removeItem("astrolab_claim");
      }
    } catch {
      /* ignore */
    }
    status = "ok";
    await invalidateAll(); // refresh the header's auth state
    await goto(localizeHref("/me"));
  });
</script>

<svelte:head><title>{m.verify_title()} — {m.app_name()}</title></svelte:head>

<section class="auth">
  {#if status === "wait"}
    <div class="spinner"></div>
    <p>{m.verify_wait()}</p>
  {:else if status === "ok"}
    <p>{m.verify_ok()}</p>
  {:else}
    <h1>{m.verify_title()}</h1>
    <p class="fail">{m.verify_fail()}</p>
    <a class="cta" href={localizeHref("/login")}>{m.verify_login_again()}</a>
  {/if}
</section>

<style>
  .auth {
    max-width: 440px;
    margin: 0 auto;
    padding: clamp(56px, 12vw, 110px) 0 60px;
    text-align: center;
  }
  h1 {
    font-size: clamp(26px, 5vw, 36px);
    letter-spacing: -0.02em;
    margin: 0 0 12px;
  }
  p {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.55;
  }
  .fail {
    margin-bottom: 22px;
  }
  .spinner {
    width: 40px;
    height: 40px;
    margin: 0 auto 18px;
    border-radius: 50%;
    border: 3px solid var(--line);
    border-top-color: var(--c3);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation-duration: 2s;
    }
  }
</style>
