<script>
  // Sale-flow comparison: one row per flow direction, each with a "then" bar
  // (baseline year) and a "now" bar (latest year), plus a growth multiplier.
  // Bars are scaled so the largest value across all rows fills the track.
  export let flows = [];         // [{label, color, then, now}]  rates in [0,1]
  export let baselineYear = null;
  export let latestYear = null;
  export let progress = 1;       // 0–1 for reveal
  export let width = 520;

  $: maxVal = flows.reduce((m, f) => Math.max(m, f.then || 0, f.now || 0), 0) || 1;
  $: visibleCount = Math.max(1, Math.ceil(flows.length * progress));
  $: visibleFlows = flows.slice(0, visibleCount);
</script>

<div class="flowbars" style="width:{width}px">
  <div class="fb-head">
    <span class="fb-col label"></span>
    <span class="fb-col col-then">{baselineYear ?? 'baseline'}</span>
    <span class="fb-col col-now">{latestYear ?? 'latest'}</span>
    <span class="fb-col col-mult">change</span>
  </div>

  {#each visibleFlows as f}
    {@const thenPct = (f.then || 0) * 100}
    {@const nowPct = (f.now || 0) * 100}
    {@const thenWidth = (f.then || 0) / maxVal * 100}
    {@const nowWidth = (f.now || 0) / maxVal * 100}
    {@const mult = f.then > 0 ? f.now / f.then : null}
    {@const isGrowth = mult != null && mult > 1.02}
    {@const isShrink = mult != null && mult < 0.98}
    <div class="fb-row">
      <div class="fb-col label">
        <span class="swatch" style="background:{f.color}"></span>
        <span class="lbl">{f.label}</span>
      </div>
      <div class="fb-col bar-cell">
        <div class="bar-track">
          <div class="bar then" style="width:{thenWidth}%; background:{f.color}"></div>
        </div>
        <span class="bar-pct">{thenPct.toFixed(1)}%</span>
      </div>
      <div class="fb-col bar-cell">
        <div class="bar-track">
          <div class="bar now" style="width:{nowWidth}%; background:{f.color}"></div>
        </div>
        <span class="bar-pct strong">{nowPct.toFixed(1)}%</span>
      </div>
      <div class="fb-col col-mult">
        {#if mult != null}
          <span class="mult" class:grow={isGrowth} class:shrink={isShrink}>
            {isGrowth ? '▲' : isShrink ? '▼' : '—'} {mult.toFixed(1)}×
          </span>
        {:else}
          <span class="mult">—</span>
        {/if}
      </div>
    </div>
  {/each}
</div>

<style>
  .flowbars {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    background: #fff;
    padding: 16px 18px;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
  }
  .fb-head, .fb-row {
    display: grid;
    grid-template-columns: 1.2fr 2.2fr 2.2fr 0.8fr;
    gap: 12px;
    align-items: center;
  }
  .fb-head {
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    padding-bottom: 4px;
    border-bottom: 1px solid #eee;
  }
  .col-then, .col-now, .col-mult {
    text-align: center;
  }

  .fb-row {
    font-size: 0.8rem;
  }
  .label {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .lbl {
    font-weight: 600;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bar-cell {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .bar-track {
    flex: 1;
    height: 14px;
    background: #f1f1f1;
    border-radius: 7px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    border-radius: 7px;
    transition: width 0.6s ease;
  }
  .bar.then { opacity: 0.55; }
  .bar.now { opacity: 1; }
  .bar-pct {
    font-variant-numeric: tabular-nums;
    font-size: 0.74rem;
    color: #666;
    min-width: 44px;
    text-align: right;
  }
  .bar-pct.strong { color: #1a1a1a; font-weight: 700; }

  .mult {
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    font-size: 0.85rem;
    color: #888;
    text-align: center;
    display: inline-block;
  }
  .mult.grow { color: #e67e22; }
  .mult.shrink { color: #2563eb; }
</style>
