<script>
  import { createEventDispatcher } from 'svelte';
  import { fade, scale } from 'svelte/transition';

  export let open = false;
  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }

  function onKey(e) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window on:keydown={onKey} />

{#if open}
  <div class="ref-backdrop" transition:fade={{ duration: 180 }} on:click={close}>
    <div
      class="ref-modal"
      role="dialog"
      aria-modal="true"
      aria-label="References"
      transition:scale={{ duration: 220, start: 0.96 }}
      on:click|stopPropagation
    >
      <button class="ref-close" on:click={close} aria-label="Close">×</button>
      <div class="ref-eyebrow">References</div>
      <h2 class="ref-title">Where this data comes from</h2>
      <p class="ref-lede">
        Every number, polygon, and dot in this story is pulled from a public
        dataset. Click any source below to explore it yourself.
      </p>

      <ul class="ref-list">
        <li>
          <div class="src-name">MAPC Residential Sales (2000–2023)</div>
          <div class="src-desc">
            Every property transaction in Metro Boston with price, address,
            year, and buyer / seller LLC indicators. Drives the Corporate
            Takeover, Who's Buying, and rent estimates.
          </div>
          <a class="src-link" href="https://datacommon.mapc.org/" target="_blank" rel="noopener">
            MAPC Data Common ↗
          </a>
        </li>

        <li>
          <div class="src-name">MA Trial Court Eviction Filings (2020–2024)</div>
          <div class="src-desc">
            Court records for every eviction case filed in Boston, with case
            type, plaintiff details, address, and file date. Each map dot is
            one of these filings.
          </div>
          <a class="src-link" href="https://www.mass.gov/orgs/massachusetts-court-system" target="_blank" rel="noopener">
            Massachusetts Court System ↗
          </a>
        </li>

        <li>
          <div class="src-name">City of Boston Property Assessment (2004–2024)</div>
          <div class="src-desc">
            Per-parcel ownership rolls used to compute corporate-ownership
            and owner-occupancy rates over time. Corporate ownership flagged
            by name patterns ("LLC", "Trust", "Realty"…).
          </div>
          <a class="src-link" href="https://data.boston.gov/dataset/property-assessment" target="_blank" rel="noopener">
            Analyze Boston · Property Assessment ↗
          </a>
        </li>

        <li>
          <div class="src-name">Zillow Observed Rent Index (ZORI)</div>
          <div class="src-desc">
            Monthly rent index per ZIP, used to calibrate sale-based rent
            estimates and to track rent change since 2016 in each
            neighborhood.
          </div>
          <a class="src-link" href="https://www.zillow.com/research/data/" target="_blank" rel="noopener">
            Zillow Research ↗
          </a>
        </li>

        <li>
          <div class="src-name">Boston Neighborhoods &amp; Census Tracts</div>
          <div class="src-desc">
            BPDA neighborhood polygons and 2020 US Census tract geometry.
            Provides the map's boundaries and demographic context (renter
            median income, owner occupancy) joined into each neighborhood.
          </div>
          <a class="src-link" href="https://data.boston.gov/dataset/boston-neighborhoods" target="_blank" rel="noopener">
            Analyze Boston · Boston Neighborhoods ↗
          </a>
        </li>
      </ul>

      <div class="ref-acknowledgement">
        <span class="ack-label">Acknowledgement</span>
        Built with the help of <strong>Claude Code</strong> (Anthropic) for
        UX iteration, visualization design, and front-end implementation.
      </div>
    </div>
  </div>
{/if}

<style>
  .ref-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 15, 15, 0.55);
    backdrop-filter: blur(2px);
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .ref-modal {
    position: relative;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
    max-width: 640px;
    width: 100%;
    max-height: calc(100vh - 80px);
    overflow-y: auto;
    padding: 32px 36px;
    font-family: 'Inter', system-ui, sans-serif;
  }
  .ref-close {
    position: absolute;
    top: 14px;
    right: 16px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #f0f0f0;
    color: #555;
    border: none;
    font-size: 1.4rem;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ref-close:hover { background: #e0e0e0; color: #1a1a1a; }
  .ref-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888;
    margin-bottom: 6px;
  }
  .ref-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #1a1a1a;
    margin: 0 0 10px;
    letter-spacing: -0.01em;
  }
  .ref-lede {
    font-size: 0.88rem;
    color: #555;
    line-height: 1.55;
    margin: 0 0 20px;
  }
  .ref-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .ref-list li {
    padding: 12px 14px;
    border-left: 3px solid #e67e22;
    background: #fafafa;
    border-radius: 4px;
  }
  .src-name {
    font-size: 0.92rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 3px;
  }
  .src-desc {
    font-size: 0.78rem;
    color: #555;
    line-height: 1.5;
    margin-bottom: 6px;
  }
  .src-link {
    font-size: 0.76rem;
    font-weight: 600;
    color: #2563eb;
    text-decoration: none;
  }
  .src-link:hover { text-decoration: underline; }

  .ref-acknowledgement {
    margin-top: 22px;
    padding: 14px 16px;
    background: #f6f8fc;
    border: 1px dashed #d6deec;
    border-radius: 6px;
    font-size: 0.78rem;
    color: #555;
    line-height: 1.55;
  }
  .ref-acknowledgement .ack-label {
    display: block;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #888;
    margin-bottom: 4px;
  }
  .ref-acknowledgement strong { color: #1a1a1a; }
</style>
