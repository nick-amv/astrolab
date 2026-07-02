<script lang="ts">
  import { m } from "$lib/paraglide/messages";

  // Toggles <html data-theme> and persists. Icon shown is CSS-driven off the
  // attribute, so there is no reactive state and no hydration mismatch.
  function toggle() {
    const cur = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (e) {
      void e;
    }
  }
</script>

<button class="theme-toggle" onclick={toggle} aria-label={m.theme_toggle()} type="button">
  <svg class="i-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z" />
  </svg>
  <svg class="i-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
</button>

<style>
  .theme-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 99px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--muted);
    cursor: pointer;
    transition:
      color var(--dur) var(--ease),
      border-color var(--dur) var(--ease),
      transform var(--dur) var(--ease);
  }
  .theme-toggle:hover {
    color: var(--ink);
    border-color: var(--line-strong);
  }
  .theme-toggle:active {
    transform: scale(0.94);
  }
  /* Light theme shows the moon (switch to dark); dark shows the sun. */
  .i-sun {
    display: none;
  }
  :global(:root[data-theme="dark"]) .i-moon {
    display: none;
  }
  :global(:root[data-theme="dark"]) .i-sun {
    display: block;
  }
</style>
