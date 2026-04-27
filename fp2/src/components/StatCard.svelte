<script>
  export let value;
  export let label;
  export let color = 'default'; // 'default' | 'accent' | 'red' | 'orange'
</script>

<div class="stat-card">
  <span class="stat-value" class:accent={color === 'accent'} class:red={color === 'red'} class:orange={color === 'orange'}>
    {value}
  </span>
  <span class="stat-label">{label}</span>
</div>

<style>
  .stat-card { display: flex; align-items: baseline; gap: 8px; padding: 4px 0; }
  .stat-value { font-size: 1.2rem; font-weight: 700; color: #1a1a1a; }
  .stat-value.accent { color: #2d8c2d; }
  .stat-value.red { color: #c0392b; }
  .stat-value.orange { color: #b35900; }
  .stat-label { font-size: 0.78rem; color: #666; }
</style>
