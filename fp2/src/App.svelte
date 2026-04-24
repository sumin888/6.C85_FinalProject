<script>
  import { onMount } from 'svelte';
  import { loadNeighborhoodGeo, loadProperties, loadZoriByNeighborhood, loadEvictionsByNeighborhood, loadStoryData, loadEvictionDots, filterProperties, filterEvictionDots } from './lib/data.js';
  import NeighborhoodMap from './components/NeighborhoodMap.svelte';
  import ControlsOverlay from './components/ControlsOverlay.svelte';
  import StoryIntro from './components/StoryIntro.svelte';
  import NeighborhoodDeepDive from './components/NeighborhoodDeepDive.svelte';
  import IntroScroller from './components/IntroScroller.svelte';

  // ── Global state ───────────────────────────────────────────────────────
  let geoData = null;
  let properties = [];
  let evictionDots = [];
  let zoriData = null;
  let evictionData = null;
  let storyData = null;
  let loading = true;
  let error = null;

  let phase = 'story';  // 'story' | 'deepdive' | 'explore'
  let maxRent = 3000;

  // ── Map control props (set by active phase component) ──────────────────
  let mapMaxYear = 2019;
  let mapUseCurrentRent = false;
  let mapHighlightInvestors = false;
  let mapHighlightEvictions = false;
  let mapZoomFeature = null;
  let mapZoomProgress = 0;
  let mapFocusNeighborhood = null;
  let mapDimOthers = false;

  let clickedNeighborhood = null;
  let neighborhoodCounts = {};
  let mapSelectedDots = [];
  let mapResetViewSignal = 0;

  // ── Show map only in deepdive and explore phases ───────────────────────
  $: showMap = phase !== 'story';

  // ── Reserve map space for right-hand panels (deep-dive sidebar is 420px) ─
  $: mapRightReservedPx = phase === 'deepdive' ? 420 : 0;

  // ── Derived for controls overlay (based on eviction dots) ───────────────
  $: visibleDots = filterEvictionDots(evictionDots, maxRent, { useCurrentRent: mapUseCurrentRent, maxYear: mapMaxYear });
  $: affordableCount = visibleDots.length;
  $: affordablePct = evictionDots.length > 0
    ? ((affordableCount / evictionDots.length) * 100).toFixed(1) : '0.0';
  $: oldAffordableCount = mapUseCurrentRent
    ? filterEvictionDots(evictionDots, maxRent, { useCurrentRent: false }).length : affordableCount;
  $: lostCount = oldAffordableCount - filterEvictionDots(evictionDots, maxRent, { useCurrentRent: true }).length;
  $: visibleCount = visibleDots.length;
  $: summaryLabel = mapUseCurrentRent ? 'eviction cases at current rents' : 'eviction cases at filing-time rents';

  // ── Load data ──────────────────────────────────────────────────────────
  onMount(async () => {
    try {
      [geoData, properties, evictionDots, zoriData, evictionData, storyData] = await Promise.all([
        loadNeighborhoodGeo(),
        loadProperties(),
        loadEvictionDots(),
        loadZoriByNeighborhood(),
        loadEvictionsByNeighborhood(),
        loadStoryData(),
      ]);
    } catch (e) {
      error = e.message ?? 'Failed to load data.';
    } finally {
      loading = false;
    }
  });

  function enterDeepDive() {
    phase = 'deepdive';
    mapDimOthers = true;
    mapZoomFeature = null;
    mapZoomProgress = 0;
    maxRent = 2000;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function enterExplore() {
    phase = 'explore';
    mapFocusNeighborhood = null;
    mapDimOthers = false;
    mapHighlightEvictions = false;
    mapHighlightInvestors = false;
    mapUseCurrentRent = false;
    mapMaxYear = 2024;
    mapZoomFeature = null;
    mapZoomProgress = 0;
    maxRent = 99999;  // effectively unlimited — shows all eviction cases on the explore page
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function backToStory() {
    phase = 'story';
    mapFocusNeighborhood = null;
    mapDimOthers = false;
    mapHighlightEvictions = false;
    mapHighlightInvestors = false;
    mapUseCurrentRent = false;
    mapMaxYear = 2019;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
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
    <!-- Phase 1: Story Intro (no map, full-screen charts) -->
    {#if phase === 'story'}
      <StoryIntro
        {storyData}
        {zoriData}
        {evictionDots}
        {geoData}
        on:enterDeepDive={enterDeepDive}
      />
    {:else}
      <!-- Phases 2 & 3: Map-based views -->
      <div class="map-sticky">
        {#if phase !== 'explore'}
          <ControlsOverlay
            bind:maxRent
            {affordableCount}
            {affordablePct}
            {visibleCount}
            {summaryLabel}
            {lostCount}
            showLost={mapUseCurrentRent}
            highlightInvestors={mapHighlightInvestors}
            highlightEvictions={mapHighlightEvictions}
          >
          {#if clickedNeighborhood}
            {@const sp = clickedNeighborhood.properties}
            {@const affordableHere = neighborhoodCounts[sp.name] ?? 0}
            <section class="detail-panel">
              <div class="detail-header">
                <h3>{sp.name}</h3>
                <button class="close-btn" on:click={() => clickedNeighborhood = null}>&times;</button>
              </div>
              <div class="detail-section">
                <div class="detail-sectiontitle">Affordability at ${maxRent.toLocaleString()}/mo</div>
                <div class="detail-bigstat">
                  <span class="bignum accent">{affordableHere.toLocaleString()}</span>
                  <span class="bigdesc">of {sp.count?.toLocaleString() ?? '—'} shown</span>
                </div>
              </div>
              <div class="detail-section">
                <div class="detail-sectiontitle">Rent</div>
                <div class="stat-row"><span>Median</span><span class="sv">${sp.median_rent?.toLocaleString()}/mo</span></div>
                <div class="stat-row"><span>Average</span><span class="sv">${sp.avg_rent?.toLocaleString()}/mo</span></div>
              </div>
              <div class="detail-section">
                <div class="detail-sectiontitle">Investor Activity</div>
                <div class="stat-row"><span>Corporate ownership</span><span class="sv">{sp.avg_corp_own_rate != null ? (sp.avg_corp_own_rate * 100).toFixed(1) + '%' : 'N/A'}</span></div>
                <div class="stat-row"><span>Owner-occupied</span><span class="sv">{sp.avg_own_occ_rate != null ? (sp.avg_own_occ_rate * 100).toFixed(1) + '%' : 'N/A'}</span></div>
              </div>
            </section>
          {/if}
          </ControlsOverlay>
        {/if}

        <NeighborhoodMap
          {geoData}
          dots={evictionDots}
          {maxRent}
          maxYear={mapMaxYear}
          useCurrentRent={mapUseCurrentRent}
          highlightInvestors={mapHighlightInvestors}
          highlightEvictions={mapHighlightEvictions}
          focusNeighborhood={mapFocusNeighborhood}
          dimOtherNeighborhoods={mapDimOthers}
          zoomFeature={mapZoomFeature}
          zoomProgress={mapZoomProgress}
          rightReservedPx={mapRightReservedPx}
          darkColorMode={phase === 'explore' || phase === 'deepdive'}
          externalPopup={phase === 'explore'}
          userPanZoom={phase === 'explore'}
          resetViewSignal={mapResetViewSignal}
          bind:selectedDots={mapSelectedDots}
          bind:selectedNeighborhood={clickedNeighborhood}
          bind:affordableByNeighborhood={neighborhoodCounts}
        />
      </div>

      {#if phase === 'deepdive'}
        <NeighborhoodDeepDive
          {geoData}
          {properties}
          bind:maxRent
          {zoriData}
          {evictionData}
          bind:mapMaxYear
          bind:mapUseCurrentRent
          bind:mapHighlightInvestors
          bind:mapHighlightEvictions
          bind:mapFocusNeighborhood
          bind:mapDimOthers
          on:back={backToStory}
          on:explore={enterExplore}
        />
      {:else if phase === 'explore'}
        <IntroScroller
          {geoData}
          {properties}
          bind:maxRent
          bind:mapMaxYear
          bind:mapUseCurrentRent
          bind:mapHighlightInvestors
          bind:mapHighlightEvictions
          bind:mapZoomFeature
          bind:mapZoomProgress
          selectedDots={mapSelectedDots}
          bind:resetViewSignal={mapResetViewSignal}
          on:back={backToStory}
          on:backToDeepDive={enterDeepDive}
        />
      {/if}
    {/if}
  {/if}
</div>

<style>
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background: #f5f5f5; color: #333;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px; line-height: 1.6;
  }
  :global(html, body, #app) { height: auto; }

  .app { position: relative; }

  .map-sticky {
    position: sticky; top: 0; height: 100vh; width: 100%;
    background: #f0f0f0; z-index: 1;
  }

  .detail-panel {
    background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10); overflow-y: auto; flex: 1; min-height: 0;
  }
  .detail-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 14px 8px; border-bottom: 1px solid #eee;
    position: sticky; top: 0; background: #fff; z-index: 1;
  }
  .detail-header h3 { font-size: 0.95rem; font-weight: 700; color: #1a1a1a; }
  .close-btn {
    background: none; border: none; color: #999; font-size: 1.2rem;
    cursor: pointer; line-height: 1; padding: 2px 4px; border-radius: 3px;
  }
  .close-btn:hover { color: #333; }
  .detail-section {
    padding: 10px 14px; border-bottom: 1px solid #eee;
    display: flex; flex-direction: column; gap: 5px;
  }
  .detail-sectiontitle {
    font-size: 0.6rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #888; margin-bottom: 2px;
  }
  .detail-bigstat { display: flex; align-items: baseline; gap: 6px; }
  .bignum { font-size: 1.2rem; font-weight: 700; color: #1a1a1a; line-height: 1; }
  .bignum.accent { color: #2d8c2d; }
  .bigdesc { font-size: 0.7rem; color: #666; }
  .stat-row {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 8px; font-size: 0.72rem; color: #666;
  }
  .stat-row .sv { font-weight: 600; color: #333; white-space: nowrap; }

  .loading-state, .error-state {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 100vh; gap: 16px; color: #666;
  }
  .spinner {
    width: 36px; height: 36px; border: 3px solid #e0e0e0;
    border-top-color: #2d8c2d; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
