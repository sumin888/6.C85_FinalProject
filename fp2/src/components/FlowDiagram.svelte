<script>
  // Two-column ownership-flow diagram.
  // Left column = baseline year (e.g. 2004). Right column = latest year.
  // Both columns have two stacked nodes (Corporate on top, Individual on
  // bottom). Four ribbons connect each seller to each buyer.
  //
  // Ribbon shape: uniform width where it meets each node box (so every
  // flow "comes out of the box" at the same size), bulging thicker or
  // thinner in the middle based on how much that flow's share changed
  // between the two years.
  //
  // Animation: a left-to-right clip driven by the scroll `progress` prop
  // reveals each ribbon as if property were flowing from the baseline year
  // into the latest year.

  export let baseline = null;     // { ind_to_ind, ind_to_corp, corp_to_ind, corp_to_corp }
  export let latest = null;
  export let baselineYear = null;
  export let latestYear = null;
  export let progress = 1;        // 0–1

  const W = 600;
  const H = 420;
  const nodeW = 140;
  const nodeH = 48;
  const colLeft = 130;
  const colRight = W - 130;
  const yCorp = 92;
  const yInd = H - 140;

  const C_IND = '#2563eb';
  const C_CORP = '#e67e22';

  // Uniform ribbon width at the seller (left) box. Every flow exits the
  // seller box at this width.
  const SELLER_W = 28;
  // The buyer-side width is SELLER_W × (latest / baseline). Clamp so extreme
  // ratios stay on-canvas.
  function scaleBuyer(mult) {
    if (mult == null || !isFinite(mult)) return 1;
    return Math.max(0.08, Math.min(6, mult));
  }

  // Nudges so two ribbons leaving or arriving at the same node don't fully overlap.
  function nudge(side) { return side * 14; }

  // Tapered ribbon: anchors at (xL,yL) with uniform SELLER_W and at
  // (xR,yR) with wR (= SELLER_W × growth multiplier). The ribbon is a
  // smooth cubic-bezier band that narrows or widens between the two ends.
  function ribbonPath(xL, yL, xR, yR, wL, wR) {
    const hL = wL / 2;
    const hR = wR / 2;
    const cx1 = xL + (xR - xL) * 0.5;
    const cx2 = xL + (xR - xL) * 0.5;
    return [
      `M ${xL - hL} ${yL}`,
      `C ${cx1 - hL} ${yL}, ${cx2 - hR} ${yR}, ${xR - hR} ${yR}`,
      `L ${xR + hR} ${yR}`,
      `C ${cx2 + hR} ${yR}, ${cx1 + hL} ${yL}, ${xL + hL} ${yL}`,
      'Z',
    ].join(' ');
  }

  $: flows = [
    { key: 'corp_to_corp', sellerY: yCorp + nodeH, buyerY: yCorp,         color: C_CORP, sellerSide: -1, buyerSide: -1 },
    { key: 'corp_to_ind',  sellerY: yCorp + nodeH, buyerY: yInd,          color: C_IND,  sellerSide:  1, buyerSide: -1 },
    { key: 'ind_to_corp',  sellerY: yInd  + nodeH, buyerY: yCorp,         color: C_CORP, sellerSide: -1, buyerSide:  1 },
    { key: 'ind_to_ind',   sellerY: yInd  + nodeH, buyerY: yInd,          color: C_IND,  sellerSide:  1, buyerSide:  1 },
  ];

  $: rendered = flows.map(f => {
    const bVal = baseline?.[f.key] ?? 0;
    const nVal = latest?.[f.key] ?? 0;
    const mult = bVal > 0 ? nVal / bVal : null;
    const wL = SELLER_W;
    const wR = SELLER_W * scaleBuyer(mult);
    const xL = colLeft + nudge(f.sellerSide);
    const xR = colRight + nudge(f.buyerSide);
    return { ...f, bVal, nVal, mult, wL, wR, xL, xR };
  });

  // Clip-path reveal: a rect growing from the left column's edge to the
  // right column's edge, mapped 0→1 on progress.
  $: clipX = Math.max(0, Math.min(1, progress)) * W;
  $: clipId = `flow-clip-${Math.random().toString(36).slice(2, 9)}`;
</script>

<div class="flowdiag">
  <svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" class="flow-svg">

    <defs>
      <clipPath id={clipId}>
        <rect x="0" y="0" width={clipX} height={H} />
      </clipPath>
    </defs>

    <!-- Column headers -->
    <text x={colLeft} y="22" class="col-header">{baselineYear ?? '2004'}</text>
    <text x={colRight} y="22" class="col-header">{latestYear ?? '2024'}</text>

    <!-- Ribbons, masked by the left→right clip for the "flowing" animation -->
    <g clip-path="url(#{clipId})">
      {#each rendered as r}
        <path
          d={ribbonPath(r.xL, r.sellerY, r.xR, r.buyerY, r.wL, r.wR)}
          fill={r.color}
          opacity="0.55"
        />
      {/each}
    </g>

    <!-- Nodes: left column -->
    <g>
      <rect x={colLeft - nodeW / 2} y={yCorp} width={nodeW} height={nodeH}
        rx="8" fill="#fff" stroke={C_CORP} stroke-width="2" />
      <text x={colLeft} y={yCorp + nodeH / 2 + 4} class="node-lbl" style="fill:{C_CORP}">Corporate</text>

      <rect x={colLeft - nodeW / 2} y={yInd} width={nodeW} height={nodeH}
        rx="8" fill="#fff" stroke={C_IND} stroke-width="2" />
      <text x={colLeft} y={yInd + nodeH / 2 + 4} class="node-lbl" style="fill:{C_IND}">Individual</text>
    </g>

    <!-- Nodes: right column -->
    <g>
      <rect x={colRight - nodeW / 2} y={yCorp} width={nodeW} height={nodeH}
        rx="8" fill="#fff" stroke={C_CORP} stroke-width="2" />
      <text x={colRight} y={yCorp + nodeH / 2 + 4} class="node-lbl" style="fill:{C_CORP}">Corporate</text>

      <rect x={colRight - nodeW / 2} y={yInd} width={nodeW} height={nodeH}
        rx="8" fill="#fff" stroke={C_IND} stroke-width="2" />
      <text x={colRight} y={yInd + nodeH / 2 + 4} class="node-lbl" style="fill:{C_IND}">Individual</text>
    </g>
  </svg>
</div>

<style>
  .flowdiag {
    width: 100%;
    display: flex;
    justify-content: center;
  }
  .flow-svg {
    width: 100%;
    height: auto;
    max-width: 640px;
    display: block;
  }
  .col-header {
    font-size: 14px;
    font-weight: 800;
    fill: #1a1a1a;
    text-anchor: middle;
    letter-spacing: 0.02em;
  }
  .node-lbl {
    font-size: 13px;
    font-weight: 700;
    text-anchor: middle;
    pointer-events: none;
  }
</style>
