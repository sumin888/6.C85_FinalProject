<script>
  // 2×2 ownership-flow matrix: rows = seller type, columns = buyer type.
  // Each cell shows baseline share → latest share, with a growth multiplier
  // and background intensity scaled to growth magnitude.
  export let baseline = null;   // { ind_to_ind, ind_to_corp, corp_to_ind, corp_to_corp }
  export let latest = null;
  export let baselineYear = null;
  export let latestYear = null;
  export let progress = 1;      // 0–1 (for reveal)

  // Cell layout (row-major, seller then buyer):
  $: cells = [
    { key: 'ind_to_ind',   seller: 'Individual', buyer: 'Individual' },
    { key: 'ind_to_corp',  seller: 'Individual', buyer: 'Corporate'  },
    { key: 'corp_to_ind',  seller: 'Corporate',  buyer: 'Individual' },
    { key: 'corp_to_corp', seller: 'Corporate',  buyer: 'Corporate'  },
  ].map(c => {
    const t = baseline?.[c.key] ?? 0;
    const n = latest?.[c.key] ?? 0;
    const mult = t > 0 ? n / t : null;
    return { ...c, then: t, now: n, mult };
  });

  // Clamp reveal to visible subset for the scroll animation
  $: visibleCells = cells.map((c, i) => ({
    ...c,
    revealed: (i + 1) / cells.length <= progress + 0.05,
  }));

  function heatColor(mult) {
    if (mult == null) return '#f5f5f5';
    if (mult > 1.15) {
      const t = Math.min(1, (mult - 1) / 4);
      // Light to bold orange
      return `rgba(230, 126, 34, ${0.12 + t * 0.5})`;
    }
    if (mult < 0.95) {
      const t = Math.min(1, (1 - mult) / 0.2);
      return `rgba(37, 99, 235, ${0.10 + t * 0.25})`;
    }
    return '#fafafa';
  }
  function signClass(mult) {
    if (mult == null) return '';
    if (mult > 1.02) return 'grow';
    if (mult < 0.98) return 'shrink';
    return '';
  }
  function fmtPct(v) { return `${(v * 100).toFixed(1)}%`; }
</script>

<div class="flow-matrix">
  <div class="matrix-head-row">
    <div class="corner">
      <span class="corner-tl">Seller</span>
      <span class="corner-br">Buyer</span>
    </div>
    <div class="col-head">Individual</div>
    <div class="col-head">Corporate</div>
  </div>

  <div class="matrix-body">
    <div class="row-head">Individual</div>
    {#each visibleCells.slice(0, 2) as c}
      <div class="cell" class:revealed={c.revealed} style="background:{c.revealed ? heatColor(c.mult) : '#f5f5f5'}">
        <div class="cell-flow">
          <span class="pill">{c.seller}</span>
          <span class="arrow">→</span>
          <span class="pill" class:corp={c.buyer === 'Corporate'}>{c.buyer}</span>
        </div>
        <div class="cell-transition">
          <span class="then-val">{fmtPct(c.then)}</span>
          <span class="arrow-sm">→</span>
          <span class="now-val">{fmtPct(c.now)}</span>
        </div>
        <div class="cell-mult {signClass(c.mult)}">
          {#if c.mult != null}
            <strong>{c.mult.toFixed(1)}×</strong>
            <span class="mult-label">
              {c.mult > 1.02 ? 'growth' : c.mult < 0.98 ? 'shrink' : 'flat'}
            </span>
          {/if}
        </div>
      </div>
    {/each}

    <div class="row-head">Corporate</div>
    {#each visibleCells.slice(2) as c}
      <div class="cell" class:revealed={c.revealed} style="background:{c.revealed ? heatColor(c.mult) : '#f5f5f5'}">
        <div class="cell-flow">
          <span class="pill" class:corp={c.seller === 'Corporate'}>{c.seller}</span>
          <span class="arrow">→</span>
          <span class="pill" class:corp={c.buyer === 'Corporate'}>{c.buyer}</span>
        </div>
        <div class="cell-transition">
          <span class="then-val">{fmtPct(c.then)}</span>
          <span class="arrow-sm">→</span>
          <span class="now-val">{fmtPct(c.now)}</span>
        </div>
        <div class="cell-mult {signClass(c.mult)}">
          {#if c.mult != null}
            <strong>{c.mult.toFixed(1)}×</strong>
            <span class="mult-label">
              {c.mult > 1.02 ? 'growth' : c.mult < 0.98 ? 'shrink' : 'flat'}
            </span>
          {/if}
        </div>
      </div>
    {/each}
  </div>

  {#if baselineYear != null && latestYear != null}
    <div class="matrix-caption">
      Share of Boston property sales, <strong>{baselineYear}</strong> → <strong>{latestYear}</strong>
    </div>
  {/if}
</div>

<style>
  .flow-matrix {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    max-width: 560px;
  }

  .matrix-head-row {
    display: grid;
    grid-template-columns: 90px 1fr 1fr;
    gap: 8px;
    align-items: stretch;
  }
  .corner {
    position: relative;
    padding: 4px 6px;
    font-size: 0.68rem;
    color: #888;
  }
  .corner-tl {
    position: absolute;
    top: 2px;
    left: 4px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #aaa;
  }
  .corner-br {
    position: absolute;
    bottom: 2px;
    right: 4px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #aaa;
  }
  .col-head {
    font-size: 0.78rem;
    font-weight: 700;
    color: #333;
    text-align: center;
    padding: 8px 0 4px;
    border-bottom: 2px solid #e0e0e0;
  }

  .matrix-body {
    display: grid;
    grid-template-columns: 90px 1fr 1fr;
    gap: 8px;
  }
  .row-head {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0 10px;
    font-size: 0.8rem;
    font-weight: 700;
    color: #333;
    border-right: 2px solid #e0e0e0;
    text-align: right;
  }

  .cell {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: background 0.5s ease, opacity 0.3s;
    opacity: 0;
  }
  .cell.revealed { opacity: 1; }

  .cell-flow {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
  }
  .pill {
    padding: 2px 7px;
    border-radius: 999px;
    background: #eef3fc;
    color: #2563eb;
    border: 1px solid #cadaf4;
    font-weight: 600;
    font-size: 0.68rem;
  }
  .pill.corp {
    background: #fdecd9;
    color: #b35900;
    border-color: #f0caa0;
  }
  .arrow { color: #999; }
  .arrow-sm { color: #aaa; margin: 0 4px; }

  .cell-transition {
    display: flex;
    align-items: baseline;
    gap: 2px;
    font-size: 0.9rem;
    color: #444;
    font-variant-numeric: tabular-nums;
  }
  .then-val { color: #888; }
  .now-val { font-weight: 700; color: #1a1a1a; }

  .cell-mult {
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: 0.9rem;
    color: #666;
  }
  .cell-mult strong {
    font-size: 1.15rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    color: #555;
  }
  .cell-mult.grow strong { color: #e67e22; }
  .cell-mult.shrink strong { color: #2563eb; }
  .mult-label {
    font-size: 0.68rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .matrix-caption {
    font-size: 0.72rem;
    color: #888;
    text-align: center;
  }
</style>
