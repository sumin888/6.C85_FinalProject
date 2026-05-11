<script context="module">
  // Module-scoped flag: persists for the page lifetime but resets on full
  // refresh. Used to honor the "don't show again" checkbox on the intro
  // popup without surviving a reload.
  let suppressIntroForSession = false;
</script>

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
  // Bound out: scroll-driven zoom progress (0 = wide Boston view with
  // neighborhood outlined, 1 = zoomed-in on neighborhood).
  export let mapZoomProgress = 0;

  // Scroll step inside NeighborhoodStory, drives the legend overlay.
  // Steps: 0 overview, 1 eviction overview, 2 who's filing,
  // 3 rent rising, 4 what's left.
  let storyScrollStep = 0;
  $: legendSplit = storyScrollStep >= 2;

  // Opens the global References modal
  export let openReferences = () => {};


  $: allNeighborhoods = geoData
    ? geoData.features.map(f => f.properties.name).sort()
    : [];

  // Drive map focus from current neighborhood
  $: mapFocusNeighborhood = $currentNeighborhood;

  // Intro popup: dim the map and point readers to the neighborhood
  // selector + rent slider. Re-shows every time the user enters the
  // deep-dive view (from the overview or from explore-on-your-own),
  // unless the user ticked "Don't show this again" earlier in the session.
  let showIntroPopup = true;
  let dontShowAgain = false;
  function closeIntro() {
    if (dontShowAgain) suppressIntroForSession = true;
    showIntroPopup = false;
  }
  function onIntroKey(e) {
    if (showIntroPopup && e.key === 'Escape') { e.preventDefault(); closeIntro(); }
  }

  // Keyboard navigation
  function handleKeydown(e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); nextNeighborhood(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prevNeighborhood(); }
  }

  onMount(() => {
    showIntroPopup = !suppressIntroForSession;
    dontShowAgain = false;
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('keydown', onIntroKey);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('keydown', onIntroKey);
    };
  });
</script>

