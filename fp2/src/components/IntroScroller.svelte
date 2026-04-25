<script>
  import { createEventDispatcher } from 'svelte';
  import { tweened } from 'svelte/motion';
  import { cubicInOut } from 'svelte/easing';

  const dispatch = createEventDispatcher();

  const zoomTween = tweened(0, { duration: 800, easing: cubicInOut });

  export let geoData;
  // eslint-disable-next-line no-unused-vars
  export let properties;  // unused here but kept for API compatibility
  export let maxRent;

  // ── Map control props (bound to parent) ────────────────────────────────
  export let mapMaxYear = 2024;
  export let mapUseCurrentRent = false;
  export let mapHighlightInvestors = false;
  export let mapHighlightEvictions = false;
  export let openReferences = () => {};
  export let mapZoomFeature = null;
  export let mapZoomProgress = 0;

  // Explore page should show every eviction case, ignoring year/rent filters.
  $: mapMaxYear = 2024;
  $: mapUseCurrentRent = false;
  $: mapHighlightInvestors = true;   // split dots into blue (individual) / orange (corp) to match legend
  $: mapHighlightEvictions = false;
  $: maxRent = 99999;

  // Selection received from the map (bound in NeighborhoodMap via selectedDots)
  export let selectedDots = [];

  // Reset signal sent to NeighborhoodMap to clear user pan/zoom
  export let resetViewSignal = 0;

  // Dropdown state (pending selection)
  let pendingNeighborhood = '';
  let activeNeighborhood = null;

  $: sortedNeighborhoods = geoData
    ? geoData.features.map(f => f.properties.name).sort() : [];

  $: mapZoomFeature = (activeNeighborhood && geoData)
    ? geoData.features.find(f => f.properties.name === activeNeighborhood)
    : null;

  // Smoothly tween the zoom progress when the active neighborhood changes
  $: zoomTween.set(activeNeighborhood ? 1 : 0);
  $: mapZoomProgress = $zoomTween;

  function selectNeighborhood() {
    activeNeighborhood = pendingNeighborhood || null;
    // Clear any user pan/zoom so the selected neighborhood always shows in the same constant view
    resetViewSignal = resetViewSignal + 1;
  }

  function resetView() {
    pendingNeighborhood = '';
    activeNeighborhood = null;
    resetViewSignal = resetViewSignal + 1;
  }
</script>

<div class="explore-overlay">
<!-- Top-left: back buttons (no bubble) -->
<div class="explore-nav">
  <button class="nav-btn green" on:click={() => dispatch('backToDeepDive')}>&larr; Neighborhood stories</button>
  <button class="nav-btn gray" on:click={() => dispatch('back')}>&larr; Back to overview</button>
</div>

