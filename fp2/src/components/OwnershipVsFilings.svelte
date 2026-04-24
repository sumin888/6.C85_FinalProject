<script>
  // Compares corporate vs individual landlord ownership share against their
  // share of eviction filings, per year and overall. The point: corporates
  // file at a rate far higher than their share of ownership would suggest.
  export let evictionDots = [];    // [{file_year, corp_landlord, ...}]
  export let corpOwnership = [];   // [{year, rate}]  — rate in [0,1]
  export let progress = 1;         // 0–1 for reveal

  // Aggregate filings per year by landlord type
  $: filingsByYear = (() => {
    const m = new Map();
    for (const d of evictionDots) {
      const y = d.file_year;
      if (y == null) continue;
      const b = m.get(y) || { year: y, corp: 0, ind: 0 };
      if (d.corp_landlord) b.corp++; else b.ind++;
      m.set(y, b);
    }
    return [...m.values()].sort((a, b) => a.year - b.year);
  })();

  // Drop sparse years (under 100 filings — the 2023–24 partial data)
  $: usableFilings = filingsByYear.filter(f => f.corp + f.ind >= 100);

  // Merge with ownership rates per year
  $: rows = usableFilings.map(f => {
    const total = f.corp + f.ind;
    const corpFile = total ? f.corp / total : 0;
    const own = corpOwnership.find(o => o.year === f.year);
    const corpOwn = own ? own.rate : null;
    return {
      year: f.year,
      corpFile,                   // 0–1
      corpOwn,                    // 0–1 (null if missing)
      indFile: 1 - corpFile,
      indOwn: corpOwn != null ? 1 - corpOwn : null,
      total,
    };
  }).filter(r => r.corpOwn != null);

  // Overall (entire usable timeframe)
  $: overall = (() => {
    if (rows.length === 0) return null;
    const totalCorp = rows.reduce((s, r) => s + r.total * r.corpFile, 0);
    const totalAll = rows.reduce((s, r) => s + r.total, 0);
    const avgCorpFile = totalAll ? totalCorp / totalAll : 0;
    const avgCorpOwn = rows.reduce((s, r) => s + r.corpOwn, 0) / rows.length;
    const years = rows.map(r => r.year);
    return {
      avgCorpFile,
      avgCorpOwn,
      ratio: avgCorpOwn ? avgCorpFile / avgCorpOwn : null,
      indRatio: (1 - avgCorpOwn) ? (1 - avgCorpFile) / (1 - avgCorpOwn) : null,
      yearMin: Math.min(...years),
      yearMax: Math.max(...years),
    };
  })();

  $: visibleRows = rows.slice(0, Math.max(1, Math.ceil(rows.length * progress)));
</script>

