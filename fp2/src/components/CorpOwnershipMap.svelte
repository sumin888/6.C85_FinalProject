<script>
  import * as d3 from 'd3';

  export let geoData;             // neighborhoods.geojson
  export let properties = [];     // sale records with lat/lng
  export let corpRates = [];      // [{year, rate}] from storyData.citywide.corp_ownership
  export let progress = 0;        // 0..1 — drives the year and dot count
  export let width = 380;
  export let height = 320;

  // Deterministic shuffle so dots accumulate in a stable order frame-to-frame.
  function mulberry32(seed) {
    return () => {
      seed = (seed + 0x6D2B79F5) | 0;
      let t = seed;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function seededShuffle(arr, seed) {
    const rng = mulberry32(seed);
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  const TOTAL_DOTS = 900;
  $: dotPool = (() => {
    if (!properties?.length) return [];
    const valid = properties.filter(p => p.lat != null && p.lng != null);
    const shuffled = seededShuffle(valid, 1337);
    return shuffled.slice(0, Math.min(TOTAL_DOTS, shuffled.length));
  })();

  $: projection = geoData?.features?.length
    ? d3.geoMercator().fitSize([width, height], geoData)
    : null;
  $: pathGen = projection ? d3.geoPath().projection(projection) : null;
  $: outlinePaths = (pathGen && geoData?.features)
    ? geoData.features.map(f => pathGen(f)).filter(Boolean)
    : [];

  $: yearMin = corpRates.length ? corpRates[0].year : 2004;
  $: yearMax = corpRates.length ? corpRates[corpRates.length - 1].year : 2024;
  $: yearF = yearMin + Math.max(0, Math.min(1, progress)) * (yearMax - yearMin);
  $: displayYear = Math.round(yearF);

  $: currentRate = (() => {
    if (!corpRates.length) return 0;
    const yLow = Math.floor(yearF);
    const yHigh = Math.min(yearMax, yLow + 1);
    const low = corpRates.find(r => r.year === yLow)?.rate;
    const high = corpRates.find(r => r.year === yHigh)?.rate;
    if (low == null) return high ?? 0;
    if (high == null) return low;
    const t = yearF - yLow;
    return low + t * (high - low);
  })();

  // Scale dot count to keep a sensible visual range across the rate span.
  $: visibleCount = Math.round(currentRate * dotPool.length / Math.max(0.0001, corpRates[corpRates.length - 1]?.rate ?? 1) * 0.85);
  $: visibleDots = dotPool.slice(0, Math.min(visibleCount, dotPool.length));

  $: dotProjections = (() => {
    if (!projection) return [];
    return visibleDots.map(p => projection([p.lng, p.lat])).filter(xy => xy && !Number.isNaN(xy[0]));
  })();
</script>

<div class="corp-map" style="width:{width}px">
  <svg viewBox="0 0 {width} {height}" {width} {height}>
    <g class="outlines">
      {#each outlinePaths as d}
        <path {d} />
      {/each}
    </g>
    <g class="dots">
      {#each dotProjections as xy, i (i)}
        <circle cx={xy[0]} cy={xy[1]} r="1.8" />
      {/each}
    </g>
  </svg>
  <div class="year-stack">
    <div class="year-label">Corporate Ownership</div>
    <div class="year-badge">{displayYear}</div>
  </div>
</div>

<style>
  .corp-map {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding-bottom: 24px; /* room for the bottom-right label */
  }
  svg {
    display: block;
    width: 100%;
    height: auto;
  }
  .outlines path {
    fill: #f4f4f4;
    stroke: #cdcdcd;
    stroke-width: 0.6;
    stroke-linejoin: round;
  }
  .dots circle {
    fill: #e67e22;
    fill-opacity: 0.7;
    stroke: #b86413;
    stroke-opacity: 0.45;
    stroke-width: 0.4;
  }
  .year-stack {
    position: absolute;
    bottom: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
    pointer-events: none;
  }
  .year-label {
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #777;
  }
  .year-badge {
    padding: 4px 10px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    font-size: 1rem;
    font-weight: 800;
    color: #e67e22;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
  }
</style>
