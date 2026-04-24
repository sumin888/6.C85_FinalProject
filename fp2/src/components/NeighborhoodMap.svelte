<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { makeDotColorScale, makeEvictionColorScale, filterEvictionDots } from '../lib/data.js';

  // ── Props ──────────────────────────────────────────────────────────────────
  export let geoData;         // GeoJSON FeatureCollection
  export let dots = [];       // eviction case array [{lat, lng, neighborhood, rent_at_filing, rent_now, case_type, corp_landlord, ...}]
  export let maxRent;         // number – slider value
  export let maxYear = 2024;
  export let useCurrentRent = false;  // use rent_now instead of rent_at_filing
  export let highlightInvestors = false;  // color corporate landlord dots differently
  export let highlightEvictions = false;  // not used (all dots are evictions now)
  export let dimOtherNeighborhoods = false;
  export let focusNeighborhood = null;
  export let zoomFeature = null;
  export let zoomProgress = 0;
  export let rightReservedPx = 0;  // width of any overlay panel on the right (e.g. deep-dive sidebar)
  export let darkColorMode = false;  // when true: solid dark green (individual) / dark red (corporate), no rent gradient
  export let externalPopup = false;  // when true: suppress internal popup and expose clicked dots via selectedDots binding
  export let selectedDots = [];      // bound out: list of eviction records under the last-clicked cluster
  export let userPanZoom = false;    // when true: allow user to pan/zoom the map with mouse/trackpad
  export let resetViewSignal = 0;    // bump this number from the parent to reset the user pan/zoom

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

  // ── User pan/zoom transform (applied on top of the auto projection) ─────
  let userK = 1, userTx = 0, userTy = 0;
  let zoomBehavior = null;
  let zoomAttached = false;

  // ── Tooltip + selected neighborhood state ─────────────────────────────────
  let tooltip = { visible: false, x: 0, y: 0, feature: null };
  export let selectedNeighborhood = null;  // pinned by click, bound from parent
  let hoveredName = null;

  // ── Filtered eviction dots ──────────────────────────────────────────────────
  $: filteredDots = dots ? filterEvictionDots(dots, maxRent, { useCurrentRent, maxYear }) : [];
  $: dotColorScale = makeDotColorScale(maxRent);
  $: corpColorScale = makeEvictionColorScale(maxRent); // red for corporate landlord

  // ── Neighborhood counts (for tooltip + parent binding) ─────────────────────
  export let affordableByNeighborhood = {};
  $: affordableByNeighborhood = (() => {
    const map = {};
    if (!projection) return map;
    for (const d of filteredDots) {
      const [x, y] = projection([d.lng, d.lat]);
      if (x < -10 || x > width + 10 || y < -10 || y > height + 10) continue;
      map[d.neighborhood] = (map[d.neighborhood] ?? 0) + 1;
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

  // ── Compute zoomed-in projection target (from zoomFeature or focusNeighborhood) ─
  $: effectiveZoomFeature = focusNeighborhood && geoData
    ? geoData.features.find(f => f.properties.name === focusNeighborhood)
    : zoomFeature;

  $: if (ready && effectiveZoomFeature && width > 0 && height > 0) {
    // Fit the zoomed feature into the visible area (excluding any reserved right-side panel)
    const rightPad = Math.max(60, rightReservedPx + 20);
    const tempProj = d3.geoMercator()
      .fitExtent([[60, 60], [width - rightPad, height - 60]], effectiveZoomFeature);
    zoomedScale = tempProj.scale();
    zoomedTranslate = tempProj.translate().slice();
  }

  // When focusNeighborhood is set, force full zoom
  $: if (focusNeighborhood && effectiveZoomFeature) {
    zoomProgress = 1;
  }

  // ── Apply scroll-driven zoom by interpolating projection ──────────────────
  $: if (ready && baseScale != null && projection) {
    const t = (effectiveZoomFeature && zoomedScale != null) ? zoomProgress : 0;
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    const tgtScale = zoomedScale ?? baseScale;
    const tgtTranslate = zoomedTranslate ?? baseTranslate;

    const autoS = baseScale + (tgtScale - baseScale) * ease;
    const autoTx = baseTranslate[0] + (tgtTranslate[0] - baseTranslate[0]) * ease;
    const autoTy = baseTranslate[1] + (tgtTranslate[1] - baseTranslate[1]) * ease;

    // Layer user pan/zoom on top of the auto projection
    const s = autoS * userK;
    const tx = userTx + userK * autoTx;
    const ty = userTy + userK * autoTy;

    projection.scale(s).translate([tx, ty]);
    pathGen = d3.geoPath().projection(projection);
    drawDots();
  }

  // ── Re-draw canvas whenever filter state changes ──────────────────────────
  $: if (canvasEl && projection && filteredDots && dotColorScale && corpColorScale && ready && (highlightInvestors || true)) {
    requestAnimationFrame(() => drawDots());
  }

  // ── Attach d3.zoom for user pan/zoom ──────────────────────────────────────
  $: if (canvasEl && userPanZoom && !zoomAttached) {
    zoomBehavior = d3.zoom()
      .scaleExtent([0.6, 18])
      .filter((event) => {
        // allow wheel, drag, touch — block right-click and double-click panning conflicts
        return !event.ctrlKey && event.button !== 2;
      })
      .on('zoom', (event) => {
        userK = event.transform.k;
        userTx = event.transform.x;
        userTy = event.transform.y;
      });
    d3.select(canvasEl).call(zoomBehavior);
    zoomAttached = true;
  }
  $: if (canvasEl && !userPanZoom && zoomAttached) {
    d3.select(canvasEl).on('.zoom', null);
    zoomAttached = false;
    userK = 1; userTx = 0; userTy = 0;
  }
  // Reset user transform when the signal changes
  let _lastResetSignal = 0;
  $: if (zoomAttached && zoomBehavior && resetViewSignal !== _lastResetSignal) {
    _lastResetSignal = resetViewSignal;
    d3.select(canvasEl)
      .transition().duration(450)
      .call(zoomBehavior.transform, d3.zoomIdentity);
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

  // ── Draw eviction dots onto canvas ─────────────────────────────────────────
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

    const baseRadius = 1.8 + zoomProgress * 1.1;
    const rentKey = useCurrentRent ? 'rent_now' : 'rent_at_filing';

    // Aggregate overlapping dots at same pixel
    const grid = new Map();
    for (const d of filteredDots) {
      const [x, y] = projection([d.lng, d.lat]);
      if (x < -10 || x > width + 10 || y < -10 || y > height + 10) continue;
      const key = `${Math.round(x)},${Math.round(y)}`;
      const rent = d[rentKey] ?? 0;
      const existing = grid.get(key);
      if (existing) {
        existing.count += 1;
        existing.totalRent += rent;
        existing.corpCount += d.corp_landlord ? 1 : 0;
      } else {
        grid.set(key, { x, y, count: 1, totalRent: rent, corpCount: d.corp_landlord ? 1 : 0 });
      }
    }

    ctx.globalAlpha = 0.75;
    for (const dot of grid.values()) {
      const avgRent = dot.totalRent / dot.count;
      const r = dot.count === 1 ? baseRadius : baseRadius + Math.min(Math.sqrt(dot.count) * 0.9, 8);

      // Color: corporate landlord = red, individual = green
      const corpRatio = dot.corpCount / dot.count;
      if (darkColorMode) {
        ctx.fillStyle = corpRatio > 0.5 ? '#c0392b' : '#2d8c2d';
      } else if (highlightInvestors && corpRatio > 0.5) {
        ctx.fillStyle = corpColorScale(avgRent);
      } else {
        ctx.fillStyle = dotColorScale(avgRent);
      }

      ctx.beginPath();
      ctx.arc(dot.x, dot.y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1.0;

    // Highlight the clicked dot: stroke directly on its circumference
    if (selectedDotLoc) {
      const [sx, sy] = projection([selectedDotLoc.lng, selectedDotLoc.lat]);
      if (sx >= -20 && sx <= width + 20 && sy >= -20 && sy <= height + 20) {
        const hitKey = `${Math.round(sx)},${Math.round(sy)}`;
        const cluster = grid.get(hitKey);
        const dotR = cluster
          ? (cluster.count === 1 ? baseRadius : baseRadius + Math.min(Math.sqrt(cluster.count) * 1.2, 10))
          : baseRadius;
        ctx.save();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#111';
        ctx.beginPath();
        ctx.arc(sx, sy, dotR, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
    }
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

  // ── Property popup (dot click) ──────────────────────────────────────────────
  let propertyPopup = { visible: false, x: 0, y: 0, props: [] };
  let selectedDotLoc = null; // {lat, lng} of the clicked cluster center

  function handleCanvasClick(event) {
    if (!projection || !filteredDots.length) return;
    const rect = canvasEl.getBoundingClientRect();
    const cx = event.clientX - rect.left;
    const cy = event.clientY - rect.top;
    const hitRadius = 12;

    // Find eviction cases near click
    const hits = [];
    for (const d of filteredDots) {
      const [px, py] = projection([d.lng, d.lat]);
      const dx = px - cx, dy = py - cy;
      if (dx * dx + dy * dy <= hitRadius * hitRadius) {
        hits.push(d);
      }
    }

    if (hits.length > 0) {
      selectedDotLoc = { lat: hits[0].lat, lng: hits[0].lng };
      if (externalPopup) {
        selectedDots = hits.slice(0, 5);
      } else {
        const popupW = 300;
        const popupH = Math.min(400, 120 + hits.length * 110);
        const rightBound = width - rightReservedPx - 8;
        let px = cx + 14;
        if (px + popupW > rightBound) px = cx - 14 - popupW;
        px = Math.max(8, Math.min(px, rightBound - popupW));
        let py = cy - 10;
        py = Math.max(8, Math.min(py, height - popupH - 8));
        propertyPopup = {
          visible: true,
          x: px,
          y: py,
          props: hits.slice(0, 5),
        };
      }
      drawDots();
    } else {
      propertyPopup = { ...propertyPopup, visible: false };
      if (externalPopup) selectedDots = [];
      if (selectedDotLoc) {
        selectedDotLoc = null;
        drawDots();
      }
    }
  }

  function closeDotPopup() {
    propertyPopup = { ...propertyPopup, visible: false };
    selectedDotLoc = null;
    drawDots();
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
          {@const isZoomTarget = effectiveZoomFeature?.properties.name === feature.properties.name}
          {@const zoomStroke = isZoomTarget && zoomProgress > 0}
          {@const isDimmed = dimOtherNeighborhoods && focusNeighborhood && feature.properties.name !== focusNeighborhood}
          <path
            d={pathGen(feature)}
            fill={isDimmed ? '#d8d8d8' : '#e8e8e8'}
            opacity={isDimmed ? 0.3 : (effectiveZoomFeature && zoomProgress > 0 && !isZoomTarget ? 1 - zoomProgress * 0.7 : 1)}
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

    <!-- Canvas overlay for property dots (clickable) -->
    <canvas
      bind:this={canvasEl}
      class="dots-canvas clickable"
      style="width:{width}px; height:{height}px;"
      on:click={handleCanvasClick}
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
      <div class="tooltip-hint">Click a dot for property details.</div>
    </div>
  {/if}

  <!-- Property popup (dot click) -->
  {#if propertyPopup.visible && propertyPopup.props.length > 0}
    <div class="property-popup" style="left:{propertyPopup.x}px; top:{propertyPopup.y}px;">
      <button class="popup-close" on:click={closeDotPopup}>&times;</button>
      {#each propertyPopup.props as p, idx}
        {#if idx > 0}<hr class="popup-divider" />{/if}
        <div class="popup-address">{p.address ?? 'Unknown Address'}{#if p.unit}, Unit {p.unit}{/if}</div>
        <div class="popup-grid">
          <div class="popup-row"><span class="pk">Case type</span><span class="pv">{p.case_type}</span></div>
          <div class="popup-row"><span class="pk">Filed</span><span class="pv">{p.file_date ?? '—'}</span></div>
          <div class="popup-row"><span class="pk">Status</span><span class="pv">{p.case_status ?? '—'}</span></div>
          {#if p.dispo}<div class="popup-row"><span class="pk">Outcome</span><span class="pv">{p.dispo}</span></div>{/if}
          <div class="popup-row"><span class="pk">Landlord</span><span class="pv" class:red={p.corp_landlord}>{p.corp_landlord ? 'Corporate' : 'Individual'}</span></div>
          {#if p.plaintiff}<div class="popup-row"><span class="pk">Filed by</span><span class="pv" style="font-size:0.65rem; white-space:normal;">{p.plaintiff.length > 50 ? p.plaintiff.slice(0, 50) + '...' : p.plaintiff}</span></div>{/if}
          {#if p.rent_at_filing || p.rent_now}
            {@const pctChange = p.rent_at_filing && p.rent_now
              ? Math.round((p.rent_now / p.rent_at_filing - 1) * 100)
              : null}
            <div class="rent-compare">
              <div class="rent-compare-col">
                <div class="rent-compare-label">At filing</div>
                <div class="rent-compare-val then">
                  {p.rent_at_filing ? `$${p.rent_at_filing.toLocaleString()}` : '—'}
                </div>
              </div>
              <div class="rent-compare-arrow">
                {#if pctChange != null}
                  <div class="rent-compare-pct" class:up={pctChange > 0} class:down={pctChange < 0}>
                    {pctChange > 0 ? '+' : ''}{pctChange}%
                  </div>
                {/if}
                <div class="rent-compare-line"></div>
              </div>
              <div class="rent-compare-col">
                <div class="rent-compare-label">Now</div>
                <div class="rent-compare-val now">
                  {p.rent_now ? `$${p.rent_now.toLocaleString()}` : '—'}
                </div>
              </div>
            </div>
          {/if}
          <div class="popup-row"><span class="pk">Neighborhood</span><span class="pv">{p.neighborhood}</span></div>
        </div>
      {/each}
      {#if propertyPopup.props.length > 1}
        <div class="popup-multi">{propertyPopup.props.length} eviction cases at this location</div>
      {/if}
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

  .dots-canvas.clickable {
    pointer-events: auto;
    cursor: crosshair;
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

  /* ── Property popup ──────────────────────────────────────────────────── */
  .property-popup {
    position: absolute;
    background: rgba(255,255,255,0.98);
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 12px 14px;
    pointer-events: auto;
    z-index: 20;
    min-width: 240px;
    max-width: 300px;
    max-height: 400px;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  }

  .popup-close {
    position: absolute;
    top: 6px;
    right: 8px;
    background: none;
    border: none;
    color: #999;
    font-size: 1.1rem;
    cursor: pointer;
    line-height: 1;
    padding: 2px 4px;
  }
  .popup-close:hover { color: #333; }

  .popup-address {
    font-weight: 700;
    font-size: 0.85rem;
    color: #1a1a1a;
    margin-bottom: 6px;
    padding-right: 20px;
  }

  .popup-grid {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .popup-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    font-size: 0.72rem;
  }

  .pk { color: #888; }
  .pv { font-weight: 600; color: #333; white-space: nowrap; }
  .pv.accent { color: #2d8c2d; }
  .pv.orange { color: #b35900; }
  .pv.red { color: #c0392b; }

  .popup-divider {
    border: none;
    border-top: 1px solid #eee;
    margin: 8px 0;
  }

  .rent-compare {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 8px;
    margin: 8px 0 4px;
    padding: 10px 10px;
    background: linear-gradient(135deg, #fff8ec 0%, #fdecec 100%);
    border: 1px solid #f0d9c8;
    border-radius: 6px;
  }
  .rent-compare-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    min-width: 0;
  }
  .rent-compare-label {
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8a7a6a;
    margin-bottom: 2px;
  }
  .rent-compare-val {
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }
  .rent-compare-val.then { color: #7a5c3a; }
  .rent-compare-val.now { color: #c0392b; }
  .rent-compare-arrow {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 52px;
  }
  .rent-compare-pct {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 999px;
    background: #fff;
    border: 1px solid #e0e0e0;
    color: #555;
    margin-bottom: 2px;
    font-variant-numeric: tabular-nums;
  }
  .rent-compare-pct.up {
    background: #fde8e6;
    border-color: #f2b3aa;
    color: #c0392b;
  }
  .rent-compare-pct.down {
    background: #e8f5e8;
    border-color: #9ec99e;
    color: #2d8c2d;
  }
  .rent-compare-line {
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, #e0c9b3 0%, #d98b7c 100%);
    border-radius: 1px;
    position: relative;
  }
  .rent-compare-line::after {
    content: '';
    position: absolute;
    right: -1px;
    top: 50%;
    transform: translateY(-50%);
    border-left: 6px solid #d98b7c;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
  }

  .popup-multi {
    font-size: 0.65rem;
    color: #999;
    text-align: center;
    margin-top: 8px;
    font-style: italic;
  }

</style>
