<script>
  import { afterUpdate } from 'svelte';
  import * as d3 from 'd3';

  export let lines = [];        // [{label, data: [{x, y}], color}]
  export let progress = 1;      // 0–1: how much of the chart to reveal
  export let width = 500;
  export let height = 280;
  export let xLabel = '';
  export let yLabel = '';
  export let yFormat = v => v;  // e.g. v => (v*100).toFixed(0) + '%'
  export let xFormat = v => v;

  let svgEl;
  const margin = { top: 16, right: 156, bottom: 36, left: 56 };

  function draw() {
    if (!svgEl || lines.length === 0) return;
    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const allPoints = lines.flatMap(l => l.data);
    const x = d3.scaleLinear()
      .domain(d3.extent(allPoints, d => d.x))
      .range([0, w]);
    const y = d3.scaleLinear()
      .domain([0, d3.max(allPoints, d => d.y) * 1.15])
      .range([h, 0]);

    // Grid
    g.append('g').attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat(d => xFormat(d)))
      .call(g => g.select('.domain').attr('stroke', '#ddd'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#eee'))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '11px'));

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => yFormat(d)))
      .call(g => g.select('.domain').attr('stroke', '#ddd'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#eee').attr('x2', w).attr('opacity', 0.3))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '11px'));

    // Axis labels
    if (xLabel) {
      g.append('text').attr('x', w / 2).attr('y', h + 32).attr('text-anchor', 'middle')
        .attr('fill', '#999').attr('font-size', '11px').text(xLabel);
    }
    if (yLabel) {
      g.append('text').attr('transform', 'rotate(-90)').attr('x', -h / 2).attr('y', -44)
        .attr('text-anchor', 'middle').attr('fill', '#999').attr('font-size', '11px').text(yLabel);
    }

    // Draw each line, clipped to progress
    const clipX = w * Math.max(0, Math.min(1, progress));

    for (const line of lines) {
      const lineGen = d3.line().x(d => x(d.x)).y(d => y(d.y)).curve(d3.curveMonotoneX);
      if (line.data.length === 0) continue;

      const sorted = [...line.data].sort((a, b) => a.x - b.x);
      const xAtEdge = x.invert(clipX);

      // Build a truncated series: every real datapoint whose x ≤ clipX,
      // plus one interpolated point exactly at (xAtEdge, y_interp). The path
      // renders this partial series instead of being clipped by a rect — so
      // its rendered endpoint *is* the dot's position, with no mismatch.
      const partial = [];
      for (let i = 0; i < sorted.length; i++) {
        const d = sorted[i];
        if (d.x <= xAtEdge) {
          partial.push(d);
        } else {
          const prev = partial.length ? partial[partial.length - 1] : sorted[0];
          const t = d.x === prev.x ? 0 : (xAtEdge - prev.x) / (d.x - prev.x);
          partial.push({ x: xAtEdge, y: prev.y + t * (d.y - prev.y) });
          break;
        }
      }
      if (partial.length === 0) partial.push(sorted[0]);
      // If clipX lands beyond the last point, extend to the last point explicitly.
      if (partial[partial.length - 1].x < sorted[sorted.length - 1].x && xAtEdge >= sorted[sorted.length - 1].x) {
        partial.push(sorted[sorted.length - 1]);
      }

      // Draw the partial line — ends precisely where we'll place the dot.
      g.append('path')
        .datum(partial)
        .attr('fill', 'none')
        .attr('stroke', line.color)
        .attr('stroke-width', 2.5)
        .attr('stroke-linecap', 'round')
        .attr('stroke-linejoin', 'round')
        .attr('d', lineGen);

      // Dot + label at the exact endpoint of the drawn line
      const tip = partial[partial.length - 1];
      const cx = x(tip.x);
      const cy = y(tip.y);

      g.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', 4).attr('fill', line.color);

      // Label reflects the nearest passed datapoint so the number stays clean
      let labelPoint = sorted[0];
      for (const d of sorted) if (d.x <= xAtEdge) labelPoint = d;
      g.append('text')
        .attr('x', cx + 8).attr('y', cy + 4)
        .attr('fill', line.color).attr('font-size', '11px').attr('font-weight', '600')
        .text(`${line.label}: ${yFormat(labelPoint.y)}`);
    }
  }

  afterUpdate(draw);
</script>

<svg bind:this={svgEl} {width} {height} class="animated-chart"></svg>

<style>
  .animated-chart { display: block; }
</style>
