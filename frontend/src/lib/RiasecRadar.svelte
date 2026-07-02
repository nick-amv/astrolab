<script lang="ts">
  // Signature RIASEC visualization: a gradient-filled radar. The one saturated
  // color moment on the page (product register keeps the rest calm).
  let {
    values,
    labels,
    size = 300,
  }: {
    values: Record<string, number>;
    labels: Record<string, string>;
    size?: number;
  } = $props();

  const AXES = ["I", "A", "S", "E", "C", "R"]; // start at top, clockwise
  const cx = $derived(size / 2);
  const cy = $derived(size / 2);
  const R = $derived(size / 2 - 34);

  function pt(i: number, v: number): [number, number] {
    const a = -Math.PI / 2 + (i * Math.PI) / 3;
    return [cx + R * v * Math.cos(a), cy + R * v * Math.sin(a)];
  }

  const rings = $derived(
    [1, 0.75, 0.5, 0.25].map((f) =>
      AXES.map((_, i) => {
        const a = -Math.PI / 2 + (i * Math.PI) / 3;
        return `${(cx + R * f * Math.cos(a)).toFixed(1)} ${(cy + R * f * Math.sin(a)).toFixed(1)}`;
      }).join(" L "),
    ),
  );
  const spokes = $derived(AXES.map((_, i) => pt(i, 1)));
  const poly = $derived(AXES.map((k, i) => pt(i, values[k] ?? 0).map((n) => n.toFixed(1)).join(",")).join(" "));
  const nodes = $derived(AXES.map((k, i) => ({ p: pt(i, values[k] ?? 0), lbl: labels[k] ?? k, lp: pt(i, 1.16) })));
  const uid = $derived(Math.round(size));
</script>

<svg viewBox="0 0 {size} {size}" width="100%" style="max-width:{size}px;display:block;margin:0 auto" role="img" aria-label="RIASEC">
  <defs>
    <linearGradient id="rg{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="var(--c2)" />
      <stop offset="1" stop-color="var(--c3)" />
    </linearGradient>
  </defs>
  {#each rings as d (d)}
    <path d="M {d} Z" fill="none" stroke="var(--line-strong)" stroke-width="1" opacity="0.7" />
  {/each}
  {#each spokes as [x, y], i (i)}
    <line x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} stroke="var(--line-strong)" stroke-width="1" opacity="0.7" />
  {/each}
  <polygon class="fill" points={poly} fill="url(#rg{uid})" fill-opacity="0.28" stroke="url(#rg{uid})" stroke-width="2.4" stroke-linejoin="round" />
  {#each nodes as n (n.lbl)}
    <circle cx={n.p[0].toFixed(1)} cy={n.p[1].toFixed(1)} r="4" fill="var(--surface)" stroke="url(#rg{uid})" stroke-width="2" />
    <text x={n.lp[0].toFixed(1)} y={n.lp[1].toFixed(1)} fill="var(--muted)" font-family="Manrope Variable, sans-serif" font-weight="600" font-size="10.5" text-anchor="middle" dominant-baseline="middle">{n.lbl}</text>
  {/each}
</svg>

<style>
  .fill {
    animation: draw 1.1s var(--ease) both;
    transform-origin: center;
  }
  @keyframes draw {
    from {
      opacity: 0;
      transform: scale(0.85);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .fill {
      animation: none;
    }
  }
</style>