<!-- Center-left bubble: neighborhood picker -->
<aside class="explore-picker">
  <div class="picker">
    <label for="explore-hood">Jump to neighborhood</label>
    <select id="explore-hood" bind:value={pendingNeighborhood}>
      <option value="">All neighborhoods</option>
      {#each sortedNeighborhoods as name}
        <option value={name}>{name}</option>
      {/each}
    </select>
    <div class="picker-btns">
      <button class="select-btn" on:click={selectNeighborhood} disabled={!pendingNeighborhood && !activeNeighborhood}>
        Select
      </button>
      <button class="reset-btn" on:click={resetView} title="Recenter map and clear selection">
        Reset view
      </button>
    </div>
    {#if activeNeighborhood}
      <div class="picker-active">Viewing <strong>{activeNeighborhood}</strong></div>
    {/if}
    <div class="picker-hint">Scroll to zoom · drag to pan</div>
  </div>
</aside>

<div class="explore-right">
<!-- Right: legend bubble (top) -->
<aside class="explore-legend">
  <div class="legend-title">Eviction cases</div>
  <div class="legend-row">
    <span class="legend-swatch individual"></span>
    <span class="legend-label">Individual landlord</span>
  </div>
  <div class="legend-row">
    <span class="legend-swatch corporate"></span>
    <span class="legend-label">Corporate landlord</span>
  </div>

  <div class="legend-subtitle">Dot size = cases at location</div>
  <div class="size-row">
    <div class="size-cell">
      <span class="size-swatch" style="width:6px;height:6px;"></span>
      <span class="size-lbl">1</span>
    </div>
    <div class="size-cell">
      <span class="size-swatch" style="width:10px;height:10px;"></span>
      <span class="size-lbl">few</span>
    </div>
    <div class="size-cell">
      <span class="size-swatch" style="width:16px;height:16px;"></span>
      <span class="size-lbl">many</span>
    </div>
  </div>

  <div class="legend-hint">Click any dot to see property details.</div>

  <div class="legend-footnote">
    <span>Built from MAPC sales · MA Trial Court evictions · Boston assessment rolls · Zillow ZORI · BPDA + Census.</span>
    <button class="legend-refs-link" on:click={openReferences}>
      See full references ↗
    </button>
  </div>
</aside>

<!-- Right: property detail bubble (below legend) -->
<aside class="explore-detail">
  <section class="detail">
    <div class="detail-title">
      {selectedDots.length > 0
        ? (selectedDots.length === 1 ? 'Eviction detail' : `${selectedDots.length} cases at this location`)
        : 'Eviction detail'}
    </div>

    {#if selectedDots.length === 0}
      <div class="detail-empty">Click a dot on the map.</div>
    {:else}
      {#each selectedDots as p, idx}
        {#if idx > 0}<hr class="detail-divider" />{/if}
        <div class="detail-address">
          {p.address ?? 'Unknown address'}{#if p.unit}, Unit {p.unit}{/if}
        </div>
        <div class="detail-meta">
          <span class="pill" class:corp={p.corp_landlord}>
            {p.corp_landlord ? 'Corporate landlord' : 'Individual landlord'}
          </span>
          {#if p.case_type}
            <span class="pill soft">{p.case_type}</span>
          {/if}
        </div>

        {#if p.rent_at_filing || p.rent_now}
          {@const pctChange = p.rent_at_filing && p.rent_now
            ? Math.round((p.rent_now / p.rent_at_filing - 1) * 100)
            : null}
          <div class="rent-compare">
            <div class="rc-col">
              <div class="rc-label">Rent at filing</div>
              <div class="rc-val then">
                {p.rent_at_filing ? `$${p.rent_at_filing.toLocaleString()}` : '—'}
              </div>
            </div>
            <div class="rc-arrow">
              {#if pctChange != null}
                <div class="rc-pct" class:up={pctChange > 0} class:down={pctChange < 0}>
                  {pctChange > 0 ? '+' : ''}{pctChange}%
                </div>
              {/if}
              <div class="rc-line"></div>
            </div>
            <div class="rc-col">
              <div class="rc-label">Rent now</div>
              <div class="rc-val now">
                {p.rent_now ? `$${p.rent_now.toLocaleString()}` : '—'}
              </div>
            </div>
          </div>
        {/if}

        <div class="detail-grid">
          {#if p.file_date}
            <div class="dg-row"><span class="dk">Filed</span><span class="dv">{p.file_date}</span></div>
          {/if}
          {#if p.case_status}
            <div class="dg-row"><span class="dk">Status</span><span class="dv">{p.case_status}</span></div>
          {/if}
          {#if p.dispo}
            <div class="dg-row"><span class="dk">Outcome</span><span class="dv">{p.dispo}</span></div>
          {/if}
          {#if p.neighborhood}
            <div class="dg-row"><span class="dk">Neighborhood</span><span class="dv">{p.neighborhood}</span></div>
          {/if}
        </div>
      {/each}
    {/if}
  </section>

  <p class="sources">
    Sources: Zillow ZORI; MAPC Residential Sales (2000–2023);
    MA Trial Court Eviction Records (2020–2024); BPDA.
  </p>
</aside>
</div>
</div>

<style>
  .explore-overlay {
    position: relative;
    margin-top: -100vh;
    height: 100vh;
    z-index: 10;
    pointer-events: none;
  }
  .explore-overlay > * { pointer-events: auto; }

  .explore-nav {
    position: absolute;
    top: 16px;
    left: 16px;
    z-index: 20;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    pointer-events: auto;
  }

  .nav-btn {
    padding: 6px 12px;
    border-radius: 6px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    white-space: nowrap;
  }
  .nav-btn.green {
    background: #eef4ee;
    color: #2d8c2d;
    border: 1px solid #cfe1cf;
  }
  .nav-btn.green:hover { background: #dfeedf; }
  .nav-btn.gray {
    background: #f0f0f0;
    color: #555;
    border: 1px solid #d5d5d5;
  }
  .nav-btn.gray:hover { background: #e5e5e5; }

  .explore-picker {
    position: absolute;
    top: 50%;
    left: 16px;
    transform: translateY(-50%);
    width: 260px;
    z-index: 20;
    padding: 14px;
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.10);
    pointer-events: auto;
  }

  .back-btns {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .back-btn {
    padding: 6px 12px;
    background: #eef4ee;
    color: #2d8c2d;
    border: 1px solid #cfe1cf;
    border-radius: 6px;
    font-family: inherit;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
  }
  .back-btn:hover { background: #dfeedf; }
  .back-btn.subtle {
    background: #f0f0f0;
    color: #666;
    border-color: #ddd;
    font-weight: 500;
  }
  .back-btn.subtle:hover { background: #e5e5e5; }

  .picker {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .picker label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #555;
  }
  .picker select {
    padding: 8px 10px;
    font-family: inherit;
    font-size: 0.85rem;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    background: #fff;
    color: #333;
    cursor: pointer;
    outline: none;
    width: 100%;
  }
  .picker select:focus { border-color: #2d8c2d; }

  .picker-btns {
    display: flex;
    gap: 8px;
    margin-top: 2px;
  }
  .select-btn {
    flex: 1;
    padding: 8px 14px;
    background: #2d8c2d;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }
  .select-btn:hover { background: #236b23; }
  .select-btn:disabled {
    background: #c8c8c8;
    cursor: not-allowed;
  }
  .reset-btn {
    padding: 8px 10px;
    background: transparent;
    color: #666;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-family: inherit;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .reset-btn:hover { background: #f0f0f0; }
  .picker-active {
    font-size: 0.75rem;
    color: #555;
  }
  .picker-active strong { color: #2d8c2d; }
  .picker-hint {
    font-size: 0.68rem;
    color: #999;
    font-style: italic;
  }

  .explore-right {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 320px;
    max-height: calc(100vh - 32px);
    z-index: 15;
    display: flex;
    flex-direction: column;
    gap: 14px;
    pointer-events: none;
    overflow: hidden;
  }
  .explore-right > * { pointer-events: auto; }

  .explore-legend {
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.10);
    flex-shrink: 0;
  }

  .explore-detail {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    padding: 14px;
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.10);
  }

  .legend-title, .detail-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #555;
    margin-bottom: 8px;
  }

  .legend-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }
  .legend-swatch {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1.5px solid rgba(0,0,0,0.25);
  }
  .legend-swatch.individual { background: #2563eb; }
  .legend-swatch.corporate { background: #e67e22; }
  .legend-label {
    font-size: 0.82rem;
    color: #333;
  }
  .legend-hint {
    font-size: 0.7rem;
    color: #999;
    margin-top: 6px;
    font-style: italic;
  }
  .legend-footnote {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #eee;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .legend-footnote span {
    font-size: 0.66rem;
    color: #999;
    line-height: 1.45;
    font-style: italic;
  }
  .legend-refs-link {
    align-self: flex-start;
    background: none;
    border: none;
    color: #2563eb;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
  }
  .legend-refs-link:hover { color: #1d4dbf; }
  .legend-subtitle {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin-top: 10px;
    margin-bottom: 4px;
  }
  .size-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 2px 0 0;
  }
  .size-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
  }
  .size-swatch {
    display: inline-block;
    background: #666;
    border: 1px solid rgba(0,0,0,0.25);
    border-radius: 50%;
    flex-shrink: 0;
  }
  .size-lbl {
    font-size: 0.66rem;
    color: #777;
  }

  .detail-empty {
    font-size: 0.8rem;
    color: #999;
    font-style: italic;
  }
  .detail-address {
    font-weight: 700;
    font-size: 0.88rem;
    color: #1a1a1a;
    margin-bottom: 6px;
  }
  .detail-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }
  .pill {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    background: #e6efff;
    color: #2563eb;
    border: 1px solid #bdd0f5;
  }
  .pill.corp {
    background: #fde8e6;
    color: #c0392b;
    border-color: #f0b3aa;
  }
  .pill.soft {
    background: #f0f0f0;
    color: #555;
    border-color: #ddd;
  }

  .rent-compare {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 8px;
    margin: 4px 0 10px;
    padding: 10px;
    background: linear-gradient(135deg, #fff8ec 0%, #fdecec 100%);
    border: 1px solid #f0d9c8;
    border-radius: 6px;
  }
  .rc-col { display: flex; flex-direction: column; align-items: center; text-align: center; min-width: 0; }
  .rc-label {
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8a7a6a;
    margin-bottom: 2px;
  }
  .rc-val {
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }
  .rc-val.then { color: #7a5c3a; }
  .rc-val.now { color: #c0392b; }
  .rc-arrow { display: flex; flex-direction: column; align-items: center; min-width: 52px; }
  .rc-pct {
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
  .rc-pct.up { background: #fde8e6; border-color: #f2b3aa; color: #c0392b; }
  .rc-pct.down { background: #e8f5e8; border-color: #9ec99e; color: #2d8c2d; }
  .rc-line {
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, #e0c9b3 0%, #d98b7c 100%);
    border-radius: 1px;
    position: relative;
  }
  .rc-line::after {
    content: '';
    position: absolute;
    right: -1px;
    top: 50%;
    transform: translateY(-50%);
    border-left: 6px solid #d98b7c;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
  }

  .detail-grid {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .dg-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 0.75rem;
  }
  .dk { color: #888; }
  .dv { font-weight: 600; color: #333; }

  .detail-divider {
    border: none;
    border-top: 1px solid #eee;
    margin: 10px 0;
  }

  .sources {
    font-size: 0.68rem;
    color: #999;
    line-height: 1.5;
    font-style: italic;
    margin-top: 4px;
  }
</style>
