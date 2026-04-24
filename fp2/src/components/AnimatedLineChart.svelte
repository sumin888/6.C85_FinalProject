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
  const margin = { top: 16, right: 120, bottom: 36, left: 56 };

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

      // Clip path
      const clipId = `clip-${Math.random().toString(36).slice(2, 8)}`;
      svg.append('defs').append('clipPath').attr('id', clipId)
        .append('rect').attr('x', margin.left).attr('y', 0)
        .attr('width', clipX).attr('height', height);

      g.append('path')
        .datum(line.data)
        .attr('fill', 'none')
        .attr('stroke', line.color)
        .attr('stroke-width', 2.5)
        .attr('d', lineGen)
        .attr('clip-path', `url(#${clipId})`);

      // Endpoint dot + label at progress position
      const visibleData = line.data.filter(d => x(d.x) <= clipX);
      if (visibleData.length > 0) {
        const last = visibleData[visibleData.length - 1];
        g.append('circle')
          .attr('cx', x(last.x)).attr('cy', y(last.y))
          .attr('r', 4).attr('fill', line.color);

        g.append('text')
          .attr('x', x(last.x) + 8).attr('y', y(last.y) + 4)
          .attr('fill', line.color).attr('font-size', '11px').attr('font-weight', '600')
          .text(`${line.label}: ${yFormat(last.y)}`);
      }
    }
  }

  afterUpdate(draw);
</script>

<svg bind:this={svgEl} {width} {height} class="animated-chart"></svg>

<style>
  .animated-chart { display: block; }
</style>
