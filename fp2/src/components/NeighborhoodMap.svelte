<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { dotColorScale, filterProperties } from '../lib/data.js';

  // ── Props ──────────────────────────────────────────────────────────────────
  export let geoData;         // GeoJSON FeatureCollection
  export let properties;      // raw property array
  export let maxRent;         // number – slider value
  export let excludeEvicted = false;  // hide properties with eviction history
  export let zoomFeature = null;      // GeoJSON feature to zoom into, or null
  export let zoomProgress = 0;        // 0 = full Boston, 1 = fully zoomed (scroll-driven)

  // ── Refs ───────────────────────────────────────────────────────────────────
  let svgEl;          // SVG element for neighborhood polygons + axes
  let canvasEl;       // Canvas overlay for property dots
  let containerEl;    // wrapping div for ResizeObserver

  // ── Dimensions ────────────────────────────────────────────────────────────
  let width = 0;
  let height = 0;
  let ready = false;

  // ── D3 objects ─────────────────────────────────────────────────────────────
  let projection;
  let pathGen;

  // ── Zoom state ───────────────────────────────────────────────────────────
  let baseScale, baseTranslate;
  let zoomedScale, zoomedTranslate;

  // ── Tooltip + selected neighborhood state ─────────────────────────────────
  let tooltip = { visible: false, x: 0, y: 0, feature: null };
  let selectedNeighborhood = null;  // pinned by click
  let hoveredName = null;

  // ── Affordable property sample ─────────────────────────────────────────────
  $: affordableProps = properties ? filterProperties(properties, maxRent, excludeEvicted) : [];

  // ── Neighborhood counts (for tooltip) ─────────────────────────────────────
  $: affordableByNeighborhood = (() => {
    const map = {};
    if (!projection) return map;
    for (const p of affordableProps) {
      const [x, y] = projection([p.lng, p.lat]);
      if (x < -10 || x > width + 10 || y < -10 || y > height + 10) continue;
      map[p.neighborhood] = (map[p.neighborhood] ?? 0) + 1;
    }
    return map;
  })();

  // ── Build base projection when dimensions or data change ──────────────────
  $: if (geoData && width > 0 && height > 0) {
    const padding = 20;
    projection = d3
      .geoMercator()
      .fitExtent(
        [[padding, padding], [width - padding, height - padding]],
        geoData
      );
    pathGen = d3.geoPath().projection(projection);
    baseScale = projection.scale();
    baseTranslate = projection.translate().slice();
    ready = true;
  }

  // ── Compute zoomed-in projection target ───────────────────────────────────
  $: if (ready && zoomFeature && width > 0 && height > 0) {
    const tempProj = d3.geoMercator()
      .fitExtent([[60, 60], [width - 60, height - 60]], zoomFeature);
    zoomedScale = tempProj.scale();
    zoomedTranslate = tempProj.translate().slice();
  }

  // ── Apply scroll-driven zoom by interpolating projection ──────────────────
  $: if (ready && baseScale != null && projection) {
    const t = (zoomFeature && zoomedScale != null) ? zoomProgress : 0;
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    const tgtScale = zoomedScale ?? baseScale;
    const tgtTranslate = zoomedTranslate ?? baseTranslate;

    const s = baseScale + (tgtScale - baseScale) * ease;
    const tx = baseTranslate[0] + (tgtTranslate[0] - baseTranslate[0]) * ease;
    const ty = baseTranslate[1] + (tgtTranslate[1] - baseTranslate[1]) * ease;

    projection.scale(s).translate([tx, ty]);
    pathGen = d3.geoPath().projection(projection);
    drawDots();
  }

  // ── Re-draw canvas whenever filter state changes ──────────────────────────
  $: if (canvasEl && projection && affordableProps && ready) {
    requestAnimationFrame(() => drawDots());
  }

  // ── ResizeObserver ─────────────────────────────────────────────────────────
  onMount(() => {
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      const w = Math.floor(entry.contentRect.width);
      const h = Math.floor(entry.contentRect.height);
      if (w > 0 && h > 0) {
        width = w;
        height = h;
      }
    });
    if (containerEl) ro.observe(containerEl);
    return () => ro.disconnect();
  });

  // ── Draw property dots onto canvas ────────────────────────────────────────
  function drawDots() {
    if (!canvasEl || !projection) return;
    const ctx = canvasEl.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const logicalW = width;
    const logicalH = height;

    const targetW = Math.round(logicalW * dpr);
    const targetH = Math.round(logicalH * dpr);
    if (canvasEl.width !== targetW || canvasEl.height !== targetH) {
      canvasEl.width = targetW;
      canvasEl.height = targetH;
    }

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, logicalW, logicalH);

    const baseRadius = 2.5 + zoomProgress * 1.5;

    // Aggregate overlapping properties at the same pixel location
    const grid = new Map();
    for (const p of affordableProps) {
      const [x, y] = projection([p.lng, p.lat]);
      if (x < -10 || x > width + 10 || y < -10 || y > height + 10) continue;
      const key = `${Math.round(x)},${Math.round(y)}`;
      const existing = grid.get(key);
      if (existing) {
        existing.count += 1;
        existing.totalRent += p.monthly_rent;
      } else {
        grid.set(key, { x, y, count: 1, totalRent: p.monthly_rent });
      }
    }

    ctx.globalAlpha = 0.75;
    for (const dot of grid.values()) {
      const avgRent = dot.totalRent / dot.count;
      const r = dot.count === 1 ? baseRadius : baseRadius + Math.min(Math.sqrt(dot.count) * 1.2, 10);
      ctx.fillStyle = dotColorScale(avgRent);
      ctx.beginPath();
      ctx.arc(dot.x, dot.y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1.0;
  }

  // ── Tooltip helpers ────────────────────────────────────────────────────────
  function handleMouseMove(event, feature) {
    hoveredName = feature.properties.name;
    const rect = svgEl.getBoundingClientRect();
    tooltip = {
      visible: true,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      feature,
    };
  }

  function handleMouseLeave() {
    hoveredName = null;
    tooltip = { ...tooltip, visible: false };
  }

  function handleClick(feature) {
    if (selectedNeighborhood?.properties.name === feature.properties.name) {
      selectedNeighborhood = null;
    } else {
      selectedNeighborhood = feature;
    }
  }

  // ── Close sidebar ──────────────────────────────────────────────────────────
  function closeDetail() {
    selectedNeighborhood = null;
  }
</script>

<!-- ── Container ──────────────────────────────────────────────────────────── -->
<div class="map-wrap" bind:this={containerEl}>

  {#if ready && projection && geoData}
    <!-- SVG: neighborhood polygons + legend -->
    <svg
      bind:this={svgEl}
      width={width}
      height={height}
      class="map-svg"
      aria-label="Boston neighborhood map"
    >
      <!-- Neighborhood polygons -->
      <g class="neighborhoods">
        {#each geoData.features as feature (feature.properties.name)}
          {@const isHovered = hoveredName === feature.properties.name}
          {@const isSelected = selectedNeighborhood?.properties.name === feature.properties.name}
          <path
            d={pathGen(feature)}
            fill="#e8e8e8"
            opacity={zoomFeature && zoomProgress > 0 && feature.properties.name !== zoomFeature.properties.name ? 1 - zoomProgress * 0.7 : 1}
            stroke={isSelected ? '#c0392b' : isHovered ? '#666' : '#bbb'}
            stroke-width={isSelected ? 2 : isHovered ? 1.5 : 0.8}
            class="neighborhood-path"
            class:hovered={isHovered}
            class:selected={isSelected}
            on:mousemove={(e) => handleMouseMove(e, feature)}
            on:mouseleave={handleMouseLeave}
            on:click={() => handleClick(feature)}
            role="button"
            tabindex="0"
            aria-label={feature.properties.name}
            on:keydown={(e) => e.key === 'Enter' && handleClick(feature)}
          />
        {/each}
      </g>

    </svg>

    <!-- Canvas overlay for property dots -->
    <canvas
      bind:this={canvasEl}
      class="dots-canvas"
      style="width:{width}px; height:{height}px;"
      aria-hidden="true"
    ></canvas>

    <!-- Labels above dots -->
    <svg
      width={width}
      height={height}
      class="labels-svg"
      pointer-events="none"
    >
      {#each geoData.features as feature}
        {@const centroid = pathGen.centroid(feature)}
        {#if centroid && !isNaN(centroid[0])}
          <text
            x={centroid[0]}
            y={centroid[1]}
            class="neighborhood-label"
            text-anchor="middle"
            dominant-baseline="middle"
          >
            {feature.properties.name}
          </text>
        {/if}
      {/each}
    </svg>
  {/if}

  <!-- Tooltip -->
  {#if tooltip.visible && tooltip.feature}
    {@const fp = tooltip.feature.properties}
    {@const affordableHere = affordableByNeighborhood[fp.name] ?? 0}
    <div
      class="tooltip"
      style="left:{Math.min(tooltip.x + 14, width - 220)}px; top:{Math.max(tooltip.y - 10, 4)}px;"
    >
      <div class="tooltip-name">{fp.name}</div>
      <div class="tooltip-row">
        <span class="tooltip-key">Affordable properties</span>
        <span class="tooltip-val accent">{affordableHere.toLocaleString()}</span>
      </div>
      <div class="tooltip-row">
        <span class="tooltip-key">Total sales</span>
        <span class="tooltip-val">{fp.count?.toLocaleString() ?? 'N/A'}</span>
      </div>
      <div class="tooltip-hint">Dots may overlap at shared addresses. Click to pin details.</div>
    </div>
  {/if}

  <!-- Detail sidebar (pinned on click) -->
  {#if selectedNeighborhood}
    {@const sp = selectedNeighborhood.properties}
    {@const affordableHere = affordableByNeighborhood[sp.name] ?? 0}
    <div class="detail-sidebar">
      <div class="detail-header">
        <h2>{sp.name}</h2>
        <button class="close-btn" on:click={closeDetail} aria-label="Close">&times;</button>
      </div>

      <div class="detail-section">
        <div class="detail-sectiontitle">Affordability at ${maxRent.toLocaleString()}/mo</div>
        <div class="detail-bigstat">
          <span class="bignum accent">{affordableHere.toLocaleString()}</span>
          <span class="bigdesc">of {sp.count?.toLocaleString() ?? '—'} properties shown</span>
        </div>
        <div class="detail-bigstat">
          <span class="bignum">{sp.count ? ((affordableHere / sp.count) * 100).toFixed(0) : '—'}%</span>
          <span class="bigdesc">of neighborhood total</span>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-sectiontitle">Rent Distribution</div>
        <div class="stat-row"><span>Median</span><span class="sv">${sp.median_rent?.toLocaleString()}/mo</span></div>
        <div class="stat-row"><span>Average</span><span class="sv">${sp.avg_rent?.toLocaleString()}/mo</span></div>
        <div class="stat-row"><span>Typical range (25–75%ile)</span><span class="sv">${sp.p25_rent?.toLocaleString()} – ${sp.p75_rent?.toLocaleString()}</span></div>
        <div class="stat-row"><span>Min – Max</span><span class="sv">${sp.min_rent?.toLocaleString()} – ${sp.max_rent?.toLocaleString()}</span></div>
      </div>

      <div class="detail-section">
        <div class="detail-sectiontitle">Housing & Demographics</div>
        <div class="stat-row">
          <span>Eviction filings (2020–23)</span>
          <span class="sv">{sp.total_evictions?.toLocaleString() ?? 'N/A'}</span>
        </div>
        <div class="stat-row">
          <span>Corporate ownership</span>
          <span class="sv">{sp.avg_corp_own_rate != null ? (sp.avg_corp_own_rate * 100).toFixed(1) + '%' : 'N/A'}</span>
        </div>
        <div class="stat-row">
          <span>Owner-occupied rate</span>
          <span class="sv">{sp.avg_own_occ_rate != null ? (sp.avg_own_occ_rate * 100).toFixed(1) + '%' : 'N/A'}</span>
        </div>
        <div class="stat-row">
          <span>Renter median HH income</span>
          <span class="sv">${sp.avg_renter_mhi?.toLocaleString() ?? 'N/A'}</span>
        </div>
        <div class="stat-row">
          <span>Total sales in dataset</span>
          <span class="sv">{sp.count?.toLocaleString()}</span>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  /* ── Layout ─────────────────────────────────────────────────────────────── */
  .map-wrap {
    position: relative;
    width: 100%;
    height: 100%;
    background: #f0f0f0;
    overflow: hidden;
  }

  .map-svg {
    position: absolute;
    top: 0;
    left: 0;
    display: block;
  }

  .dots-canvas {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
  }

  .labels-svg {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
  }

  /* ── Neighborhood paths ──────────────────────────────────────────────────── */
  .neighborhood-path {
    cursor: pointer;
    transition: stroke 0.1s, stroke-width 0.1s;
  }

  .neighborhood-path:focus {
    outline: none;
    stroke: #c0392b !important;
    stroke-width: 2 !important;
  }

  /* ── Labels ──────────────────────────────────────────────────────────────── */
  .neighborhood-label {
    font-size: 9px;
    font-family: 'Inter', system-ui, sans-serif;
    fill: #333;
    font-weight: 600;
    letter-spacing: 0.03em;
    pointer-events: none;
    user-select: none;
    paint-order: stroke fill;
    stroke: rgba(255, 255, 255, 0.8);
    stroke-width: 3px;
    stroke-linejoin: round;
  }

  /* ── Tooltip ─────────────────────────────────────────────────────────────── */
  .tooltip {
    position: absolute;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 10px 12px;
    pointer-events: none;
    z-index: 10;
    min-width: 180px;
    max-width: 220px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .tooltip-name {
    font-weight: 700;
    font-size: 0.88rem;
    color: #1a1a1a;
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid #eee;
  }

  .tooltip-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 3px;
  }

  .tooltip-key {
    font-size: 0.72rem;
    color: #888;
    white-space: nowrap;
  }

  .tooltip-val {
    font-size: 0.8rem;
    font-weight: 600;
    color: #333;
    white-space: nowrap;
  }

  .tooltip-val.accent {
    color: #c0392b;
  }

  .tooltip-hint {
    font-size: 0.65rem;
    color: #aaa;
    margin-top: 6px;
    text-align: right;
    font-style: italic;
  }

  /* ── Detail sidebar ──────────────────────────────────────────────────────── */
  .detail-sidebar {
    position: absolute;
    bottom: 12px;
    right: 12px;
    width: 280px;
    max-height: 50vh;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #ddd;
    border-radius: 8px;
    z-index: 20;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(4px);
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 14px 10px;
    border-bottom: 1px solid #eee;
    position: sticky;
    top: 0;
    background: rgba(255, 255, 255, 0.98);
    z-index: 1;
  }

  .detail-header h2 {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
  }

  .close-btn {
    background: none;
    border: none;
    color: #999;
    font-size: 1.2rem;
    cursor: pointer;
    line-height: 1;
    padding: 2px 4px;
    border-radius: 3px;
    transition: color 0.1s;
  }

  .close-btn:hover {
    color: #333;
  }

  .detail-section {
    padding: 12px 14px;
    border-bottom: 1px solid #eee;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .detail-sectiontitle {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-bottom: 4px;
  }

  .detail-bigstat {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .bignum {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1a1a1a;
    line-height: 1;
  }

  .bignum.accent {
    color: #c0392b;
  }

  .bigdesc {
    font-size: 0.75rem;
    color: #666;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    font-size: 0.75rem;
    color: #666;
  }

  .stat-row .sv {
    font-weight: 600;
    color: #333;
    white-space: nowrap;
  }
</style>
