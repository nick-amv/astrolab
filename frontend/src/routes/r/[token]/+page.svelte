<script lang="ts">
  import ResultView from "$lib/ResultView.svelte";
  import { m } from "$lib/paraglide/messages";
  import { localizeHref } from "$lib/paraglide/runtime";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
</script>

<svelte:head><title>{m.result_title()} — {m.app_name()}</title></svelte:head>

<section class="result">
  <h1>{m.result_title()}</h1>
  <ResultView result={data.result} />
  <a class="cta" href={localizeHref("/test")}>{m.home_cta()} →</a>
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
  .cta {
    display: inline-block;
    margin-top: 6px;
  }
</style>
