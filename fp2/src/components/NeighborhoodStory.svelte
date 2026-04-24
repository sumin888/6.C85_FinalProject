<script>
  import { onMount, tick } from 'svelte';
  import { filterProperties } from '../lib/data.js';
  import { stories } from '../lib/neighborhoodStories.js';
  import StatCard from './StatCard.svelte';
  import ZoriTrendChart from './ZoriTrendChart.svelte';
  import DonutChart from './DonutChart.svelte';

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

  // Neighborhood rent increase (ZORI start → latest)
  $: rentStart = zori.length ? zori[0].rent : null;
  $: rentEnd = zori.length ? zori[zori.length - 1].rent : null;
  $: hoodRentIncPct = rentStart && rentEnd ? ((rentEnd / rentStart) - 1) * 100 : null;

  // Citywide avg ZORI increase over the same period
  $: cityRentIncPct = (() => {
    if (!zoriData) return null;
    const pcts = [];
    for (const h in zoriData) {
      const arr = zoriData[h];
      if (Array.isArray(arr) && arr.length > 1 && arr[0].rent && arr[arr.length - 1].rent) {
        pcts.push((arr[arr.length - 1].rent / arr[0].rent - 1) * 100);
      }
    }
    return pcts.length ? pcts.reduce((a, b) => a + b, 0) / pcts.length : null;
  })();

  // BLS CPI inflation, 2016 → 2024 for Boston-Cambridge-Newton: ≈ 29% cumulative
  const CPI_INC_PCT = 29;

  // Corporate "over-filing" = corp filing rate − corp ownership rate (positive = corps file disproportionately)
  $: corpFileRate = eviction?.corp_rate != null ? eviction.corp_rate * 100 : null;
  $: corpOwnRate = sp?.avg_corp_own_rate != null ? sp.avg_corp_own_rate * 100 : null;
  $: corpOverfile = corpFileRate != null && corpOwnRate != null ? corpFileRate - corpOwnRate : null;

  // Dominant case type (non-payment in most neighborhoods)
  $: dominantCause = (() => {
    if (!eviction?.case_types) return null;
    const entries = Object.entries(eviction.case_types);
    if (!entries.length) return null;
    entries.sort((a, b) => b[1] - a[1]);
    const [name, count] = entries[0];
    const total = entries.reduce((s, [, v]) => s + v, 0);
    return { name, count, pct: total ? (count / total) * 100 : 0 };
  })();

  // Donut-chart slices for eviction cause breakdown
  const CAUSE_PALETTE = ['#c0392b', '#e67e22', '#f1c40f', '#95a5a6', '#7f8c8d'];
  $: causeSlices = (() => {
    if (!eviction?.case_types) return [];
    const entries = Object.entries(eviction.case_types).sort((a, b) => b[1] - a[1]);
    const top = entries.slice(0, 4);
    const rest = entries.slice(4).reduce((s, [, v]) => s + v, 0);
    const out = top.map(([label, value], i) => ({ label, value, color: CAUSE_PALETTE[i] }));
    if (rest > 0) out.push({ label: 'Other', value: rest, color: CAUSE_PALETTE[CAUSE_PALETTE.length - 1] });
    return out;
  })();

  // Corporate-filing vs corporate-ownership donut (for step 2)
  $: corpFilingSlices = corpFileRate != null ? [
    { label: 'Corporate landlord', value: corpFileRate, color: '#e67e22' },
    { label: 'Individual landlord', value: 100 - corpFileRate, color: '#2563eb' },
  ] : [];

  // Drive map state from scroll step
  // 0=neighborhood overview, 1=general eviction (all green), 2=corp ownership+filing (red),
  // 3=rent above market, 4=what's left
  $: {
    mapMaxYear = 2022;
    mapUseCurrentRent = scrollStep >= 3;
    mapHighlightInvestors = scrollStep >= 2;  // turn dots red (corp) at step 2
    mapHighlightEvictions = false;
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
  <!-- Step 0: Neighborhood overview -->
  <div class="story-step" data-step="0">
    <div class="story-card" class:active={scrollStep === 0}>
      <h3>{neighborhood}</h3>
      <div class="overview-meta">
        {#if sp.median_rent}
          <div class="meta-item">
            <span class="meta-num">${sp.median_rent.toLocaleString()}</span>
            <span class="meta-lbl">median rent /mo</span>
          </div>
        {/if}
        {#if hoodRentIncPct != null}
          <div class="meta-item">
            <span class="meta-num red">+{hoodRentIncPct.toFixed(0)}%</span>
            <span class="meta-lbl">rent since 2016</span>
          </div>
        {/if}
      </div>
      <p>{@html story.overview ?? ''}</p>
      <div class="scroll-hint">Keep scrolling ↓</div>
    </div>
  </div>

  <!-- Step 1: General eviction — blue dots, overall picture -->
  <div class="story-step" data-step="1">
    <div class="story-card" class:active={scrollStep === 1}>
      <h3>Eviction in {neighborhood}</h3>
      <p class="lede">
        Each <span class="inline-dot blue"></span> <strong class="blue-txt">blue dot</strong>
        on the map is one eviction case filed here, 2020–2024.
      </p>
      {#if eviction}
        <div class="headline-stat">
          <span class="headline-num red">{eviction.total_filings.toLocaleString()}</span>
          <span class="headline-lbl">total eviction filings</span>
        </div>
        {#if causeSlices.length > 0 && dominantCause}
          <div class="viz-caption">Cause of eviction</div>
          <DonutChart
            slices={causeSlices}
            size={150}
            thickness={26}
            centerValue="{Math.round(dominantCause.pct)}%"
            centerLabel="non-payment"
          />
        {/if}
      {/if}
    </div>
  </div>

  <!-- Step 2: Corporate ownership → corporate filings -->
  <div class="story-step" data-step="2">
    <div class="story-card" class:active={scrollStep === 2}>
      <h3>Who's Filing These?</h3>
      <p class="lede">
        Dots now <span class="inline-dot orange"></span> <strong class="orange-txt">orange</strong>
        where the filer is a <strong>corporate landlord</strong>.
      </p>

      {#if corpFileRate != null}
        <div class="viz-caption">Who filed the evictions</div>
        <div class="stacked-pct">
          <div class="stk-seg orange" style="width:{Math.max(corpFileRate, 12)}%">
            <span>{corpFileRate.toFixed(0)}%</span>
          </div>
          <div class="stk-seg blue" style="width:{Math.max(100 - corpFileRate, 12)}%">
            <span>{(100 - corpFileRate).toFixed(0)}%</span>
          </div>
        </div>
        <div class="stacked-labels">
          <span><span class="dot-inline orange-sw"></span> Corporate landlord</span>
          <span><span class="dot-inline blue-sw"></span> Individual landlord</span>
        </div>
      {/if}

      {#if corpFileRate != null && corpOwnRate != null}
        <div class="viz-caption">Own vs. file</div>
        <div class="corp-bars">
          <div class="corp-bar-row">
            <div class="corp-bar-lbl">Own</div>
            <div class="corp-bar-track">
              <div class="corp-bar-fill orange" style="width:{Math.min(corpOwnRate, 100)}%"></div>
            </div>
            <div class="corp-bar-val orange">{corpOwnRate.toFixed(0)}%</div>
          </div>
          <div class="corp-bar-row">
            <div class="corp-bar-lbl">File</div>
            <div class="corp-bar-track">
              <div class="corp-bar-fill orange" style="width:{Math.min(corpFileRate, 100)}%"></div>
            </div>
            <div class="corp-bar-val orange">{corpFileRate.toFixed(0)}%</div>
          </div>
        </div>
        {#if corpOverfile > 5}
          <div class="multiplier orange">
            Corps file at
            <strong class="big orange-txt">{(corpFileRate / corpOwnRate).toFixed(1)}×</strong>
            their ownership share.
          </div>
        {/if}
      {/if}
    </div>
  </div>

  <!-- Step 3: Rent rising above the market — driven by corporate owners -->
  <div class="story-step" data-step="3">
    <div class="story-card" class:active={scrollStep === 3}>
      <h3>The Rent Behind the Filings</h3>
      {#if hoodRentIncPct != null}
        {@const vsCity = cityRentIncPct != null ? hoodRentIncPct - cityRentIncPct : null}
        {@const vsCPI = hoodRentIncPct - CPI_INC_PCT}
        <div class="rent-compare-bars">
          <div class="rcb-row highlight">
            <div class="rcb-lbl">{neighborhood}</div>
            <div class="rcb-track">
              <div class="rcb-fill red" style="width:{Math.min(hoodRentIncPct, 100)}%"></div>
            </div>
            <div class="rcb-val red">+{hoodRentIncPct.toFixed(0)}%</div>
          </div>
          {#if cityRentIncPct != null}
            <div class="rcb-row">
              <div class="rcb-lbl">Boston avg</div>
              <div class="rcb-track">
                <div class="rcb-fill neutral" style="width:{Math.min(cityRentIncPct, 100)}%"></div>
              </div>
              <div class="rcb-val">+{cityRentIncPct.toFixed(0)}%</div>
            </div>
          {/if}
          <div class="rcb-row">
            <div class="rcb-lbl">Inflation</div>
            <div class="rcb-track">
              <div class="rcb-fill neutral" style="width:{Math.min(CPI_INC_PCT, 100)}%"></div>
            </div>
            <div class="rcb-val">+{CPI_INC_PCT}%</div>
          </div>
        </div>
        {#if vsCity != null && vsCity > 0}
          <div class="multiplier">
            <strong class="big red-txt">+{vsCity.toFixed(0)} pts</strong>
            above the citywide average.
          </div>
        {:else if vsCPI > 0}
          <div class="multiplier">
            <strong class="big red-txt">+{vsCPI.toFixed(0)} pts</strong>
            above inflation.
          </div>
        {/if}
      {/if}
      {#if zori.length > 0}
        <ZoriTrendChart data={zori} highlightYear={2018} />
      {/if}
    </div>
  </div>

  <!-- Step 4: What's left — affordability at the user's budget -->
  <div class="story-step" data-step="4">
    <div class="story-card" class:active={scrollStep === 4}>
      <h3>What's Left in {neighborhood}?</h3>
      <p class="lede">
        At your budget of <strong>${maxRent.toLocaleString()}/mo</strong>:
      </p>
      <div class="before-after">
        <div class="ba-col">
          <div class="ba-num accent">{affordableOld.toLocaleString()}</div>
          <div class="ba-lbl">Affordable<br/>5 years ago</div>
        </div>
        <div class="ba-arrow">→</div>
        <div class="ba-col">
          <div class="ba-num" class:red={affordableNow < affordableOld} class:accent={affordableNow >= affordableOld}>
            {affordableNow.toLocaleString()}
          </div>
          <div class="ba-lbl">Affordable<br/>today</div>
        </div>
      </div>
      {#if lostHere > 0}
        <div class="multiplier">
          <strong class="big red-txt">−{lostHere.toLocaleString()}</strong>
          {lostHere === 1 ? 'unit' : 'units'} priced out.
        </div>
      {:else if affordableOld === 0}
        <div class="multiplier muted">
          Nothing was affordable at this budget.
        </div>
      {:else}
        <div class="multiplier">
          All {affordableOld.toLocaleString()} still fit your budget.
        </div>
      {/if}
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
    color: #1a1a1a;
    font-weight: 700;
  }

  .budget-line {
    margin-top: 8px;
    padding: 8px 10px;
    background: #fafafa;
    border-left: 3px solid #2d8c2d;
    border-radius: 4px;
    font-size: 0.82rem !important;
  }
  .budget-line :global(strong.lost-text) {
    color: #c0392b !important;
  }

  .stat-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 20px;
    margin-top: 12px;
  }

  .dot-legend {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    margin: 0 0 12px;
    background: #fafafa;
    border: 1px solid #ececec;
    border-radius: 8px;
  }
  .dot-legend.subtle { background: #f7f7f7; }
  .dot-legend-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.78rem;
    color: #444;
    line-height: 1.4;
  }
  .dot-legend .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 1px solid rgba(0, 0, 0, 0.15);
  }
  .dot-legend .dot.red { background: #c0392b; }
  .dot-legend .dot.blue { background: #2563eb; }
  .dot-legend .dot.green { background: #2d8c2d; }
  .dot-legend strong { color: #1a1a1a; font-weight: 700; }

  .correlation-card, .benchmark-card {
    margin: 12px 0;
    padding: 12px 14px;
    background: #fffafa;
    border: 1px solid #f0d9d5;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .corr-row, .bench-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    font-size: 0.78rem;
    color: #555;
  }
  .bench-row.top {
    padding-bottom: 4px;
    border-bottom: 1px dashed #e8d2cd;
    font-size: 0.82rem;
  }
  .corr-lbl, .bench-lbl { color: #666; }
  .corr-val, .bench-val {
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .corr-val.red, .bench-val.red { color: #c0392b; }
  .corr-val.neutral { color: #666; }
  .bench-val.muted { color: #999; }
  .corr-note, .bench-note {
    margin-top: 6px;
    padding-top: 8px;
    border-top: 1px solid #f0d9d5;
    font-size: 0.78rem !important;
    line-height: 1.55;
    color: #444;
  }
  .red-txt { color: #c0392b !important; font-weight: 700; }

  .lede {
    font-size: 0.85rem !important;
    color: #333 !important;
    margin-bottom: 12px;
  }
  .inline-dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin: 0 1px 1px;
    vertical-align: middle;
    border: 1px solid rgba(0,0,0,0.2);
  }
  .inline-dot.green { background: #2d8c2d; }
  .inline-dot.blue { background: #2563eb; }
  .inline-dot.red { background: #c0392b; }
  .inline-dot.orange { background: #e67e22; }
  .blue-txt { color: #2563eb !important; font-weight: 700; }
  .orange-txt { color: #e67e22 !important; font-weight: 700; }

  .scroll-hint {
    margin-top: 18px;
    text-align: center;
    font-size: 0.78rem;
    font-weight: 600;
    color: #888;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    animation: bounceDown 1.6s ease-in-out infinite;
  }
  @keyframes bounceDown {
    0%, 100% { transform: translateY(0); opacity: 0.7; }
    50% { transform: translateY(4px); opacity: 1; }
  }

  .headline-stat {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 8px 0 14px;
  }
  .headline-num {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
  }
  .headline-num.red { color: #c0392b; }
  .headline-lbl { font-size: 0.78rem; color: #666; }

  .viz-caption {
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin: 14px 0 4px;
  }

  .stacked-pct {
    display: flex;
    width: 100%;
    height: 26px;
    border-radius: 6px;
    overflow: hidden;
    margin: 2px 0 6px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }
  .stk-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 700;
    color: #fff;
    transition: width 0.4s ease;
    min-width: 0;
  }
  .stk-seg span {
    white-space: nowrap;
    text-shadow: 0 1px 1px rgba(0,0,0,0.2);
  }
  .stk-seg.red { background: #c0392b; }
  .stk-seg.blue { background: #2563eb; }
  .stk-seg.green { background: #2d8c2d; }
  .stk-seg.orange { background: #e67e22; }
  .stacked-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #555;
    margin-bottom: 8px;
  }
  .stacked-labels .dot-inline {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin-right: 4px;
    vertical-align: middle;
  }
  .red-sw { background: #c0392b; }
  .blue-sw { background: #2563eb; }
  .green-sw { background: #2d8c2d; }
  .orange-sw { background: #e67e22; }

  .multiplier {
    margin-top: 10px;
    padding: 10px 12px;
    background: #fffafa;
    border-left: 3px solid #c0392b;
    border-radius: 4px;
    font-size: 0.85rem;
    color: #333;
    line-height: 1.4;
  }
  .multiplier.muted {
    background: #fafafa;
    border-left-color: #aaa;
    color: #666;
  }
  .multiplier.orange {
    background: #fff7ee;
    border-left-color: #e67e22;
  }
  .multiplier .big {
    font-size: 1.2rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
  }

  .corp-bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 10px 0 8px;
  }
  .corp-bar-row {
    display: grid;
    grid-template-columns: 40px 1fr 44px;
    gap: 10px;
    align-items: center;
    font-size: 0.75rem;
    color: #555;
  }
  .corp-bar-lbl { line-height: 1.2; }
  .corp-bar-lbl strong { color: #1a1a1a; font-weight: 700; }
  .corp-bar-track {
    height: 12px;
    background: #eee;
    border-radius: 6px;
    overflow: hidden;
  }
  .corp-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
  }
  .corp-bar-fill.neutral { background: #9aa3ad; }
  .corp-bar-fill.orange { background: #e67e22; }
  .corp-bar-fill.red { background: #c0392b; }
  .corp-bar-val {
    font-weight: 700;
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #444;
  }
  .corp-bar-val.red { color: #c0392b; }
  .corp-bar-val.orange { color: #e67e22; }

  .overview-meta {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    padding: 12px 14px;
    margin: 4px 0 14px;
    background: #f7f9f7;
    border: 1px solid #e4ebe4;
    border-radius: 8px;
  }
  .meta-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 72px;
  }
  .meta-num {
    font-size: 1.1rem;
    font-weight: 800;
    color: #1a1a1a;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .meta-num.red { color: #c0392b; }
  .meta-lbl {
    font-size: 0.66rem;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .rent-compare-bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 8px 0 6px;
  }
  .rcb-row {
    display: grid;
    grid-template-columns: 80px 1fr 56px;
    gap: 10px;
    align-items: center;
    font-size: 0.76rem;
    color: #666;
  }
  .rcb-row.highlight .rcb-lbl { color: #1a1a1a; font-weight: 700; }
  .rcb-lbl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rcb-track {
    height: 14px;
    background: #eee;
    border-radius: 7px;
    overflow: hidden;
  }
  .rcb-fill {
    height: 100%;
    border-radius: 7px;
    transition: width 0.4s ease;
  }
  .rcb-fill.red { background: #c0392b; }
  .rcb-fill.neutral { background: #9aa3ad; }
  .rcb-val {
    font-weight: 700;
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #555;
  }
  .rcb-val.red { color: #c0392b; }

  .before-after {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 10px;
    padding: 14px 10px;
    margin: 6px 0 4px;
    background: #fafafa;
    border: 1px solid #ececec;
    border-radius: 8px;
  }
  .ba-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    text-align: center;
  }
  .ba-num {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .ba-num.accent { color: #2d8c2d; }
  .ba-num.red { color: #c0392b; }
  .ba-lbl {
    font-size: 0.7rem;
    color: #777;
    line-height: 1.3;
  }
  .ba-arrow {
    font-size: 1.5rem;
    color: #aaa;
    font-weight: 300;
  }

  .corr-note.standalone {
    margin: 0 0 12px;
    padding: 10px 12px;
    background: #fffafa;
    border: 1px solid #f0d9d5;
    border-top: 1px solid #f0d9d5;
    border-radius: 8px;
  }
</style>
