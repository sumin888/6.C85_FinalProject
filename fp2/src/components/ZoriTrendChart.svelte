<script>
  import { onMount, afterUpdate } from 'svelte';
  import * as d3 from 'd3';

  export let data = [];         // [{date, rent}]
  export let highlightYear = null;  // optional: year to mark with vertical line
  export let width = 280;
  export let height = 120;

  let svgEl;
  const margin = { top: 10, right: 12, bottom: 22, left: 42 };

  function draw() {
    if (!svgEl || !data || data.length === 0) return;
    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const parsed = data.map(d => ({ date: new Date(d.date), rent: d.rent })).filter(d => !isNaN(d.rent));
    if (parsed.length === 0) return;

    const x = d3.scaleTime().domain(d3.extent(parsed, d => d.date)).range([0, w]);
    const y = d3.scaleLinear().domain([0, d3.max(parsed, d => d.rent) * 1.1]).range([h, 0]);

    // Axes
    g.append('g').attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat('%Y')))
      .call(g => g.select('.domain').attr('stroke', '#ccc'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#ccc'))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '9px'));

    g.append('g')
      .call(d3.axisLeft(y).ticks(4).tickFormat(d => `$${d >= 1000 ? (d/1000).toFixed(1) + 'k' : d}`))
      .call(g => g.select('.domain').attr('stroke', '#ccc'))
      .call(g => g.selectAll('.tick line').attr('stroke', '#ccc'))
      .call(g => g.selectAll('.tick text').attr('fill', '#888').attr('font-size', '9px'));

    // Line
    const line = d3.line().x(d => x(d.date)).y(d => y(d.rent)).curve(d3.curveMonotoneX);
    g.append('path').datum(parsed)
      .attr('fill', 'none').attr('stroke', '#2d8c2d').attr('stroke-width', 2)
      .attr('d', line);

    // Endpoint dot
    const last = parsed[parsed.length - 1];
    g.append('circle').attr('cx', x(last.date)).attr('cy', y(last.rent))
      .attr('r', 4).attr('fill', '#2d8c2d');

    // Endpoint label
    g.append('text').attr('x', x(last.date)).attr('y', y(last.rent) - 8)
      .attr('text-anchor', 'end').attr('fill', '#2d8c2d')
      .attr('font-size', '10px').attr('font-weight', '600')
      .text(`$${last.rent.toLocaleString()}`);

    // Highlight year marker
    if (highlightYear) {
      const hlDate = new Date(`${highlightYear}-07-01`);
      if (hlDate >= x.domain()[0] && hlDate <= x.domain()[1]) {
        g.append('line')
          .attr('x1', x(hlDate)).attr('x2', x(hlDate))
          .attr('y1', 0).attr('y2', h)
          .attr('stroke', '#e67e22').attr('stroke-width', 1.5)
          .attr('stroke-dasharray', '4,3').attr('opacity', 0.7);
      }
    }
  }

  onMount(draw);
  afterUpdate(draw);
</script>

<svg bind:this={svgEl} {width} {height} class="zori-chart"></svg>

<style>
  .zori-chart {
    display: block;
    margin-top: 8px;
  }
</style>
