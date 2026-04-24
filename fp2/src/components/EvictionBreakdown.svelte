<script>
  export let data = null; // eviction data for one neighborhood

  $: caseTypes = data ? Object.entries(data.case_types || {})
    .sort((a, b) => b[1] - a[1]).slice(0, 4) : [];
  $: totalFilings = data?.total_filings ?? 0;
  $: corpRate = data?.corp_rate ?? 0;
  $: topPlaintiffs = data?.top_plaintiffs?.slice(0, 3) ?? [];
</script>

{#if data && totalFilings > 0}
  <div class="eviction-breakdown">
    <!-- Corp vs Individual bar -->
    <div class="bar-section">
      <div class="bar-label">
        <span>Corporate: <strong>{(corpRate * 100).toFixed(0)}%</strong></span>
        <span>Individual: <strong>{((1 - corpRate) * 100).toFixed(0)}%</strong></span>
      </div>
      <div class="stacked-bar">
        <div class="bar-segment corp" style="width:{corpRate * 100}%"></div>
        <div class="bar-segment indiv" style="width:{(1 - corpRate) * 100}%"></div>
      </div>
    </div>

    <!-- Case types -->
    <div class="case-types">
      {#each caseTypes as [type, count]}
        {@const pct = (count / totalFilings * 100).toFixed(0)}
        <div class="case-row">
          <span class="case-name">{type}</span>
          <div class="case-bar-wrap">
            <div class="case-bar" style="width:{pct}%"></div>
          </div>
          <span class="case-count">{count}</span>
        </div>
      {/each}
    </div>

    <!-- Top plaintiffs -->
    {#if topPlaintiffs.length > 0}
      <div class="top-plaintiffs">
        <div class="plaintiff-label">Top Corporate Filers</div>
        {#each topPlaintiffs as ptf}
          <div class="plaintiff-row">
            <span class="plaintiff-name">{ptf.name.length > 40 ? ptf.name.slice(0, 40) + '...' : ptf.name}</span>
            <span class="plaintiff-count">{ptf.count} filings</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .eviction-breakdown { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; }
  .bar-section { display: flex; flex-direction: column; gap: 4px; }
  .bar-label { display: flex; justify-content: space-between; font-size: 0.7rem; color: #666; }
  .bar-label strong { color: #333; }
  .stacked-bar { display: flex; height: 16px; border-radius: 3px; overflow: hidden; }
  .bar-segment.corp { background: #c0392b; }
  .bar-segment.indiv { background: #3498db; }
  .case-types { display: flex; flex-direction: column; gap: 4px; }
  .case-row { display: flex; align-items: center; gap: 6px; font-size: 0.7rem; }
  .case-name { flex: 0 0 130px; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .case-bar-wrap { flex: 1; height: 8px; background: #eee; border-radius: 2px; }
  .case-bar { height: 100%; background: #c0392b; border-radius: 2px; opacity: 0.7; }
  .case-count { flex: 0 0 32px; text-align: right; font-weight: 600; color: #333; font-size: 0.65rem; }
  .top-plaintiffs { display: flex; flex-direction: column; gap: 3px; }
  .plaintiff-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #888; }
  .plaintiff-row { display: flex; justify-content: space-between; font-size: 0.68rem; }
  .plaintiff-name { color: #444; }
  .plaintiff-count { color: #c0392b; font-weight: 600; white-space: nowrap; }
</style>
