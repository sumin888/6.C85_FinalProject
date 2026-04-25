<script>
  // Donut chart for percentage breakdowns.
  // slices: [{ label, value, color }]
  // progress: 0–1 — sweeps the donut from 0° to 360° as the value rises.
  export let slices = [];
  export let size = 160;
  export let thickness = 28;
  export let centerLabel = '';
  export let centerValue = '';
  export let progress = 1;

  $: total = slices.reduce((s, d) => s + (d.value || 0), 0);
  $: r = size / 2;
  $: inner = r - thickness;
  $: clampedProgress = Math.max(0, Math.min(1, progress));

  // Build arcs as <path> d-strings using native SVG
  function arcPath(cx, cy, rOut, rIn, a0, a1) {
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const x0 = cx + rOut * Math.cos(a0), y0 = cy + rOut * Math.sin(a0);
    const x1 = cx + rOut * Math.cos(a1), y1 = cy + rOut * Math.sin(a1);
    const x2 = cx + rIn * Math.cos(a1), y2 = cy + rIn * Math.sin(a1);
    const x3 = cx + rIn * Math.cos(a0), y3 = cy + rIn * Math.sin(a0);
    return `M ${x0} ${y0}
            A ${rOut} ${rOut} 0 ${large} 1 ${x1} ${y1}
            L ${x2} ${y2}
            A ${rIn} ${rIn} 0 ${large} 0 ${x3} ${y3}
            Z`;
  }

  // Build full-extent arcs (for legend percent display)
  $: fullArcs = (() => {
    if (!total) return [];
    const out = [];
    let acc = -Math.PI / 2;
    for (const s of slices) {
      const frac = (s.value || 0) / total;
      out.push({ ...s, startAng: acc, endAng: acc + frac * Math.PI * 2, pct: frac * 100 });
      acc = out[out.length - 1].endAng;
    }
    return out;
  })();

  // Visible arcs are clipped by progress: total sweep = progress * 2π from -π/2.
  $: arcs = (() => {
    if (!total || clampedProgress === 0) return [];
    const sweepLimit = -Math.PI / 2 + clampedProgress * Math.PI * 2;
    const out = [];
    for (const a of fullArcs) {
      if (a.startAng >= sweepLimit) break;
      const visEnd = Math.min(a.endAng, sweepLimit);
      out.push({ ...a, d: arcPath(r, r, r, inner, a.startAng, visEnd) });
    }
    return out;
  })();
</script>

<div class="donut-wrap">
  <svg width={size} height={size} viewBox="0 0 {size} {size}" class="donut">
    {#each arcs as a, i}
      <path d={a.d} fill={a.color} stroke="#fff" stroke-width="1.5" />
    {/each}
    {#if centerValue}
      <text x={r} y={r - 4} text-anchor="middle" class="center-value">{centerValue}</text>
    {/if}
    {#if centerLabel}
      <text x={r} y={r + 14} text-anchor="middle" class="center-label">{centerLabel}</text>
    {/if}
  </svg>

  <ul class="donut-legend">
    {#each fullArcs as a}
      <li>
        <span class="swatch" style="background:{a.color}"></span>
        <span class="lab">{a.label}</span>
        <span class="pct">{a.pct.toFixed(0)}%</span>
      </li>
    {/each}
  </ul>
</div>

<style>
  .donut-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 22px;
    margin: 6px 0 4px;
    width: 100%;
  }
  .donut { flex-shrink: 0; }
  .center-value {
    font-size: 22px;
    font-weight: 800;
    fill: #1a1a1a;
    font-variant-numeric: tabular-nums;
  }
  .center-label {
    font-size: 10px;
    fill: #777;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .donut-legend {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.8rem;
    color: #444;
    flex: 0 1 auto;
    min-width: 180px;
  }
  .donut-legend li {
    display: grid;
    grid-template-columns: 12px 1fr auto;
    align-items: start;
    gap: 8px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(0,0,0,0.1);
    margin-top: 3px;
  }
  .lab {
    white-space: normal;
    overflow: visible;
    line-height: 1.35;
    word-break: break-word;
  }
  .pct { font-weight: 700; color: #1a1a1a; font-variant-numeric: tabular-nums; }
</style>
