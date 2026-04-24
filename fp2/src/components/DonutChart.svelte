<script>
  // Simple donut chart for percentage breakdowns.
  // slices: [{ label, value, color }]
  export let slices = [];
  export let size = 160;
  export let thickness = 28;
  export let centerLabel = '';
  export let centerValue = '';

  $: total = slices.reduce((s, d) => s + (d.value || 0), 0);
  $: r = size / 2;
  $: inner = r - thickness;

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

  $: arcs = (() => {
    if (!total) return [];
    const out = [];
    let acc = -Math.PI / 2;
    for (const s of slices) {
      const frac = (s.value || 0) / total;
      const a1 = acc + frac * Math.PI * 2;
      out.push({ ...s, d: arcPath(r, r, r, inner, acc, a1), pct: frac * 100 });
      acc = a1;
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
    {#each arcs as a}
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
    gap: 14px;
    margin: 6px 0 4px;
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
    gap: 5px;
    font-size: 0.78rem;
    color: #444;
    flex: 1;
    min-width: 0;
  }
  .donut-legend li {
    display: grid;
    grid-template-columns: 12px 1fr auto;
    align-items: center;
    gap: 8px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(0,0,0,0.1);
  }
  .lab { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pct { font-weight: 700; color: #1a1a1a; font-variant-numeric: tabular-nums; }
</style>
