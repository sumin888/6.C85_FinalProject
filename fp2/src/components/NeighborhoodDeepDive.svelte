<script>
  import { onMount, onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { currentNeighborhood, nextNeighborhood, prevNeighborhood } from '../stores/navigation.js';
  import NeighborhoodNav from './NeighborhoodNav.svelte';
  import NeighborhoodStory from './NeighborhoodStory.svelte';

  const dispatch = createEventDispatcher();

  export let geoData;
  export let properties;
  export let maxRent;
  export let zoriData;
  export let evictionData;

  const RENT_MIN = 500;
  const RENT_MAX = 6000;
  const RENT_STEP = 100;

  // Map control outputs (bound to parent)
  export let mapMaxYear = 2022;
  export let mapUseCurrentRent = false;
  export let mapHighlightInvestors = false;
  export let mapHighlightEvictions = false;
  export let mapFocusNeighborhood = null;
  export let mapDimOthers = true;

  // Scroll step inside NeighborhoodStory, drives the legend overlay
  let storyScrollStep = 0;
  $: legendSplit = storyScrollStep >= 2;


  $: allNeighborhoods = geoData
    ? geoData.features.map(f => f.properties.name).sort()
    : [];

  // Drive map focus from current neighborhood
  $: mapFocusNeighborhood = $currentNeighborhood;

  // Keyboard navigation
  function handleKeydown(e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); nextNeighborhood(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prevNeighborhood(); }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<div class="deep-dive">
  <button class="deep-dive-back" on:click={() => dispatch('back')}>&larr; Back to overview</button>

  <!-- Eviction-case legend, pinned bottom-left. Starts as a single
       "eviction count" row; when the user scrolls to "Who's Filing These?"
       the corporate-landlord row and size key fade in smoothly. -->
  <aside class="dot-legend-overlay" class:expanded={legendSplit}>
    <div class="legend-title">Eviction cases</div>

    <div class="legend-row">
      <span class="legend-swatch individual"></span>
      <span class="legend-label">
        <span class="label-variant" class:active={!legendSplit}>Eviction count</span>
        <span class="label-variant" class:active={legendSplit}>Individual landlord</span>
      </span>
    </div>

    <div class="extra">
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
    </div>
  </aside>

  <div class="deep-dive-panel">
    <NeighborhoodNav />

    <div class="rent-slider">
      <div class="rent-slider-header">
        <span class="rent-slider-label">My budget</span>
        <span class="rent-slider-value">${maxRent.toLocaleString()}/mo</span>
      </div>
      <input
        type="range"
        min={RENT_MIN}
        max={RENT_MAX}
        step={RENT_STEP}
        bind:value={maxRent}
        aria-label="Maximum monthly rent"
      />
      <div class="rent-slider-scale">
        <span>${RENT_MIN.toLocaleString()}</span>
        <span>${RENT_MAX.toLocaleString()}</span>
      </div>
    </div>

    <NeighborhoodStory
      neighborhood={$currentNeighborhood}
      {geoData}
      {properties}
      {maxRent}
      {zoriData}
      {evictionData}
      bind:mapMaxYear
      bind:mapUseCurrentRent
      bind:mapHighlightInvestors
      bind:mapHighlightEvictions
      bind:scrollStep={storyScrollStep}
    />

    <div class="explore-cta">
      <button class="explore-btn" on:click={() => dispatch('explore')}>
        Explore on Your Own
      </button>
    </div>
  </div>
</div>

<style>
  .deep-dive {
    position: relative;
    z-index: 10;
    margin-top: -100vh;
    height: 100vh;
    pointer-events: none;
  }

  .dot-legend-overlay {
    pointer-events: auto;
    position: absolute;
    bottom: 24px;
    left: 16px;
    z-index: 20;
    width: 240px;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.10);
    font-family: 'Inter', system-ui, sans-serif;
    transition: width 0.45s cubic-bezier(0.2, 0.9, 0.3, 1);
  }

  .dot-legend-overlay .extra {
    max-height: 0;
    opacity: 0;
    transform: translateY(-6px);
    overflow: hidden;
    transition:
      max-height 0.55s cubic-bezier(0.2, 0.9, 0.3, 1),
      opacity 0.4s ease 0.08s,
      transform 0.45s cubic-bezier(0.2, 0.9, 0.3, 1);
  }
  .dot-legend-overlay.expanded .extra {
    max-height: 160px;
    opacity: 1;
    transform: translateY(0);
  }

  .dot-legend-overlay .label-variant {
    display: inline-block;
    opacity: 0;
    transform: translateY(3px);
    transition: opacity 0.3s ease, transform 0.3s ease;
  }
  .dot-legend-overlay .label-variant.active {
    opacity: 1;
    transform: translateY(0);
  }
  .dot-legend-overlay .legend-label {
    position: relative;
    display: inline-grid;
  }
  .dot-legend-overlay .label-variant:not(.active) {
    grid-area: 1 / 1;
  }
  .dot-legend-overlay .label-variant.active {
    grid-area: 1 / 1;
  }
  .dot-legend-overlay .legend-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #555;
    margin-bottom: 8px;
  }
  .dot-legend-overlay .legend-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }
  .dot-legend-overlay .legend-swatch {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1.5px solid rgba(0, 0, 0, 0.25);
  }
  .dot-legend-overlay .legend-swatch.individual { background: #2563eb; }
  .dot-legend-overlay .legend-swatch.corporate { background: #e67e22; }
  .dot-legend-overlay .legend-label {
    font-size: 0.82rem;
    color: #333;
  }

  .dot-legend-overlay .legend-subtitle {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin-top: 10px;
    margin-bottom: 4px;
  }
  .dot-legend-overlay .size-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 2px 0 0;
  }
  .dot-legend-overlay .size-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
  }
  .dot-legend-overlay .size-swatch {
    display: inline-block;
    background: #666;
    border: 1px solid rgba(0, 0, 0, 0.25);
    border-radius: 50%;
    flex-shrink: 0;
  }
  .dot-legend-overlay .size-lbl {
    font-size: 0.66rem;
    color: #777;
  }

  .deep-dive-back {
    pointer-events: auto;
    position: absolute;
    top: 16px;
    left: 16px;
    z-index: 25;
    padding: 6px 12px;
    background: #f0f0f0;
    color: #555;
    border: 1px solid #d5d5d5;
    border-radius: 6px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  .deep-dive-back:hover { background: #e5e5e5; }

  .deep-dive-panel {
    pointer-events: auto;
    position: absolute;
    top: 0;
    right: 0;
    width: 420px;
    height: 100vh;
    background: rgba(255,255,255,0.97);
    border-left: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .rent-slider {
    padding: 12px 20px 14px;
    border-bottom: 1px solid #e0e0e0;
    background: #fafafa;
    flex-shrink: 0;
  }
  .rent-slider-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
  }
  .rent-slider-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #666;
  }
  .rent-slider-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: #111;
  }
  .rent-slider input[type="range"] {
    width: 100%;
    accent-color: #111;
  }
  .rent-slider-scale {
    display: flex;
    justify-content: space-between;
    font-size: 0.65rem;
    color: #999;
    margin-top: 2px;
  }

  .explore-cta {
    padding: 16px 24px;
    border-top: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .explore-btn {
    width: 100%;
    padding: 12px 20px;
    background: #2d8c2d;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  .explore-btn:hover {
    background: #236b23;
  }

  @media (max-width: 900px) {
    .deep-dive-panel {
      width: 100%;
      border-left: none;
    }
  }
</style>