<div class="deep-dive">
  <button class="deep-dive-back" on:click={() => dispatch('back')}>&larr; Back to overview</button>

  {#if showIntroPopup}
    <div class="intro-backdrop" on:click={closeIntro} aria-hidden="true"></div>
    <div
      class="intro-popup"
      role="dialog"
      aria-modal="true"
      aria-label="Welcome to the neighborhoods"
      on:click|stopPropagation
    >
      <button class="intro-close" on:click={closeIntro} aria-label="Close">×</button>
      <div class="intro-eyebrow">Explore Neighborhoods</div>
      <p class="intro-body">
        Here are six neighborhoods that exemplify the effect of corporate
        ownership on rental prices. Feel free to move between the
        neighborhoods on the upper right, and use the <strong>My Budget</strong>
        slider to put in your desired rental budget.
      </p>
      <p class="intro-body intro-dot-hint">
        On the maps that follow, <span class="intro-dot blue"></span>
        <strong>dots</strong> represent eviction filings.
      </p>
      <p class="intro-caveat">
        <strong>Note:</strong> Per-unit rents we'll show later are
        <em>estimates</em>, not pulled from actual leases — they're
        interpolated using <strong>ZORI</strong>, Zillow's Observed Rent
        Index, which tracks market rent over time.
      </p>
      <div class="intro-footer">
        <label class="intro-checkbox">
          <input type="checkbox" bind:checked={dontShowAgain} />
          <span>Don't show this again</span>
        </label>
        <button class="intro-cta" on:click={closeIntro}>Got it</button>
      </div>
    </div>
  {/if}

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

    <div class="legend-footnote">
      <span>Built from MAPC sales · MA Trial Court evictions · Boston assessment rolls · Zillow ZORI · BPDA + Census.</span>
      <button class="legend-refs-link" on:click={openReferences}>
        See full references ↗
      </button>
    </div>
  </aside>

  <div class="deep-dive-panel">
    <div class="nav-wrap" class:spotlight={showIntroPopup}>
      <NeighborhoodNav />
    </div>

    <div class="rent-slider" class:spotlight={showIntroPopup}>
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
      bind:mapZoomProgress
      {openReferences}
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
    max-height: 40px;
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

  .dot-legend-overlay .legend-footnote {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #eee;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .dot-legend-overlay .legend-footnote span {
    font-size: 0.66rem;
    color: #999;
    line-height: 1.45;
    font-style: italic;
  }
  .dot-legend-overlay .legend-refs-link {
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
  .dot-legend-overlay .legend-refs-link:hover { color: #1d4dbf; }

  .intro-backdrop {
    pointer-events: auto;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 420px; /* leave the sidebar visible/undimmed */
    background: rgba(15, 15, 15, 0.55);
    backdrop-filter: blur(1px);
    z-index: 40;
    animation: introFade 220ms ease both;
  }
  .intro-popup {
    pointer-events: auto;
    position: absolute;
    top: 50%;
    left: calc((100% - 420px) / 2);
    transform: translate(-50%, -50%);
    z-index: 50;
    width: min(460px, calc(100% - 460px));
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.30);
    padding: 24px 28px 22px;
    font-family: 'Inter', system-ui, sans-serif;
    animation: introScale 220ms cubic-bezier(0.2, 0.9, 0.3, 1) both;
  }
  .intro-close {
    position: absolute;
    top: 10px;
    right: 12px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: #f0f0f0;
    color: #555;
    font-size: 1.2rem;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .intro-close:hover { background: #e0e0e0; color: #111; }
  .intro-eyebrow {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2d8c2d;
    margin-bottom: 6px;
  }
  .intro-body {
    font-size: 0.92rem;
    color: #333;
    line-height: 1.6;
    margin: 0 0 16px;
  }
  .intro-body strong { color: #1a1a1a; font-weight: 700; }
  .intro-dot-hint { margin-top: -6px; }
  .intro-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    vertical-align: middle;
    margin: 0 2px 1px;
    border: 1px solid rgba(0, 0, 0, 0.2);
  }
  .intro-dot.blue { background: #2563eb; }
  .intro-caveat {
    margin: 0 0 16px;
    padding: 9px 12px;
    background: #fafafa;
    border-left: 3px solid #bbb;
    border-radius: 4px;
    font-size: 0.78rem;
    color: #555;
    line-height: 1.55;
  }
  .intro-caveat strong { color: #1a1a1a; font-weight: 700; }
  .intro-caveat em { color: #444; font-style: italic; font-weight: 600; }
  .intro-cta {
    background: #2d8c2d;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s;
  }
  .intro-cta:hover { background: #236b23; }

  .intro-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
  }
  .intro-checkbox {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    color: #555;
    cursor: pointer;
    user-select: none;
  }
  .intro-checkbox input {
    width: 14px;
    height: 14px;
    accent-color: #2d8c2d;
    cursor: pointer;
  }
  .intro-checkbox:hover { color: #1a1a1a; }

  /* Highlight the < / > arrows in the nav and the budget slider while the
     intro popup is open. Both sit in the sidebar (already undimmed) and
     gain a pulsing green glow. */
  .nav-wrap { position: relative; }
  .nav-wrap.spotlight :global(.nav-arrow) {
    position: relative;
    z-index: 45;
    border-color: #2d8c2d !important;
    color: #2d8c2d !important;
    box-shadow:
      0 0 0 3px rgba(45, 140, 45, 0.55),
      0 0 22px rgba(45, 140, 45, 0.35);
    animation: spotlightPulse 1.8s ease-in-out infinite alternate;
  }
  .rent-slider.spotlight {
    position: relative;
    z-index: 45;
    box-shadow:
      0 0 0 3px rgba(45, 140, 45, 0.55),
      0 0 22px rgba(45, 140, 45, 0.35);
    border-radius: 8px;
    animation: spotlightPulse 1.8s ease-in-out infinite alternate;
  }
  @keyframes spotlightPulse {
    from { box-shadow: 0 0 0 3px rgba(45, 140, 45, 0.45), 0 0 14px rgba(45, 140, 45, 0.25); }
    to   { box-shadow: 0 0 0 3px rgba(45, 140, 45, 0.70), 0 0 30px rgba(45, 140, 45, 0.50); }
  }
  @keyframes introFade {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes introScale {
    from { opacity: 0; transform: translate(-50%, -50%) scale(0.96); }
    to   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
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
