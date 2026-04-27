<script>
  // Small-multiples sparklines: one mini time-series per sale-flow direction.
  // Each panel has its own y-scale so trajectories with very different absolute
  // magnitudes stay readable and change-over-time is the focal point.
  export let flows = [];    // [{label, color, points:[{x,y}]}]
  export let progress = 1;
  export let width = 540;
  export let height = 360;

  const padX = 34;
  const padY = 24;

  $: cols = 2;
  $: rows = Math.ceil(flows.length / cols);
  $: panelW = width / cols;
  $: panelH = height / rows;

  function panelGeom(i) {
    const r = Math.floor(i / cols);
    const c = i % cols;
    return {
      x0: c * panelW,
      y0: r * panelH,
      innerX: c * panelW + padX,
      innerY: r * panelH + padY,
      innerW: panelW - padX - 14,
      innerH: panelH - padY - 28,
    };
  }

  function scaleX(pts, g) {
    const xs = pts.map(p => p.x);
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    return (x) => g.innerX + ((x - xMin) / (xMax - xMin || 1)) * g.innerW;
  }
  function scaleY(pts, g) {
    const ys = pts.map(p => p.y);
    const yMin = Math.min(0, ...ys);
    const yMax = Math.max(...ys) * 1.15 || 1;
    return (y) => g.innerY + g.innerH - ((y - yMin) / (yMax - yMin || 1)) * g.innerH;
  }
  function clipCount(pts, progress) {
    return Math.max(2, Math.ceil(pts.length * Math.max(0.001, progress)));
  }

  // Find leading edge (last visible point) per flow
  function leadingPoint(pts, progress) {
    const n = clipCount(pts, progress);
    return pts[Math.min(n - 1, pts.length - 1)];
  }
  function pathFor(pts, progress, xs, ys) {
    const n = clipCount(pts, progress);
    return pts.slice(0, n).map((p, i) => `${i === 0 ? 'M' : 'L'} ${xs(p.x)} ${ys(p.y)}`).join(' ');
  }

  function fmtPct(v) { return `${(v * 100).toFixed(1)}%`; }
</script>

<svg viewBox="0 0 {width} {height}" width={width} height={height} class="sparks">
  {#each flows as f, i}
    {@const pts = [...f.points].sort((a, b) => a.x - b.x)}
    {@const g = panelGeom(i)}
    {@const xs = scaleX(pts, g)}
    {@const ys = scaleY(pts, g)}
    {@const first = pts[0]}
    {@const last = pts[pts.length - 1]}
    {@const lead = leadingPoint(pts, progress)}
    {@const growthFirst = first.y}
    {@const growthLast = last.y}
    {@const mult = growthFirst > 0 ? growthLast / growthFirst : null}

    <!-- Panel border -->
    <rect
      x={g.x0 + 4} y={g.y0 + 4}
      width={panelW - 8} height={panelH - 8}
      fill="#fff" stroke="#eee" rx="6"
    />

    <!-- Panel title + baseline→latest readout -->
    <text x={g.x0 + padX - 2} y={g.y0 + 16}
      font-size="11" font-weight="700" fill={f.color} class="panel-title">
      {f.label}
    </text>
    <text x={g.x0 + panelW - 10} y={g.y0 + 16}
      font-size="10" text-anchor="end" fill="#888" class="panel-range">
      {fmtPct(growthFirst)} → {fmtPct(growthLast)}{#if mult != null} · {mult.toFixed(1)}×{/if}
    </text>

    <!-- y-axis min/max labels -->
    <text x={g.innerX - 4} y={g.innerY + 4}
      font-size="9" text-anchor="end" fill="#aaa">{fmtPct(Math.max(...pts.map(p => p.y)))}</text>
    <text x={g.innerX - 4} y={g.innerY + g.innerH + 3}
      font-size="9" text-anchor="end" fill="#aaa">0%</text>

    <!-- x-axis endpoints -->
    <text x={g.innerX} y={g.innerY + g.innerH + 16}
      font-size="9" fill="#aaa">{first.x}</text>
    <text x={g.innerX + g.innerW} y={g.innerY + g.innerH + 16}
      font-size="9" text-anchor="end" fill="#aaa">{last.x}</text>

    <!-- Baseline tick line -->
    <line
      x1={g.innerX} x2={g.innerX + g.innerW}
      y1={g.innerY + g.innerH} y2={g.innerY + g.innerH}
      stroke="#eee" stroke-width="1"
    />

    <!-- Area under the line for subtle fill -->
    <path
      d="{pathFor(pts, progress, xs, ys)} L {xs(lead.x)} {g.innerY + g.innerH} L {xs(first.x)} {g.innerY + g.innerH} Z"
      fill={f.color} opacity="0.12"
    />

    <!-- The line itself -->
    <path
      d={pathFor(pts, progress, xs, ys)}
      fill="none" stroke={f.color} stroke-width="2.2"
      stroke-linecap="round" stroke-linejoin="round"
    />

    <!-- Leading-edge dot -->
    <circle
      cx={xs(lead.x)} cy={ys(lead.y)}
      r="3.5" fill={f.color}
    />
  {/each}
</svg>

<style>
  .sparks {
    display: block;
    max-width: 100%;
  }
  text { font-family: 'Inter', system-ui, sans-serif; }
</style>
