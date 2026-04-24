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
  const margin = { top: 16, right: 120, bottom: 36, left: 56 };

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

    const x = d3.scaleBand()
      .domain(visibleData.map(d => d.year))
      .range([0, w])
      .padding(0.2);

    const y = d3.scaleLinear()
      .domain([0, d3.max(stacked[stacked.length - 1], d => d[1]) * 1.1 || 1])
      .range([h, 0]);

    const colorMap = {};
    for (const c of categories) colorMap[c.key] = c.color;

    // Axes
    g.append('g').attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(x).tickValues(visibleData.filter((_, i) => i % Math.max(1, Math.floor(visibleData.length / 8)) === 0).map(d => d.year)))
      .call(g => g.select('.domain').attr('stroke', '#ddd'))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '10px'));

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(yFormat))
      .call(g => g.select('.domain').attr('stroke', '#ddd'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#eee').attr('x2', w).attr('opacity', 0.3))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '10px'));

    // Bars
    for (const layer of stacked) {
      g.selectAll(`.bar-${layer.key}`)
        .data(layer)
        .join('rect')
        .attr('x', d => x(d.data.year))
        .attr('y', d => y(d[1]))
        .attr('height', d => y(d[0]) - y(d[1]))
        .attr('width', x.bandwidth())
        .attr('fill', colorMap[layer.key] || '#999')
        .attr('opacity', 0.85);
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

<svg bind:this={svgEl} {width} {height} class="animated-chart"></svg>

<style>
  .animated-chart { display: block; }
</style>
