<script>
  import { onMount, tick } from 'svelte';
  import { filterProperties } from '../lib/data.js';
  import { stories } from '../lib/neighborhoodStories.js';
  import StatCard from './StatCard.svelte';
  import ZoriTrendChart from './ZoriTrendChart.svelte';
  import EvictionBreakdown from './EvictionBreakdown.svelte';

  export let neighborhood;
  export let geoData;
  export let properties;
  export let maxRent;
  export let zoriData;
  export let evictionData;

  // Map control outputs
  export let mapMaxYear = 2022;
  export let mapUseCurrentRent = false;
  export let mapHighlightInvestors = false;
  export let mapHighlightEvictions = false;

  let scrollStep = 0;
  let panelEl;

  $: story = stories[neighborhood] ?? {};
  $: feature = geoData?.features.find(f => f.properties.name === neighborhood);
  $: sp = feature?.properties ?? {};
  $: zori = zoriData?.[neighborhood] ?? [];
  $: eviction = evictionData?.[neighborhood] ?? null;
  $: hoodProps = properties.filter(p => p.neighborhood === neighborhood);
  $: investorProps = hoodProps.filter(p => p.investor_buyer);
  $: investorPct = hoodProps.length > 0 ? ((investorProps.length / hoodProps.length) * 100).toFixed(0) : '0';
  $: affordableOld = hoodProps.filter(p => p.monthly_rent <= maxRent).length;
  $: affordableNow = hoodProps.filter(p => p.monthly_rent_now <= maxRent).length;
  $: lostHere = affordableOld - affordableNow;

  // Drive map state from scroll step (now 4 steps: 0=rent+afford, 1=ownership, 2=eviction, 3=what's left)
  $: {
    mapMaxYear = 2022;
    mapUseCurrentRent = scrollStep >= 3;
    mapHighlightInvestors = scrollStep >= 1;
    mapHighlightEvictions = scrollStep >= 2;
  }

  function setupScroll() {
    if (!panelEl) return;
    const steps = panelEl.querySelectorAll('.story-step');
    if (steps.length === 0) return;

    function onScroll() {
      const panelRect = panelEl.getBoundingClientRect();
      const mid = panelRect.top + panelRect.height / 2;
      let active = 0;
      for (const el of steps) {
        const rect = el.getBoundingClientRect();
        if (rect.top < mid && rect.bottom > mid) {
          active = parseInt(el.dataset.step, 10);
          break;
        }
      }
      scrollStep = active;
    }

    panelEl.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => panelEl.removeEventListener('scroll', onScroll);
  }

  $: if (neighborhood && panelEl) {
    scrollStep = 0;
    panelEl.scrollTop = 0;
    tick().then(setupScroll);
  }

  onMount(() => {
    if (panelEl) return setupScroll();
  });
</script>

<div class="story-panel" bind:this={panelEl}>
  <!-- Step 0: Rent trend + Affordability (merged) -->
  <div class="story-step" data-step="0">
    <div class="story-card" class:active={scrollStep === 0}>
      <h3>Rent & Affordability in {neighborhood}</h3>
      <p>{@html story.rentAndAffordability ?? ''}</p>
      <div class="stat-grid">
        <StatCard value="{sp.count?.toLocaleString() ?? '—'}" label="rental properties" />
        <StatCard value="${sp.median_rent?.toLocaleString() ?? '—'}/mo" label="median rent" color="accent" />
        {#if affordableOld > 0}
          <StatCard value="{affordableOld} → {affordableNow}" label="affordable at your budget" color={lostHere > 0 ? 'red' : 'accent'} />
        {/if}
      </div>
      {#if zori.length > 0}
        <ZoriTrendChart data={zori} highlightYear={2018} />
      {/if}
    </div>
  </div>

  <!-- Step 1: Who owns it -->
  <div class="story-step" data-step="1">
    <div class="story-card" class:active={scrollStep === 1}>
      <h3>Who Owns {neighborhood}?</h3>
      <p>{@html story.ownership ?? ''}</p>
      <div class="stat-grid">
        <StatCard value="{investorPct}%" label="investor-purchased" color="orange" />
        <StatCard value="{sp.avg_corp_own_rate != null ? (sp.avg_corp_own_rate * 100).toFixed(1) + '%' : 'N/A'}" label="corporate ownership" color="orange" />
        <StatCard value="{sp.avg_own_occ_rate != null ? (sp.avg_own_occ_rate * 100).toFixed(1) + '%' : 'N/A'}" label="owner-occupied" />
      </div>
    </div>
  </div>

  <!-- Step 2: Eviction patterns -->
  <div class="story-step" data-step="2">
    <div class="story-card" class:active={scrollStep === 2}>
      <h3>Eviction in {neighborhood}</h3>
      <p>{@html story.eviction ?? ''}</p>
      {#if eviction}
        <div class="stat-grid">
          <StatCard value="{eviction.total_filings.toLocaleString()}" label="eviction filings" color="red" />
          <StatCard value="{(eviction.corp_rate * 100).toFixed(0)}%" label="by corporate landlords" color="red" />
        </div>
        <EvictionBreakdown data={eviction} />
      {/if}
    </div>
  </div>

  <!-- Step 3: What's affordable now -->
  <div class="story-step" data-step="3">
    <div class="story-card" class:active={scrollStep === 3}>
      <h3>What's Left in {neighborhood}?</h3>
      <p>{@html story.whatsLeft ?? ''}</p>
      <div class="stat-grid">
        <StatCard value="{affordableOld}" label="affordable 5 years ago" color="accent" />
        <StatCard value="{affordableNow}" label="affordable now" color={affordableNow < affordableOld ? 'red' : 'accent'} />
        {#if lostHere > 0}
          <StatCard value="-{lostHere}" label="units lost" color="red" />
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .story-panel {
    height: 100vh;
    overflow-y: auto;
    overscroll-behavior: contain;
    scroll-snap-type: y proximity;
    flex: 1;
  }

  .story-step {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 24px;
    scroll-snap-align: start;
  }

  .story-step:first-child {
    align-items: flex-start;
    padding-top: 20px;
  }

  .story-card {
    background: #fff;
    max-width: 400px;
    width: 100%;
    padding: 28px 24px;
    border-radius: 10px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    border: 1px solid #e0e0e0;
    opacity: 0.5;
    transform: translateY(8px);
    transition: opacity 0.35s ease, transform 0.35s ease;
  }

  .story-card.active {
    opacity: 1;
    transform: translateY(0);
  }

  .story-card h3 {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 10px;
  }

  .story-card :global(p) {
    font-size: 0.85rem;
    color: #444;
    line-height: 1.7;
  }

  .story-card :global(strong) {
    color: #2d8c2d;
    font-weight: 600;
  }

  .stat-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 20px;
    margin-top: 12px;
  }
</style>
