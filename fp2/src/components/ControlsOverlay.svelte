<script>
  export let maxRent;
  export let affordableCount = 0;
  export let affordablePct = '0.0';
  export let visibleCount = 0;
  export let summaryLabel = '';
  export let lostCount = 0;
  export let showLost = false;
  export let highlightInvestors = false;
  export let highlightEvictions = false;
</script>

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

    <div class="affordability-summary">
      <div class="summary-stat">
        <span class="stat-value accent">{affordableCount.toLocaleString()}</span>
        <span class="stat-label">{summaryLabel}</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{affordablePct}%</span>
        <span class="stat-label">of {visibleCount.toLocaleString()} rental properties shown</span>
      </div>
      {#if showLost && lostCount > 0}
        <div class="summary-stat">
          <span class="stat-value lost">{lostCount.toLocaleString()}</span>
          <span class="stat-label">homes no longer affordable</span>
        </div>
      {/if}
    </div>

    <!-- Color legends -->
    <div class="rent-legend">
      <span class="legend-label">Individual Landlord Eviction (rent)</span>
      <div class="legend-bar-gradient">
        <div class="gradient-bar green"></div>
        <div class="gradient-labels"><span>Lower</span><span>Higher</span></div>
      </div>
    </div>
    {#if highlightInvestors}
      <div class="rent-legend" style="margin-top:2px; padding-top:6px;">
        <span class="legend-label">Corporate Landlord Eviction (rent)</span>
        <div class="legend-bar-gradient">
          <div class="gradient-bar orange"></div>
          <div class="gradient-labels"><span>Lower</span><span>Higher</span></div>
        </div>
      </div>
    {/if}
    {#if highlightEvictions}
      <div class="rent-legend" style="margin-top:2px; padding-top:6px;">
        <span class="legend-label">Eviction Filed (rent)</span>
        <div class="legend-bar-gradient">
          <div class="gradient-bar red"></div>
          <div class="gradient-labels"><span>Lower</span><span>Higher</span></div>
        </div>
      </div>
    {/if}

    <div class="size-legend">
      <span class="legend-label">Properties at Location</span>
      <div class="size-legend-row">
        <div class="size-dot-group"><span class="size-dot" style="width:6px;height:6px;"></span><span class="size-dot-label">1</span></div>
        <div class="size-dot-group"><span class="size-dot" style="width:12px;height:12px;"></span><span class="size-dot-label">5</span></div>
        <div class="size-dot-group"><span class="size-dot" style="width:18px;height:18px;"></span><span class="size-dot-label">20+</span></div>
      </div>
    </div>
  </section>

  <slot></slot>
</div>

<style>
  .controls-overlay {
    position: absolute;
    top: 16px;
    right: 16px;
    bottom: 16px;
    z-index: 30;
    width: 280px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    pointer-events: none;
    overflow: hidden;
  }
  .controls-overlay > :global(*) { pointer-events: auto; }
  .control-group { display: flex; flex-direction: column; gap: 10px; }
  .primary-control {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10);
  }
  .control-header { display: flex; justify-content: space-between; align-items: baseline; }
  .control-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #666; }
  .rent-display { font-size: 1.6rem; font-weight: 700; color: #2d8c2d; line-height: 1; }
  .rent-unit { font-size: 0.9rem; font-weight: 400; color: #666; }
  .rent-slider {
    -webkit-appearance: none; appearance: none; width: 100%; height: 4px; border-radius: 2px;
    background: linear-gradient(to right, #2d8c2d 0%, #2d8c2d var(--pct, 28.57%), #ddd var(--pct, 28.57%));
    outline: none; cursor: pointer;
  }
  .rent-slider::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%;
    background: #2d8c2d; border: 2px solid #fff; cursor: pointer; box-shadow: 0 0 6px rgba(45,140,45,0.4);
  }
  .rent-slider::-moz-range-thumb {
    width: 16px; height: 16px; border-radius: 50%; background: #2d8c2d; border: 2px solid #fff; cursor: pointer;
  }
  .slider-ticks { display: flex; justify-content: space-between; font-size: 0.65rem; color: #999; margin-top: -4px; }
  .affordability-summary { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; padding-top: 12px; border-top: 1px solid #e0e0e0; }
  .summary-stat { display: flex; align-items: baseline; gap: 6px; }
  .stat-value { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; }
  .stat-value.accent { color: #2d8c2d; }
  .stat-value.lost { color: #c0392b; }
  .stat-label { font-size: 0.75rem; color: #666; }
  .rent-legend { margin-top: 4px; padding-top: 12px; border-top: 1px solid #e0e0e0; display: flex; flex-direction: column; gap: 4px; }
  .legend-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #666; }
  .legend-bar-gradient { display: flex; flex-direction: column; gap: 2px; }
  .gradient-bar { height: 14px; border-radius: 3px; }
  .gradient-bar.green { background: linear-gradient(to right, #b2dfb2, #1a5e1a); }
  .gradient-bar.orange { background: linear-gradient(to right, #fdd9b5, #b35900); }
  .gradient-bar.red { background: linear-gradient(to right, #f5b7b1, #7b241c); }
  .gradient-labels { display: flex; justify-content: space-between; font-size: 0.6rem; color: #888; }
  .size-legend { margin-top: 4px; padding-top: 12px; border-top: 1px solid #e0e0e0; display: flex; flex-direction: column; gap: 6px; }
  .size-legend-row { display: flex; align-items: center; gap: 16px; }
  .size-dot-group { display: flex; align-items: center; gap: 5px; }
  .size-dot { display: inline-block; border-radius: 50%; background: #2d8c2d; opacity: 0.75; flex-shrink: 0; }
  .size-dot-label { font-size: 0.65rem; color: #666; }
</style>
