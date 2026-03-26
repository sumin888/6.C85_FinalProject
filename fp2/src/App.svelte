<script>
  import { onMount, tick } from 'svelte';
  import { loadNeighborhoodGeo, loadProperties, filterProperties } from './lib/data.js';
  import NeighborhoodMap from './components/NeighborhoodMap.svelte';

  // ── State ──────────────────────────────────────────────────────────────────
  let geoData = null;
  let properties = [];
  let loading = true;
  let error = null;

  let maxRent = 3000;
  let scrollStep = 0;
  let selectedNeighborhood = null;
  let zoomProgress = 0;  // 0 = full Boston, 1 = fully zoomed

  // ── Scroll-driven state ──────────────────────────────────────────────────
  $: excludeEvicted = scrollStep >= 3;

  $: zoomFeature = (selectedNeighborhood && geoData)
    ? geoData.features.find(f => f.properties.name === selectedNeighborhood)
    : null;

  // ── Derived ────────────────────────────────────────────────────────────────
  $: filtered = filterProperties(properties, maxRent, excludeEvicted);
  $: affordableCount = filtered.length;
  $: affordablePct =
    properties.length > 0
      ? ((affordableCount / properties.length) * 100).toFixed(1)
      : '0.0';

  $: sortedNeighborhoods = geoData
    ? geoData.features.map(f => f.properties.name).sort()
    : [];

  // ── Narrative sections ───────────────────────────────────────────────────
  const sections = [
    {
      title: "Boston's Housing Market",
      body: `Every dot on this map represents a residential property sold in Boston between
             2018 and 2023. Over <strong>32,000 transactions</strong> from the
             <strong>MAPC Regional Residential Sales dataset</strong> reveal where housing
             exists across the city's 24 neighborhoods. Monthly rent is estimated from sale
             price using a price-to-rent ratio of 20. Use the slider on the right to set
             your budget — then pick a neighborhood below to explore.`,
    },
    {
      title: "The Eviction Shadow",
      body: `Between 2020 and 2024, over <strong>6,000 eviction cases</strong> were filed at
             properties in Boston — for non-payment of rent, lease violations, and no-fault
             evictions. Using geocoded <strong>Massachusetts court filing records
             (2020–2024)</strong>, we spatially matched each case to the nearest property
             sale within 50 meters. The result: <strong>26.7% of all properties on this map
             had at least one eviction filed at or near their address in the past five
             years</strong>.`,
    },
    {
      title: "Zooming In",
      body: null, // dynamic content rendered in template
    },
    {
      title: "What's Really Available",
      body: `Now we remove every property that had an eviction court filing within 50 meters
             of its address between 2020 and 2024. These are locations where tenants faced
             displacement — a concrete signal of housing instability. What remains is where
             <strong>stable, affordable housing</strong> actually exists. Adjust
             the slider to explore.
             <span class="sources">Sources: MAPC Regional Residential Sales (2000–2023);
             MA Trial Court Eviction Filing Records (2020–2024); Boston Neighborhood
             boundaries via BPDA.</span>`,
    },
  ];

  // ── Load data + setup observer ─────────────────────────────────────────────
  onMount(async () => {
    try {
      [geoData, properties] = await Promise.all([
        loadNeighborhoodGeo(),
        loadProperties(),
      ]);
    } catch (e) {
      error = e.message ?? 'Failed to load data.';
    } finally {
      loading = false;
    }

    await tick();

    // Scroll-driven step tracking + zoom progress
    function onScroll() {
      const steps = document.querySelectorAll('.scroll-step');
      if (steps.length === 0) return;

      const vh = window.innerHeight;
      const mid = vh / 2;

      // Determine active step (which step's center is closest to viewport center)
      let activeStep = 0;
      for (const el of steps) {
        const rect = el.getBoundingClientRect();
        if (rect.top < mid && rect.bottom > mid) {
          activeStep = parseInt(el.dataset.step, 10);
          break;
        }
      }
      scrollStep = activeStep;

      // Compute continuous zoom progress for step 2
      const step2 = steps[2];
      if (step2 && zoomFeature) {
        const rect = step2.getBoundingClientRect();
        // Progress: 0 when step2 top enters viewport bottom, 1 when step2 center reaches viewport center
        const progress = 1 - (rect.top / vh);
        zoomProgress = Math.max(0, Math.min(1, progress));
      } else {
        // If before step 2 or no neighborhood selected, no zoom
        if (scrollStep < 2) zoomProgress = 0;
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll(); // initial call
    return () => window.removeEventListener('scroll', onScroll);
  });
</script>

<div class="app">
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading Boston housing data…</p>
    </div>
  {:else if error}
    <div class="error-state">
      <p>Error: {error}</p>
    </div>
  {:else}
    <!-- Sticky map background -->
    <div class="map-sticky">
      <!-- Controls overlay (top-right) -->
      <div class="controls-overlay">
        <section class="control-group primary-control">
          <div class="control-header">
            <label for="rent-slider" class="control-label">Max Monthly Rent</label>
            <span class="rent-display">${maxRent.toLocaleString()}<span class="rent-unit">/mo</span></span>
          </div>
          <input
            id="rent-slider"
            type="range"
            min="200"
            max="10000"
            step="50"
            bind:value={maxRent}
            class="rent-slider"
            style="--pct: {(((maxRent - 200) / 9800) * 100).toFixed(2)}%"
          />
          <div class="slider-ticks">
            <span>$200</span>
            <span>$2,500</span>
            <span>$5,000</span>
            <span>$7,500</span>
            <span>$10,000</span>
          </div>

          <!-- Affordability summary -->
          <div class="affordability-summary">
            <div class="summary-stat">
              <span class="stat-value accent">{affordableCount.toLocaleString()}</span>
              <span class="stat-label">properties {excludeEvicted ? '(no evictions)' : 'at or below this rent'}</span>
            </div>
            <div class="summary-stat">
              <span class="stat-value">{affordablePct}%</span>
              <span class="stat-label">of all 32,695 Boston sales</span>
            </div>
          </div>

          <!-- Rent color legend -->
          <div class="rent-legend">
            <span class="legend-label">Monthly Rent</span>
            <div class="legend-bar"></div>
            <div class="legend-ticks">
              <span>$200</span>
              <span>$1,500</span>
              <span>$3,000</span>
              <span>$5,000</span>
            </div>
          </div>

          <!-- Size legend -->
          <div class="size-legend">
            <span class="legend-label">Properties at Location</span>
            <div class="size-legend-row">
              <div class="size-dot-group">
                <span class="size-dot" style="width:6px;height:6px;"></span>
                <span class="size-dot-label">1</span>
              </div>
              <div class="size-dot-group">
                <span class="size-dot" style="width:12px;height:12px;"></span>
                <span class="size-dot-label">5</span>
              </div>
              <div class="size-dot-group">
                <span class="size-dot" style="width:18px;height:18px;"></span>
                <span class="size-dot-label">20+</span>
              </div>
            </div>
            <span class="size-hint">Larger dots = more units at same address</span>
          </div>
        </section>
      </div>

      <NeighborhoodMap
        {geoData}
        {properties}
        {maxRent}
        {excludeEvicted}
        {zoomFeature}
        {zoomProgress}
      />
    </div>

    <!-- Scrollable narrative overlay -->
    <div class="scroll-foreground">
      {#each sections as section, i}
        <div
          class="scroll-step"
          data-step={i}
        >
          <div class="step-card" class:active={scrollStep === i}>
            <h2>{section.title}</h2>

            {#if i === 0}
              <p>{@html section.body}</p>
              {#if geoData}
                <label class="select-label">Choose a neighborhood</label>
                <select bind:value={selectedNeighborhood} class="neighborhood-select">
                  <option value={null}>All neighborhoods</option>
                  {#each sortedNeighborhoods as name}
                    <option value={name}>{name}</option>
                  {/each}
                </select>
              {/if}

            {:else if i === 2}
              {#if selectedNeighborhood && zoomFeature}
                <p>
                  Let's zoom into <strong>{selectedNeighborhood}</strong>.
                  This neighborhood had <strong>{zoomFeature.properties.count?.toLocaleString() ?? '—'}</strong>
                  property sales in our dataset with a median estimated rent of
                  <strong>${zoomFeature.properties.median_rent?.toLocaleString() ?? '—'}/mo</strong>.
                  {#if zoomFeature.properties.total_evictions}
                    There were <strong>{zoomFeature.properties.total_evictions.toLocaleString()}</strong>
                    eviction filings in the area between 2020 and 2023.
                  {/if}
                </p>
              {:else}
                <p>Scroll back up and <strong>pick a neighborhood</strong> from the dropdown to zoom in and explore it in detail.</p>
              {/if}

            {:else}
              <p>{@html section.body}</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  /* ── Reset / base ──────────────────────────────────────────────────────── */
  :global(*) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    background: #f5f5f5;
    color: #333;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.6;
  }

  :global(html, body, #app) {
    height: auto;
  }

  /* ── App shell ─────────────────────────────────────────────────────────── */
  .app {
    position: relative;
  }

  /* ── Sticky map ─────────────────────────────────────────────────────────── */
  .map-sticky {
    position: sticky;
    top: 0;
    height: 100vh;
    width: 100%;
    background: #f0f0f0;
    z-index: 1;
  }

  /* ── Scrollable foreground ──────────────────────────────────────────────── */
  .scroll-foreground {
    position: relative;
    z-index: 10;
    pointer-events: none;
    margin-top: -100vh;
  }

  .scroll-step {
    min-height: 100vh;
    display: flex;
    align-items: center;
    padding: 0 40px;
  }

  .step-card {
    pointer-events: auto;
    background: rgba(255, 255, 255, 0.93);
    max-width: 380px;
    padding: 28px 24px;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.10);
    border: 1px solid #e0e0e0;
    opacity: 0.4;
    transform: translateY(10px);
    transition: opacity 0.4s ease, transform 0.4s ease;
  }

  .step-card.active {
    opacity: 1;
    transform: translateY(0);
  }

  .step-card h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 12px;
    letter-spacing: -0.01em;
  }

  .step-card p {
    font-size: 0.9rem;
    color: #444;
    line-height: 1.7;
  }

  .step-card :global(strong) {
    color: #c0392b;
    font-weight: 600;
  }

  .step-card :global(.sources) {
    display: block;
    margin-top: 12px;
    font-size: 0.72rem;
    color: #888;
    line-height: 1.5;
    font-style: italic;
  }

  /* ── Neighborhood selector ──────────────────────────────────────────────── */
  .select-label {
    display: block;
    margin-top: 16px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #666;
    margin-bottom: 6px;
  }

  .neighborhood-select {
    width: 100%;
    padding: 8px 12px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.88rem;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background: #fff;
    color: #333;
    cursor: pointer;
    outline: none;
    transition: border-color 0.15s;
  }

  .neighborhood-select:focus {
    border-color: #c0392b;
  }

  /* ── Controls overlay (top-right) ────────────────────────────────────────── */
  .controls-overlay {
    position: absolute;
    top: 16px;
    right: 16px;
    z-index: 30;
    width: 280px;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .primary-control {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.10);
  }

  .control-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .control-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #666;
  }

  .rent-display {
    font-size: 1.6rem;
    font-weight: 700;
    color: #c0392b;
    line-height: 1;
  }

  .rent-unit {
    font-size: 0.9rem;
    font-weight: 400;
    color: #666;
  }

  /* ── Slider ────────────────────────────────────────────────────────────── */
  .rent-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 2px;
    background: linear-gradient(
      to right,
      #c0392b 0%,
      #c0392b var(--pct, 28.57%),
      #ddd var(--pct, 28.57%)
    );
    outline: none;
    cursor: pointer;
  }

  .rent-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #c0392b;
    border: 2px solid #fff;
    cursor: pointer;
    box-shadow: 0 0 6px rgba(192, 57, 43, 0.4);
  }

  .rent-slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #c0392b;
    border: 2px solid #fff;
    cursor: pointer;
  }

  .slider-ticks {
    display: flex;
    justify-content: space-between;
    font-size: 0.65rem;
    color: #999;
    margin-top: -4px;
  }

  /* ── Affordability summary ─────────────────────────────────────────────── */
  .affordability-summary {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 4px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
  }

  .summary-stat {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .stat-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a1a;
  }

  .stat-value.accent {
    color: #c0392b;
  }

  .stat-label {
    font-size: 0.75rem;
    color: #666;
  }

  /* ── Rent color legend ─────────────────────────────────────────────────── */
  .rent-legend {
    margin-top: 4px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .legend-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #666;
  }

  .legend-bar {
    height: 10px;
    border-radius: 3px;
    background: linear-gradient(to right, #ffcccc, #8b0000);
  }

  .legend-ticks {
    display: flex;
    justify-content: space-between;
    font-size: 0.6rem;
    color: #999;
  }

  /* ── Size legend ──────────────────────────────────────────────────────── */
  .size-legend {
    margin-top: 4px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .size-legend-row {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .size-dot-group {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .size-dot {
    display: inline-block;
    border-radius: 50%;
    background: #c0392b;
    opacity: 0.75;
    flex-shrink: 0;
  }

  .size-dot-label {
    font-size: 0.65rem;
    color: #666;
  }

  .size-hint {
    font-size: 0.6rem;
    color: #999;
    font-style: italic;
  }

  /* ── Loading / Error ───────────────────────────────────────────────────── */
  .loading-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    gap: 16px;
    color: #666;
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid #e0e0e0;
    border-top-color: #c0392b;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