<div class="ovf">
  {#if overall}
    <div class="hero-range">
      Averaged across <strong>{overall.yearMin}–{overall.yearMax}</strong>
    </div>
    <div class="hero-card">
      <div class="hero-block corp">
        <div class="hero-lbl">Corporate landlords</div>
        <div class="hero-stats">
          <div class="stat">
            <span class="n">{(overall.avgCorpOwn * 100).toFixed(0)}%</span>
            <span class="s">of ownership</span>
          </div>
          <div class="arrow">→</div>
          <div class="stat">
            <span class="n orange">{(overall.avgCorpFile * 100).toFixed(0)}%</span>
            <span class="s">of eviction filings</span>
          </div>
        </div>
        <div class="hero-ratio orange-bg">
          Corps filed at <strong>{overall.ratio.toFixed(1)}×</strong>
          their ownership share, {overall.yearMin}–{overall.yearMax}
        </div>
      </div>
      <div class="hero-block ind">
        <div class="hero-lbl">Individual landlords</div>
        <div class="hero-stats">
          <div class="stat">
            <span class="n">{((1 - overall.avgCorpOwn) * 100).toFixed(0)}%</span>
            <span class="s">of ownership</span>
          </div>
          <div class="arrow">→</div>
          <div class="stat">
            <span class="n blue">{((1 - overall.avgCorpFile) * 100).toFixed(0)}%</span>
            <span class="s">of eviction filings</span>
          </div>
        </div>
        <div class="hero-ratio blue-bg">
          Individuals filed at <strong>{overall.indRatio.toFixed(2)}×</strong>
          their ownership share, {overall.yearMin}–{overall.yearMax}
        </div>
      </div>
    </div>
  {/if}

  <div class="year-grid">
    <div class="year-header">
      <span></span>
      <span class="col-lbl">Ownership</span>
      <span class="col-lbl">Filings</span>
      <span class="col-lbl">Ratio</span>
    </div>
    {#each visibleRows as r, i (r.year)}
      {@const ratio = r.corpOwn ? r.corpFile / r.corpOwn : 0}
      {@const delay = i * 90}
      <div class="year-row" style="--row-delay: {delay}ms">
        <span class="year-lbl">{r.year}</span>

        <div class="stacked-mini">
          <div class="seg orange slide" style="--w: {r.corpOwn * 100}%">
            <span class="pct-inline">{(r.corpOwn * 100).toFixed(0)}%</span>
          </div>
          <div class="seg blue slide" style="--w: {r.indOwn * 100}%; animation-delay: calc(var(--row-delay) + 80ms);"></div>
        </div>

        <div class="stacked-mini">
          <div class="seg orange slide" style="--w: {r.corpFile * 100}%; animation-delay: calc(var(--row-delay) + 140ms);">
            <span class="pct-inline">{(r.corpFile * 100).toFixed(0)}%</span>
          </div>
          <div class="seg blue slide" style="--w: {r.indFile * 100}%; animation-delay: calc(var(--row-delay) + 200ms);"></div>
        </div>

        <span class="ratio-val">{ratio.toFixed(1)}×</span>
      </div>
    {/each}
  </div>

  <div class="legend-row">
    <span><span class="sw orange"></span> Corporate</span>
    <span><span class="sw blue"></span> Individual</span>
  </div>
</div>

<style>
  .ovf {
    display: flex;
    flex-direction: column;
    gap: 18px;
    width: 100%;
    max-width: 640px;
    margin: 0 auto;
    align-items: stretch;
  }

  .hero-range {
    text-align: center;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-bottom: -6px;
  }
  .hero-range strong { color: #333; }

  .hero-card {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    justify-content: center;
  }
  .hero-block {
    padding: 14px 16px;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    background: #fff;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .hero-lbl {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #666;
  }
  .hero-stats {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
  }
  .stat .n {
    font-size: 1.4rem;
    font-weight: 800;
    line-height: 1;
    color: #333;
    font-variant-numeric: tabular-nums;
  }
  .stat .n.orange { color: #e67e22; }
  .stat .n.blue { color: #2563eb; }
  .stat .s {
    font-size: 0.68rem;
    color: #888;
    margin-top: 2px;
    text-align: center;
  }
  .arrow {
    font-size: 1.2rem;
    color: #aaa;
  }
  .hero-ratio {
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    text-align: center;
    color: #333;
  }
  .hero-ratio.orange-bg { background: #fff1e0; }
  .hero-ratio.blue-bg { background: #e7efff; }
  .hero-ratio strong { font-size: 1rem; }

  .year-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px 14px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fff;
  }
  .year-header, .year-row {
    display: grid;
    grid-template-columns: 56px 1fr 1fr 52px;
    gap: 10px;
    align-items: center;
  }
  .year-header {
    padding-bottom: 4px;
    border-bottom: 1px solid #eee;
  }
  .col-lbl {
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
  }
  .year-lbl {
    font-size: 0.8rem;
    font-weight: 700;
    color: #333;
    font-variant-numeric: tabular-nums;
  }
  .stacked-mini {
    display: flex;
    height: 16px;
    border-radius: 3px;
    overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
  }
  .seg {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    min-width: 0;
    width: var(--w);
  }
  .seg.slide {
    animation: segSlide 0.6s cubic-bezier(0.2, 0.9, 0.3, 1) backwards;
    animation-delay: var(--row-delay, 0ms);
  }
  @keyframes segSlide {
    from { width: 0; }
    to   { width: var(--w); }
  }
  .seg.orange { background: #e67e22; }
  .seg.blue { background: #2563eb; }
  .pct-inline {
    font-size: 0.64rem;
    font-weight: 700;
    color: #fff;
    padding: 0 4px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.2);
    white-space: nowrap;
  }
  .ratio-val {
    text-align: right;
    font-size: 0.9rem;
    font-weight: 800;
    color: #e67e22;
    font-variant-numeric: tabular-nums;
  }

  .legend-row {
    display: flex;
    gap: 18px;
    font-size: 0.75rem;
    color: #555;
  }
  .sw {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: middle;
  }
  .sw.orange { background: #e67e22; }
  .sw.blue { background: #2563eb; }
</style>
