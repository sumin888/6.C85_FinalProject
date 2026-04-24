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
    pointer-events: none;
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
