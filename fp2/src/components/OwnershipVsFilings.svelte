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
  <div class="year-grid">
    <div class="year-header">
      <span></span>
      <span class="col-lbl">Ownership</span>
      <span class="col-lbl">Filings</span>
      <span class="col-lbl">Corps ratio</span>
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

  .year-row.avg-row {
    background: #fafbfd;
    margin: 0 -10px 4px;
    padding: 8px 10px;
    border-radius: 6px;
    border-bottom: 1px dashed #d6deec;
  }
  .avg-lbl {
    font-weight: 800;
    color: #1a1a1a !important;
    font-size: 0.74rem !important;
    line-height: 1.15;
  }
  .avg-ratios {
    display: flex;
    flex-direction: column;
    gap: 3px;
    align-items: flex-end;
  }
  .ratio-chip {
    font-size: 0.9rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    color: #e67e22;
  }

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
    grid-template-columns: 64px 1fr 1fr 78px;
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
  /* Right-most header aligns with the right-aligned ratio values below */
  .year-header .col-lbl:last-child {
    text-align: right;
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
