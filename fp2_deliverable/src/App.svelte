<script>
  import { onMount } from 'svelte'
  import { loadNeighborhoodGeo, loadParcelSample, METRICS, STATS } from './lib/data.js'

  // ── State ─────────────────────────────────────────────────────────────────
  let geoData    = null   // GeoJSON FeatureCollection — pass to NeighborhoodMap
  let scatter    = []     // array of { neighborhood, lng, lat, monthly_payment }
  let loading    = true
  let error      = null

  // Which metric the choropleth is colored by (index into METRICS array)
  let metricIdx  = 0
  $: activeMetric = METRICS[metricIdx]

  // ── Load data on mount ────────────────────────────────────────────────────
  onMount(async () => {
    try {
      [geoData, scatter] = await Promise.all([
        loadNeighborhoodGeo(),
        loadParcelSample(),
      ])
    } catch (e) {
      error = `Could not load map data. Run fp2_preprocess.py first.\n\n${e.message}`
    } finally {
      loading = false
    }
  })
</script>

<!-- ── Layout ──────────────────────────────────────────────────────────────── -->
<main>

  <!-- Header -->
  <header>
    <p class="label">BOSTON HOUSING · NEIGHBORHOOD AFFORDABILITY</p>
    <h1>Who can afford to live here?</h1>
    <p class="intro">
      Housing speculation drives up prices across Boston — but the burden isn't shared equally.
      Explore how monthly housing costs, investor ownership, and eviction rates vary by neighborhood.
    </p>
  </header>

  <!-- Metric toggle -->
  <div class="metric-row">
    <span class="toggle-label">Show:</span>
    <div class="toggle">
      {#each METRICS as m, i}
        <button
          class:active={metricIdx === i}
          on:click={() => metricIdx = i}
        >{m.label}</button>
      {/each}
    </div>
  </div>

  <!-- Active metric description -->
  <section class="narrative">
    <div class="stat-callout">
      {#if metricIdx === 0}
        $2,000 – $5,000+/mo — the range renters and buyers face across Boston neighborhoods
      {:else if metricIdx === 1}
        {(STATS.total_conversions_2016_2024).toLocaleString()} condo conversions since 2016 — investor-owned buildings dominate high-conversion ZIPs
      {:else if metricIdx === 2}
        ~{STATS.estimated_displaced.toLocaleString()} people displaced since 2016 — concentrated in lower-income neighborhoods
      {/if}
    </div>
    <p>
      {#if metricIdx === 0}
        Monthly payment estimates are calculated as purchase price per unit divided by a 20-year term,
        giving a comparable affordability signal across neighborhoods.
        Warmer colors = higher cost.
      {:else if metricIdx === 1}
        Corporate ownership rate measures the share of residential properties owned by LLCs,
        trusts, and institutional investors. Higher corporate ownership correlates with
        reduced housing availability and rising rents.
      {:else if metricIdx === 2}
        Total eviction filings from 2020–2023. Neighborhoods with high investor activity
        tend to see disproportionately more eviction filings — displacing renters
        from communities they've lived in for generations.
      {/if}
    </p>
  </section>

  <!-- ── MAP GOES HERE ────────────────────────────────────────────────────────
       NURI: import your map component above and replace this placeholder.

       Props already available:
         geoData      — GeoJSON FeatureCollection  (neighborhoods.geojson)
                        Each feature.properties has:
                          name, avg_monthly_payment, median_monthly_payment,
                          p25_payment, p75_payment, parcel_count,
                          total_evictions, avg_corp_own_rate, avg_own_occ_rate,
                          avg_renter_mhi
         scatter      — array of { neighborhood, lng, lat, monthly_payment }
                        ~60 jittered parcel points per neighborhood
         activeMetric — current METRICS entry { key, label, format, makeScale }
                        .key       → which property to read from feature.properties
                        .format(d) → formats a value for display in the tooltip
                        .makeScale → call with geoData to get a D3 color scale

       Example:
         import NeighborhoodMap from './components/NeighborhoodMap.svelte'
         ...
         <NeighborhoodMap {geoData} {scatter} {activeMetric} />

       What the map should do:
         1. Render Boston neighborhood polygons (d3-geo + geoData)
         2. Color each polygon by activeMetric.key using activeMetric.makeScale()
         3. Show scatter points from `scatter` array (toggle-able)
         4. Tooltip on hover: neighborhood name + formatted metric value
         5. Non-trivial interaction (pick one):
              a. Click neighborhood → sidebar panel with all metrics for that hood
              b. Scatter toggle button → show/hide individual parcel dots
              c. Neighborhood search/highlight via dropdown
         6. Legend showing the color scale
  ─────────────────────────────────────────────────────────────────────────── -->
  <div class="map-area">
    {#if loading}
      <p class="loading">Loading map data…</p>
    {:else if error}
      <pre class="error">{error}</pre>
    {:else}
      <!-- NURI: replace this div with <NeighborhoodMap {geoData} {scatter} {activeMetric} /> -->
      <div class="map-placeholder">
        🗺 Map goes here — see Instructions.md<br/>
        <small>{geoData?.features?.length} neighborhoods loaded · {scatter?.length} scatter points loaded</small>
      </div>
    {/if}
  </div>

</main>

<style>
  :global(body) {
    margin: 0;
    background: #0d0d0d;
    color: #ddd;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  }

  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  /* ── Header ── */
  header { margin-bottom: 2rem; }

  .label {
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    color: #c0392b;
    margin: 0 0 0.5rem;
  }

  h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.75rem;
  }

  .intro {
    font-size: 0.95rem;
    color: #888;
    max-width: 700px;
    line-height: 1.6;
    margin: 0;
  }

  /* ── Metric toggle ── */
  .metric-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 2rem 0 1.5rem;
    flex-wrap: wrap;
  }

  .toggle-label {
    font-size: 0.9rem;
    color: #888;
    white-space: nowrap;
  }

  .toggle {
    display: flex;
    gap: 0;
    border: 1px solid #333;
    border-radius: 6px;
    overflow: hidden;
  }

  .toggle button {
    background: #1a1a1a;
    color: #888;
    border: none;
    padding: 0.5rem 1.2rem;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    border-right: 1px solid #333;
  }

  .toggle button:last-child { border-right: none; }
  .toggle button:hover { background: #252525; color: #ccc; }

  .toggle button.active {
    background: #d4730a;
    color: #fff;
    font-weight: 600;
  }

  /* ── Narrative ── */
  .narrative {
    margin-bottom: 2rem;
    max-width: 780px;
  }

  .stat-callout {
    font-size: 1.05rem;
    font-weight: 700;
    color: #d4730a;
    margin-bottom: 0.75rem;
  }

  .narrative p {
    font-size: 0.92rem;
    color: #999;
    line-height: 1.7;
    margin: 0;
  }

  /* ── Map area ── */
  .map-area {
    background: #111;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 2rem;
    min-height: 560px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .map-placeholder {
    color: #444;
    font-size: 1.1rem;
    text-align: center;
    line-height: 2;
  }

  .map-placeholder small {
    display: block;
    font-size: 0.8rem;
    color: #2a7a5e;
    margin-top: 0.5rem;
  }

  .loading {
    color: #555;
    font-size: 0.9rem;
  }

  .error {
    color: #c0392b;
    font-size: 0.8rem;
    background: #1a0a0a;
    padding: 1rem;
    border-radius: 4px;
    white-space: pre-wrap;
    max-width: 600px;
  }
</style>
