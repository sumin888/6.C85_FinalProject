<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { makeDotColorScale, filterProperties } from '../lib/data.js';

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
  export let selectedNeighborhood = null;  // pinned by click, bound from parent
  let hoveredName = null;

  // ── Affordable property sample ─────────────────────────────────────────────
  $: affordableProps = properties ? filterProperties(properties, maxRent, excludeEvicted) : [];
  $: dotColorScale = makeDotColorScale(maxRent);

  // ── Neighborhood counts (for tooltip + parent binding) ─────────────────────
  export let affordableByNeighborhood = {};
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
  $: if (canvasEl && projection && affordableProps && dotColorScale && ready) {
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

  // ── Scale bar computation (derived from actual projection) ─────────────────
  // Project two real points a known lng offset apart, measure pixel distance
  // to get true meters-per-pixel at the current zoom level.
  const BOSTON_CENTER = [-71.0589, 42.3601];
  const LNG_OFFSET = 0.01; // ~0.01° longitude
  const niceDistances = [100, 200, 500, 1000, 2000, 5000, 10000];

  function haversineMeters([lon1, lat1], [lon2, lat2]) {
    const R = 6371000;
    const toRad = (d) => d * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  $: scaleBar = (() => {
    // depend on pathGen so this recomputes when zoom changes
    void pathGen;
    if (!projection) return null;
    const ptA = BOSTON_CENTER;
    const ptB = [BOSTON_CENTER[0] + LNG_OFFSET, BOSTON_CENTER[1]];
    const pxA = projection(ptA);
    const pxB = projection(ptB);
    if (!pxA || !pxB) return null;
    const pxDist = Math.sqrt((pxB[0] - pxA[0]) ** 2 + (pxB[1] - pxA[1]) ** 2);
    const realMeters = haversineMeters(ptA, ptB);
    const metersPerPx = realMeters / pxDist;

    const maxPx = 120;
    let dist = niceDistances[0];
    for (const d of niceDistances) {
      if (d / metersPerPx <= maxPx) dist = d;
    }
    const barPx = dist / metersPerPx;
    const label = dist >= 1000 ? `${dist / 1000} km` : `${dist} m`;
    return { barPx, label };
  })();
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
          {@const isZoomTarget = zoomFeature?.properties.name === feature.properties.name}
          {@const zoomStroke = isZoomTarget && zoomProgress > 0}
          <path
            d={pathGen(feature)}
            fill="#e8e8e8"
            opacity={zoomFeature && zoomProgress > 0 && !isZoomTarget ? 1 - zoomProgress * 0.7 : 1}
            stroke={zoomStroke ? '#2d8c2d' : isSelected ? '#2d8c2d' : isHovered ? '#666' : '#bbb'}
            stroke-width={zoomStroke ? 1.5 + zoomProgress * 1.5 : isSelected ? 2 : isHovered ? 1.5 : 0.8}
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

    <!-- Scale bar + North arrow (top layer) -->
    {#if scaleBar}
      {@const barY = height - 24}
      {@const barX = Math.round(width * 0.5 - scaleBar.barPx / 2)}
      {@const northX = barX + scaleBar.barPx + 20}
      <svg
        width={width}
        height={height}
        class="scale-bar-svg"
        pointer-events="none"
      >
        <g class="scale-bar-group">
          <line x1={barX} y1={barY} x2={barX + scaleBar.barPx} y2={barY}
                stroke="#333" stroke-width="2" />
          <line x1={barX} y1={barY - 5} x2={barX} y2={barY + 5}
                stroke="#333" stroke-width="1.5" />
          <line x1={barX + scaleBar.barPx} y1={barY - 5} x2={barX + scaleBar.barPx} y2={barY + 5}
                stroke="#333" stroke-width="1.5" />
          <text x={barX + scaleBar.barPx / 2} y={barY - 8}
                class="scale-label" text-anchor="middle">
            {scaleBar.label}
          </text>
          <g transform="translate({northX},{barY - 12})">
            <line x1="0" y1="10" x2="0" y2="-8" stroke="#333" stroke-width="1.5" />
            <polygon points="0,-12 -4,-6 4,-6" fill="#333" />
            <text x="0" y="20" class="north-label" text-anchor="middle">N</text>
          </g>
        </g>
      </svg>
    {/if}
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

  .scale-bar-svg {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    z-index: 5;
  }

  /* ── Neighborhood paths ──────────────────────────────────────────────────── */
  .neighborhood-path {
    cursor: pointer;
    transition: stroke 0.1s, stroke-width 0.1s;
  }

  .neighborhood-path:focus {
    outline: none;
    stroke: #2d8c2d !important;
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
    color: #2d8c2d;
  }

  /* ── Scale bar + North arrow ──────────────────────────────────────────────── */
  .scale-bar-group {
    pointer-events: none;
  }

  .scale-label {
    font-size: 10px;
    font-family: 'Inter', system-ui, sans-serif;
    fill: #333;
    font-weight: 600;
    paint-order: stroke fill;
    stroke: rgba(255, 255, 255, 0.85);
    stroke-width: 3px;
    stroke-linejoin: round;
  }

  .north-label {
    font-size: 10px;
    font-family: 'Inter', system-ui, sans-serif;
    fill: #333;
    font-weight: 700;
  }

  .tooltip-hint {
    font-size: 0.65rem;
    color: #aaa;
    margin-top: 6px;
    text-align: right;
    font-style: italic;
  }

</style>
