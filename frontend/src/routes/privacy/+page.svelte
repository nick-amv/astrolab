<script lang="ts">
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";

  const sections = [
    { t: m.privacy_s1_t(), d: m.privacy_s1_d() },
    { t: m.privacy_s2_t(), d: m.privacy_s2_d() },
    { t: m.privacy_s3_t(), d: m.privacy_s3_d() },
    { t: m.privacy_s4_t(), d: m.privacy_s4_d() },
    { t: m.privacy_s5_t(), d: m.privacy_s5_d() },
    { t: m.privacy_s6_t(), d: m.privacy_s6_d() },
    { t: m.privacy_s7_t(), d: m.privacy_s7_d() },
    { t: m.privacy_s8_t(), d: m.privacy_s8_d() },
  ];
</script>

<svelte:head><title>{m.privacy_title()} — {m.app_name()}</title></svelte:head>

<article class="doc">
  <h1>{m.privacy_title()}</h1>
  <p class="updated">{m.doc_updated()}</p>
  <p class="intro">{m.privacy_intro()}</p>

  {#each sections as s (s.t)}
    <section>
      <h2>{s.t}</h2>
      <p>{s.d}</p>
    </section>
  {/each}

  <section>
    <h2>{m.doc_contact_t()}</h2>
    <p>{m.privacy_contact_d()}</p>
  </section>

  <a class="back" href={localizeHref("/")}>← {m.back_home()}</a>
</article>

<style>
  .doc {
    padding: clamp(24px, 5vw, 44px) 0 64px;
    max-width: 68ch;
    margin: 0 auto;
  }
  h1 {
    font-size: clamp(28px, 5vw, 40px);
    letter-spacing: -0.02em;
    margin: 0 0 10px;
  }
  .updated {
    color: var(--muted);
    font-size: 13px;
    margin: 0 0 22px;
  }
  .intro {
    font-size: 17px;
    line-height: 1.6;
    margin: 0 0 8px;
  }
  section {
    margin: 26px 0;
  }
  h2 {
    font-size: 19px;
    letter-spacing: -0.01em;
    margin: 0 0 8px;
  }
  section p {
    color: var(--muted);
    font-size: 15.5px;
    line-height: 1.6;
    margin: 0;
  }
  .back {
    display: inline-block;
    margin-top: 20px;
    font-size: 14px;
    font-weight: 600;
    color: var(--chip-ink);
    text-decoration: none;
  }
  .back:hover {
    text-decoration: underline;
  }
</style>
