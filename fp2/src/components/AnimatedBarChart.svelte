<script>
  import { afterUpdate } from 'svelte';
  import * as d3 from 'd3';

  export let data = [];         // [{year, ...category_values}]
  export let categories = [];   // [{key, label, color}]
  export let progress = 1;      // 0–1
  export let width = 500;
  export let height = 280;
  export let yFormat = v => v;

  let svgEl;
  let hoveredYear = null;
  const margin = { top: 16, right: 120, bottom: 36, left: 56 };

  // Compute per-year x + width. If a year is hovered, it takes expandFactor times
  // the width of an ordinary column; otherwise everything is uniform.
  function bandPositions(years, w, hovered) {
    const n = years.length;
    if (n === 0) return [];
    const pad = 0.2;
    const expandFactor = Math.min(4, Math.max(2, n / 6)); // 2×–4× wider

    const totalUnits = hovered != null && years.includes(hovered)
      ? (n - 1) + expandFactor
      : n;
    const unit = w / totalUnits;

    const out = [];
    let cursor = 0;
    for (const y of years) {
      const units = (hovered === y) ? expandFactor : 1;
      const slot = unit * units;
      const bw = slot * (1 - pad);
      out.push({ year: y, x: cursor + (slot - bw) / 2, w: bw, slotX: cursor, slotW: slot });
      cursor += slot;
    }
    return out;
  }

  function draw() {
    if (!svgEl || data.length === 0 || categories.length === 0) return;
    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const visibleCount = Math.max(1, Math.ceil(data.length * progress));
    const visibleData = data.slice(0, visibleCount);

    const keys = categories.map(c => c.key);
    const stacked = d3.stack().keys(keys)(visibleData);

    // When a year is hovered, drop the years farthest from it so the hovered
    // bar has room to breathe without crushing the x-axis labels.
    const hoverWindow = 3;
    let drawData = visibleData;
    if (hoveredYear != null) {
      const idx = visibleData.findIndex(d => d.year === hoveredYear);
      if (idx >= 0) {
        const lo = Math.max(0, idx - hoverWindow);
        const hi = Math.min(visibleData.length, idx + hoverWindow + 1);
        drawData = visibleData.slice(lo, hi);
      }
    }
    // Map for stacked layers: restrict to drawn years only
    const drawYears = new Set(drawData.map(d => d.year));

    const positions = bandPositions(drawData.map(d => d.year), w, hoveredYear);
    const posByYear = new Map(positions.map(p => [p.year, p]));

    const y = d3.scaleLinear()
      .domain([0, d3.max(stacked[stacked.length - 1], d => d[1]) * 1.1 || 1])
      .range([h, 0]);

    const colorMap = {};
    for (const c of categories) colorMap[c.key] = c.color;

    // Axes — x-axis uses the computed positions. When hovered, every surviving
    // year gets a label (the window is small enough). Otherwise subsample.
    const tickStep = Math.max(1, Math.floor(drawData.length / 8));
    const xAxis = g.append('g').attr('transform', `translate(0,${h})`);
    xAxis.append('line')
      .attr('x1', 0).attr('y1', 0).attr('x2', w).attr('y2', 0)
      .attr('stroke', '#ddd');
    drawData.forEach((d, i) => {
      const p = posByYear.get(d.year);
      if (!p) return;
      const isHovered = d.year === hoveredYear;
      if (hoveredYear == null && i % tickStep !== 0) return;
      xAxis.append('text')
        .attr('x', p.x + p.w / 2)
        .attr('y', 14)
        .attr('text-anchor', 'middle')
        .attr('fill', isHovered ? '#1a1a1a' : '#888')
        .attr('font-size', isHovered ? '11px' : '10px')
        .attr('font-weight', isHovered ? 700 : 400)
        .text(d.year);
    });

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(yFormat))
      .call(g => g.select('.domain').attr('stroke', '#ddd'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#eee').attr('x2', w).attr('opacity', 0.3))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '10px'));

    // Bars — only render layers for the drawn years
    for (const layer of stacked) {
      const bars = g.append('g').attr('class', `layer-${layer.key}`);
      layer.forEach(seg => {
        if (!drawYears.has(seg.data.year)) return;
        const p = posByYear.get(seg.data.year);
        if (!p) return;
        bars.append('rect')
          .attr('x', p.x)
          .attr('y', y(seg[1]))
          .attr('width', p.w)
          .attr('height', y(seg[0]) - y(seg[1]))
          .attr('fill', colorMap[layer.key] || '#999')
          .attr('opacity', hoveredYear == null || seg.data.year === hoveredYear ? 0.9 : 0.45)
          .style('transition', 'x 0.18s ease, width 0.18s ease, opacity 0.18s ease');
      });
    }

    // Invisible hit-areas that drive hover state
    const hitLayer = g.append('g').attr('class', 'hit-layer');
    for (const p of positions) {
      hitLayer.append('rect')
        .attr('x', p.slotX)
        .attr('y', 0)
        .attr('width', p.slotW)
        .attr('height', h)
        .attr('fill', 'transparent')
        .style('cursor', 'pointer')
        .on('mouseenter', () => { if (hoveredYear !== p.year) { hoveredYear = p.year; draw(); } })
        .on('mouseleave', () => { if (hoveredYear === p.year) { hoveredYear = null; draw(); } });
    }

    // Legend
    const legend = svg.append('g')
      .attr('transform', `translate(${margin.left + w + 12}, ${margin.top})`);

    categories.forEach((c, i) => {
      const row = legend.append('g').attr('transform', `translate(0, ${i * 18})`);
      row.append('rect').attr('width', 12).attr('height', 12).attr('rx', 2).attr('fill', c.color).attr('opacity', 0.85);
      row.append('text').attr('x', 16).attr('y', 10).attr('fill', '#666').attr('font-size', '10px').text(c.label);
    });
  }

  afterUpdate(draw);
</script>

<svg bind:this={svgEl} {width} {height} class="animated-chart" on:mouseleave={() => { if (hoveredYear != null) { hoveredYear = null; draw(); } }}></svg>

<style>
  .animated-chart { display: block; }
</style>
