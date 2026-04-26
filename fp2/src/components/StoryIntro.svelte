<script>
  import { onMount, tick, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';

  export let openReferences = () => {};
  import AnimatedLineChart from './AnimatedLineChart.svelte';
  import FlowDiagram from './FlowDiagram.svelte';
  import OwnershipVsFilings from './OwnershipVsFilings.svelte';
  import DonutChart from './DonutChart.svelte';

  const dispatch = createEventDispatcher();

  export let storyData;   // corp_ownership_timeseries.json
  export let zoriData;    // zori_by_neighborhood.json
  export let evictionDots = [];  // eviction case dots, for per-year aggregation
  export let geoData;     // neighborhoods.geojson (for median income)

  let scrollStep = 0;
  let stepProgresses = [0, 0, 0, 0, 0, 0, 0, 0]; // per-step scroll progress 0–1

  // ── Sale-flow baseline vs. latest for the flow diagram ─────────────────
  $: saleFlowDiagram = (() => {
    const flow = storyData?.citywide?.sale_flow_rates;
    if (!Array.isArray(flow) || flow.length < 2) return null;
    const sorted = [...flow].sort((a, b) => a.year - b.year);
    const baseline = sorted[0];
    const latest = sorted[sorted.length - 1];
    return {
      baselineYear: baseline.year,
      latestYear: latest.year,
      baseline: {
        ind_to_ind: baseline.ind_to_ind, ind_to_corp: baseline.ind_to_corp,
        corp_to_ind: baseline.corp_to_ind, corp_to_corp: baseline.corp_to_corp,
      },
      latest: {
        ind_to_ind: latest.ind_to_ind, ind_to_corp: latest.ind_to_corp,
        corp_to_ind: latest.corp_to_ind, corp_to_corp: latest.corp_to_corp,
      },
    };
  })();

  // ── Median renter income per neighborhood (step 3 sub-scroll) ───────────
  const focusHoods = ['Mission Hill', 'Roxbury', 'Dorchester'];
  $: focusIncome = (() => {
    if (!geoData?.features) return [];
    return focusHoods.map(name => {
      const f = geoData.features.find(x => x.properties?.name === name);
      return {
        name,
        renter: f?.properties?.avg_renter_mhi ?? null,
        owner: f?.properties?.avg_owner_mhi ?? null,
      };
    }).filter(d => d.renter != null);
  })();
  // Boston-wide medians: prefer the household-weighted citywide value baked
  // into the geojson metadata (every tract weighted by its renter/owner
  // household count). Falls back to a household-weighted average across the
  // available neighborhood records if metadata isn't present.
  $: bostonMedians = (() => {
    const meta = geoData?.metadata;
    if (meta?.citywide_renter_mhi && meta?.citywide_owner_mhi) {
      return { renter: meta.citywide_renter_mhi, owner: meta.citywide_owner_mhi };
    }
    if (!geoData?.features) return { renter: 54000, owner: 118000 };
    const r = [], o = [];
    for (const f of geoData.features) {
      if (f.properties?.avg_renter_mhi) r.push(f.properties.avg_renter_mhi);
      if (f.properties?.avg_owner_mhi) o.push(f.properties.avg_owner_mhi);
    }
    return {
      renter: r.length ? Math.round(r.reduce((s, v) => s + v, 0) / r.length) : 54000,
      owner: o.length ? Math.round(o.reduce((s, v) => s + v, 0) / o.length) : 118000,
    };
  })();

  // ── Eviction-cause donut data (citywide, computed from evictionDots) ──
  $: evictionCauseSlices = (() => {
    if (!Array.isArray(evictionDots) || evictionDots.length === 0) return null;
    const counts = new Map();
    for (const d of evictionDots) {
      const c = (d.case_type || 'Other').trim();
      counts.set(c, (counts.get(c) || 0) + 1);
    }
    const total = [...counts.values()].reduce((a, b) => a + b, 0);
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const palette = ['#c0392b', '#e67e22', '#f1c40f', '#2563eb', '#888888'];
    const top = sorted.slice(0, 4);
    const restSum = sorted.slice(4).reduce((s, [, v]) => s + v, 0);
    const slices = top.map(([label, value], i) => ({ label, value, color: palette[i] }));
    if (restSum > 0) slices.push({ label: 'Other', value: restSum, color: palette[palette.length - 1] });
    const top1 = sorted[0];
    return {
      slices,
      total,
      topLabel: top1 ? top1[0] : null,
      topPct: top1 ? Math.round((top1[1] / total) * 100) : null,
    };
  })();

  // ── Step-3 sub-scroll: phase + derived progress values ─────────────────
  // Scroll timeline: rent chart draws from 0 → 0.40, then a pause zone from
  // 0.40 → 0.60 (both charts sit still so the reader can take a breath),
  // then the income chart starts drawing from 0.60 → 1.00.
  $: priceP = stepProgresses[4] ?? 0;
  $: pricePhase = priceP >= 0.6 ? 'income' : 'rent';
  $: rentProgress = Math.min(1, Math.max(0, priceP / 0.40));
  $: incomeProgress = Math.min(1, Math.max(0, (priceP - 0.60) / 0.40));
  // Bars share one scale: the largest value across renter + owner across all
  // neighborhood rows + the Boston row. Owner bars sit underneath, renter
  // bars overlay on top.
  $: focusIncomeMax = (() => {
    const vals = [];
    for (const r of focusIncome) {
      if (r.renter) vals.push(r.renter);
      if (r.owner) vals.push(r.owner);
    }
    if (bostonMedians.renter) vals.push(bostonMedians.renter);
    if (bostonMedians.owner) vals.push(bostonMedians.owner);
    return vals.length ? Math.max(...vals) : 1;
  })();
  // Boston-median row reveals once the user scrolls a little past the start
  // of the income phase, in a tight window for visible snap-in.
  $: bostonBarProgress = Math.min(1, Math.max(0, (incomeProgress - 0.25) / 0.15));
  $: bostonRenterW = focusIncomeMax ? bostonMedians.renter / focusIncomeMax * 100 : 0;
  $: bostonOwnerW = focusIncomeMax ? bostonMedians.owner / focusIncomeMax * 100 : 0;

  // ── Prepare chart data ─────────────────────────────────────────────────
  $: corpLines = storyData ? [
    {
      label: 'Corporate',
      color: '#e67e22',
      data: storyData.citywide.corp_ownership.map(d => ({ x: d.year, y: d.rate })),
    },
    {
      label: 'Owner-Occupied',
      color: '#2563eb',
      data: storyData.citywide.owner_occupancy.map(d => ({ x: d.year, y: d.rate })),
    },
  ] : [];

  $: indToCorpLines = storyData ? [
    {
      label: 'Ind→Corp Rate',
      color: '#e67e22',
      data: storyData.citywide.ind_to_corp_rate.map(d => ({ x: d.year, y: d.rate })),
    },
  ] : [];

  $: investorBarData = storyData?.citywide?.investor_types?.map(d => ({
    year: d.year,
    institutional: d.institutional || 0,
    large: d.large || 0,
    medium: d.medium || 0,
    small: d.small || 0,
    non_investor: d.non_investor || d['non-investor'] || 0,
  })) ?? [];

  const investorCategories = [
    { key: 'non_investor', label: 'Non-Investor', color: '#2563eb' },
    { key: 'small', label: 'Small Investor', color: '#f4b678' },
    { key: 'medium', label: 'Medium', color: '#e67e22' },
    { key: 'large', label: 'Large', color: '#c26014' },
    { key: 'institutional', label: 'Institutional', color: '#7a3f0d' },
  ];

  // ZORI rent lines for contrasting neighborhoods
  // Citywide median rent: average across all neighborhoods per date
  $: bostonMedianRent = (() => {
    if (!zoriData) return [];
    const perDate = new Map();
    for (const hood in zoriData) {
      for (const d of zoriData[hood]) {
        if (!d.date || !d.rent || d.date < '2016-01-01') continue;
        const b = perDate.get(d.date) || { sum: 0, n: 0 };
        b.sum += d.rent;
        b.n += 1;
        perDate.set(d.date, b);
      }
    }
    return [...perDate.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .filter((_, i) => i % 3 === 0)
      .map(([date, { sum, n }]) => ({
        x: new Date(date).getFullYear() + (new Date(date).getMonth() / 12),
        y: sum / n,
      }));
  })();

  $: rentLines = zoriData ? [
    ...[
      { label: 'Mission Hill', color: '#c0392b', hood: 'Mission Hill' },
      { label: 'Roxbury', color: '#e67e22', hood: 'Roxbury' },
      { label: 'Dorchester', color: '#3498db', hood: 'Dorchester' },
    ].filter(l => zoriData[l.hood]).map(l => ({
      label: l.label,
      color: l.color,
      data: zoriData[l.hood]
        .filter(d => d.date >= '2016-01-01')
        .filter((_, i) => i % 3 === 0) // every 3 months to reduce density
        .map(d => ({ x: new Date(d.date).getFullYear() + (new Date(d.date).getMonth() / 12), y: d.rent })),
    })),
    ...(bostonMedianRent.length
      ? [{ label: 'Boston median', color: '#1a1a1a', data: bostonMedianRent }]
      : []),
  ] : [];

  // ── Scroll observer ────────────────────────────────────────────────────
  onMount(async () => {
    await tick();

    function onScroll() {
      const steps = document.querySelectorAll('.story-scroll-step');
      if (steps.length === 0) return;
      const vh = window.innerHeight;
      const mid = vh / 2;

      let active = 0;
      for (const el of steps) {
        const rect = el.getBoundingClientRect();
        if (rect.top < mid && rect.bottom > mid) {
          active = parseInt(el.dataset.step, 10);
          const isTall = el.classList.contains('tall');
          let rawProgress;
          if (isTall) {
            // Tall (sticky) step: progress maps the full scroll range from
            // step-top-at-viewport-top to step-bottom-at-viewport-bottom.
            const scrolled = -rect.top;
            const scrollable = rect.height - vh;
            rawProgress = scrollable > 0 ? scrolled / scrollable : 1;
          } else {
            rawProgress = (mid - rect.top) / (rect.height * 0.5);
          }
          stepProgresses[active] = Math.max(0, Math.min(1, rawProgress));
          stepProgresses = stepProgresses;
          break;
        }
      }
      scrollStep = active;
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  });
</script>

<div class="story-intro">
  <!-- Step 0: Hero — what's this all about -->
  <div class="story-scroll-step" data-step="0">
    <div class="story-section hero-section" class:active={scrollStep === 0}>
      <div class="hero-inner">
        <span class="hero-eyebrow">Boston Housing · 2004–2024</span>
        <h1 class="hero-title">Things are changing<br/>rapidly in Boston.</h1>
        <p class="hero-lede">
          <strong>Investors</strong> are buying up the city's rental housing.
          <strong>Rents</strong> have jumped past what most renters earn.
          And <strong class="hero-accent">evictions</strong> are piling up in the
          neighborhoods feeling it hardest. Let us walk you through what
          changed, who's driving it, and where it's hitting.
        </p>
        <div class="hero-arrow" aria-hidden="true">↓ Scroll to begin</div>
      </div>
    </div>
  </div>

  <!-- Step 1: A short, trust-building note about the data -->
  <div class="story-scroll-step" data-step="1">
    <div class="story-section trust-section" class:active={scrollStep === 1}>
      <div class="trust-card">
        <div class="trust-eyebrow">Where this data comes from</div>
        <p class="trust-lede">
          Everything you're about to see is built from <strong>public,
          authoritative sources</strong> — Metro Boston property sales, MA
          Trial Court eviction filings, City of Boston assessment rolls,
          Zillow's rent index, and US Census tract geometry. We've cleaned,
          joined, and aggregated them, but the raw ground truth is open —
          you can verify any of it yourself.
        </p>
        <p class="trust-cta">
          The full list of sources lives at the bottom of this page, and is
          one click away on every page via the
          <strong>References</strong> button.
        </p>
        <div class="trust-arrow" aria-hidden="true">↓ Continue</div>
      </div>
    </div>
  </div>

  <!-- Step 2: Boston's Corporate Takeover — ownership trend -->
  <div class="story-scroll-step" data-step="2">
    <div class="story-section" class:active={scrollStep === 2}>
      <div class="story-text">
        <h1>Boston's Corporate Takeover</h1>
        <p>
          Over the past 20 years, corporate entities have steadily acquired
          Boston's rental housing. Corporate ownership has risen from
          <strong style="color:#e67e22;">5.5% in 2004</strong> to
          <strong style="color:#e67e22;">25.3% in 2024</strong> —
          nearly a 5× increase. Meanwhile, owner-occupancy has declined
          from 43.6% to 38%.
        </p>
        <p class="detail">
          In 9 neighborhoods, corporate ownership now <em>exceeds</em>
          owner-occupancy — a reversal that was unthinkable two decades ago.
        </p>
        <p class="detail">
          That combination matters. An owner-occupant has every reason to
          stabilize a building: their neighbors are their neighbors, and a
          rent hike means losing them. A corporate owner is running a
          portfolio — units are line items, and the fastest way to lift
          returns is to <strong>raise rent to market</strong>, replace the
          long-term tenant with someone who'll pay it, and repeat. As more
          buildings shift from the first model to the second, rents climb
          faster than wages and tenants who can't keep up get
          <em>pushed out</em>. The line chart on the right is the leading
          indicator; the eviction map you'll see later is the trailing one.
        </p>
      </div>
      <div class="story-chart">
        <AnimatedLineChart
          lines={corpLines}
          progress={scrollStep >= 2 ? Math.max(stepProgresses[2], scrollStep > 2 ? 1 : 0) : 0}
          yFormat={v => (v * 100).toFixed(0) + '%'}
          xFormat={v => String(Math.round(v))}
          yLabel="Rate"
          width={520}
          height={300}
        />
      </div>
    </div>
  </div>

  <!-- Step 2: Who's Buying — Sankey-style flow diagram -->
  <div class="story-scroll-step" data-step="3">
    <div class="story-section flow-section" class:active={scrollStep === 3}>
      <div class="story-text">
        <h1>Who's Buying?</h1>
        <p>
          Every property sale in Boston flows between two types of owners:
          <strong style="color:#2563eb;">individuals</strong> and
          <strong style="color:#e67e22;">corporate</strong> entities.
        </p>
        {#if saleFlowDiagram}
          {@const b = saleFlowDiagram.baseline}
          {@const n = saleFlowDiagram.latest}
          <ul class="flow-list">
            <li>
              <div class="fl-head">
                <span class="fl-name" style="color:#e67e22;">Ind → Corp ▲</span>
                <span class="fl-val">{(b.ind_to_corp * 100).toFixed(1)}% → <strong>{(n.ind_to_corp * 100).toFixed(1)}%</strong></span>
              </div>
              <div class="fl-implication">
                Family-owned homes are being <strong>handed over to LLCs</strong> at 5× the rate of two decades ago. Each transfer permanently removes a unit from the individual-owner stock.
              </div>
            </li>
            <li>
              <div class="fl-head">
                <span class="fl-name" style="color:#e67e22;">Corp → Corp ▲</span>
                <span class="fl-val">{(b.corp_to_corp * 100).toFixed(1)}% → <strong>{(n.corp_to_corp * 100).toFixed(1)}%</strong></span>
              </div>
              <div class="fl-implication">
                Once an LLC owns a building, the next sale tends to be to <strong>another LLC</strong>. Corporate ownership is consolidating internally — properties stay inside the corporate market and rarely return to individuals.
              </div>
            </li>
            <li>
              <div class="fl-head">
                <span class="fl-name" style="color:#888;">Corp → Ind</span>
                <span class="fl-val">{(b.corp_to_ind * 100).toFixed(1)}% → <strong>{(n.corp_to_ind * 100).toFixed(1)}%</strong></span>
              </div>
              <div class="fl-implication">
                The reverse pipeline is essentially <strong>flat</strong> — corporate sellers rarely hand properties back to individual buyers. Whatever moves into corporate hands tends to stay there.
              </div>
            </li>
            <li>
              <div class="fl-head">
                <span class="fl-name" style="color:#2563eb;">Ind → Ind ▼</span>
                <span class="fl-val">{(b.ind_to_ind * 100).toFixed(1)}% → <strong>{(n.ind_to_ind * 100).toFixed(1)}%</strong></span>
              </div>
              <div class="fl-implication">
                The traditional <strong>family-to-family</strong> sale — once nine of every ten transactions — is shrinking. Boston's housing market is quietly <strong>losing its individual-owner core</strong>.
              </div>
            </li>
          </ul>
        {/if}
      </div>
      <div class="story-chart">
        {#if saleFlowDiagram}
          <FlowDiagram
            baseline={saleFlowDiagram.baseline}
            latest={saleFlowDiagram.latest}
            baselineYear={saleFlowDiagram.baselineYear}
            latestYear={saleFlowDiagram.latestYear}
            progress={scrollStep >= 3 ? Math.max(stepProgresses[3], scrollStep > 3 ? 1 : 0) : 0}
          />
        {/if}
      </div>
    </div>
  </div>

  <!-- Step 3: The Price You Pay — sub-scroll between rent and income views -->
  <div class="story-scroll-step tall" data-step="4">
    <div class="price-sticky">
      <div class="story-section" class:active={scrollStep === 4}>
        <div class="story-text">
          <h1>The Price You Pay</h1>
          {#if pricePhase === 'rent'}
            <p>
              As corporate ownership rises, so do rents. The sharpest climbs
              cluster in just a few neighborhoods —
              <strong style="color:#c0392b;">Mission Hill</strong>,
              <strong style="color:#e67e22;">Roxbury</strong>, and
              <strong style="color:#3498db;">Dorchester</strong> lead the
              list.
            </p>
            <p class="detail">
              Keep scrolling ↓ to see what the renters in those same
              neighborhoods actually earn.
            </p>
          {:else}
            <p>
              Now the other half of the picture: the median income of
              renters in the same three neighborhoods. The people absorbing
              the steepest rent hikes are often the ones with the least
              room to absorb them.
            </p>
          {/if}
        </div>
        <div class="story-chart">
          {#if pricePhase === 'rent'}
            <div in:fade={{ duration: 380 }} out:fade={{ duration: 220 }}>
              <AnimatedLineChart
                lines={rentLines}
                progress={rentProgress}
                yFormat={v => '$' + Math.round(v).toLocaleString()}
                xFormat={v => String(Math.round(v))}
                yLabel="Monthly Rent"
                width={520}
                height={300}
              />
            </div>
          {:else if focusIncome.length}
            <div in:fade={{ duration: 380, delay: 100 }} out:fade={{ duration: 220 }} class="income-compare">
              <div class="income-caption">
                Median household income, by tenure
              </div>
              {#each focusIncome as row, i}
                {@const revealed = incomeProgress >= i * 0.05}
                {@const color = i === 0 ? '#c0392b' : i === 1 ? '#e67e22' : '#3498db'}
                {@const ownerW = (row.owner ?? 0) / focusIncomeMax * 100}
                {@const renterW = (row.renter ?? 0) / focusIncomeMax * 100}
                <div class="income-row" class:revealed>
                  <span class="income-name">{row.name}</span>
                  <div class="income-bar">
                    <div class="owner-fill" style="width:{ownerW}%"></div>
                    <div class="renter-fill" style="width:{renterW}%; background:{color}"></div>
                  </div>
                  <span class="income-val">
                    <span class="renter-val" style="color:{color}">
                      <span class="tenure-tag" style="color:{color}">Renter</span>
                      ${(row.renter ?? 0).toLocaleString()}
                    </span>
                    <span class="owner-val">
                      <span class="tenure-tag muted">Owner</span>
                      ${(row.owner ?? 0).toLocaleString()}
                    </span>
                  </span>
                </div>
              {/each}
              <div class="income-row boston" class:revealed={bostonBarProgress > 0.05}>
                <span class="income-name boston-name">Boston<br/>median</span>
                <div class="income-bar">
                  <div class="owner-fill boston-owner"
                    style="width:{bostonOwnerW * bostonBarProgress}%"></div>
                  <div class="renter-fill boston-renter"
                    style="width:{bostonRenterW * bostonBarProgress}%"></div>
                </div>
                <span class="income-val">
                  <span class="renter-val">
                    <span class="tenure-tag">Renter</span>
                    ${bostonMedians.renter.toLocaleString()}
                  </span>
                  <span class="owner-val">
                    <span class="tenure-tag muted">Owner</span>
                    ${bostonMedians.owner.toLocaleString()}
                  </span>
                </span>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- Step 4: When Rent Outruns Income — Evictions -->
  <div class="story-scroll-step" data-step="5">
    <div class="story-section eviction-section" class:active={scrollStep === 5}>
      <div class="story-text">
        <h1>When Rent Outruns Income</h1>
        <p>
          Between 2020 and 2024, Massachusetts courts logged
          <strong>over 6,000 eviction filings</strong> in Boston alone.
          The most common cause isn't lease violations or property damage —
          it's simply <em>non-payment of rent</em>.
        </p>
        <p class="detail">
          As corporate landlords consolidate and rents climb, more tenants
          fall short on the first of the month. Across the city,
          <strong>roughly two out of every three eviction cases</strong>
          cite unpaid rent as the reason, and corporate landlords file the
          majority of them.
        </p>
      </div>
      {#if evictionCauseSlices}
        <div class="cause-pie">
          <DonutChart
            slices={evictionCauseSlices.slices}
            size={180}
            thickness={32}
            centerValue="{Math.round(evictionCauseSlices.topPct * (scrollStep >= 5 ? Math.max(stepProgresses[5], scrollStep > 5 ? 1 : 0) : 0))}%"
            centerLabel="non-payment"
            progress={scrollStep >= 5 ? Math.max(stepProgresses[5], scrollStep > 5 ? 1 : 0) : 0}
          />
        </div>
      {/if}
    </div>
  </div>

  <!-- Step 5: Who's Really Filing — normalized corp vs individual -->
  <div class="story-scroll-step" data-step="6">
    <div class="story-section ovf-section" class:active={scrollStep === 6}>
      <div class="story-text">
        <h1>Who's Really Filing?</h1>
        <p>
          Corporate landlords make up roughly a fifth of Boston's rental ownership.
          They file the overwhelming majority of its evictions. Normalizing filings
          to ownership share makes the gap impossible to miss —
          <strong style="color:#e67e22;">corps file evictions at several times
          their share of the market</strong>, and individual landlords file well
          under theirs, every single year.
        </p>
        <p class="detail">
          Each row below shows one year: what share of Boston rentals corporations
          owned vs. what share of evictions they filed. The <strong>ratio</strong>
          column is how many times above their fair share corps filed that year.
        </p>
      </div>
      <OwnershipVsFilings
        evictionDots={evictionDots}
        corpOwnership={storyData?.citywide?.corp_ownership ?? []}
        progress={scrollStep >= 6 ? Math.max(stepProgresses[6], scrollStep > 6 ? 1 : 0) : 0}
      />
    </div>
  </div>

  <!-- Step 6: CTA -->
  <div class="story-scroll-step" data-step="7">
    <div class="story-section cta-section" class:active={scrollStep === 7}>
      <h1>Let's Look Closer</h1>
      <p>
        The next page is about <strong>eviction</strong> — where it's
        happening, who's filing it, and who's being pushed out. On the
        map you're about to see, each
        <span class="dot-inline blue"></span>
        <strong class="blue-strong">blue dot</strong> is one eviction filing.
      </p>
      <p>
        We'll take you through <strong>6 neighborhoods</strong> — each
        with a different story about what investor activity and rising
        rent mean for the people who live there.
      </p>
      <button class="cta-btn" on:click={() => dispatch('enterDeepDive')}>
        Explore the Neighborhoods
      </button>

      <div class="cta-footnote">
        <span>Built from MAPC sales · MA Trial Court evictions · Boston assessment rolls · Zillow ZORI · BPDA + Census.</span>
        <button class="cta-refs-link" on:click={openReferences}>
          See full references ↗
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .story-intro {
    background: #fafafa;
  }

  .story-scroll-step {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 60px;
  }

  .story-section {
    display: flex;
    gap: 48px;
    max-width: 1100px;
    width: 100%;
    align-items: center;
    opacity: 0.3;
    transform: translateY(20px);
    transition: opacity 0.5s ease, transform 0.5s ease;
  }

  .story-section.active {
    opacity: 1;
    transform: translateY(0);
  }

  .story-section.cta-section {
    flex-direction: column;
    text-align: center;
    max-width: 600px;
  }

  .story-text {
    flex: 1;
    min-width: 280px;
  }

  .story-chart {
    flex: 0 0 auto;
  }

  h1 {
    font-size: 2rem;
    font-weight: 800;
    color: #1a1a1a;
    margin-bottom: 16px;
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  p {
    font-size: 1.05rem;
    color: #444;
    line-height: 1.8;
    margin-bottom: 12px;
  }

  p.detail {
    font-size: 0.92rem;
    color: #666;
  }

  p :global(strong) {
    color: #2d8c2d;
    font-weight: 700;
  }

  p :global(em) {
    color: #c0392b;
    font-style: normal;
    font-weight: 600;
  }

  .ovf-section {
    flex-direction: column;
    max-width: 820px;
    gap: 28px;
    align-items: stretch;
  }
  .ovf-section .story-text { min-width: 0; }

  .trust-section {
    flex-direction: column;
    max-width: 720px;
    padding: 40px 24px;
  }
  .trust-card {
    width: 100%;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #e67e22;
    border-radius: 10px;
    padding: 28px 32px;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.05);
  }
  .trust-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888;
    margin-bottom: 10px;
  }
  .trust-lede {
    font-size: 1rem !important;
    color: #1a1a1a !important;
    line-height: 1.7 !important;
    margin: 0 0 12px !important;
  }
  .trust-cta {
    font-size: 0.85rem !important;
    color: #555 !important;
    line-height: 1.6 !important;
    margin: 0 !important;
  }
  .trust-arrow {
    margin-top: 18px;
    text-align: center;
    font-size: 0.8rem;
    color: #999;
    letter-spacing: 0.05em;
  }
  @media (max-width: 700px) {
    .trust-card { padding: 22px 20px; }
  }

  .cta-footnote {
    margin-top: 28px;
    padding-top: 20px;
    border-top: 1px solid #e8e8e8;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    text-align: center;
    max-width: 580px;
  }
  .cta-footnote span {
    font-size: 0.74rem;
    color: #999;
    line-height: 1.5;
    font-style: italic;
  }
  .cta-refs-link {
    background: none;
    border: none;
    color: #2563eb;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    padding: 4px 8px;
    text-decoration: underline;
  }
  .cta-refs-link:hover { color: #1d4dbf; }

  .hero-section {
    flex-direction: column;
    max-width: 780px;
    gap: 0;
    padding: 20px 24px;
  }
  .hero-inner {
    display: flex;
    flex-direction: column;
    gap: 18px;
    text-align: center;
  }
  .hero-eyebrow {
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #c0392b;
    align-self: center;
  }
  .hero-title {
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.08;
    letter-spacing: -0.02em;
    color: #1a1a1a;
    margin: 0;
  }
  .hero-lede {
    font-size: 1.2rem !important;
    line-height: 1.7 !important;
    color: #333 !important;
    max-width: 640px;
    margin: 0 auto !important;
  }
  .hero-accent {
    color: #c0392b !important;
  }
  .hero-arrow {
    margin-top: 10px;
    font-size: 0.85rem;
    color: #888;
    letter-spacing: 0.05em;
  }
  @media (max-width: 900px) {
    .hero-title { font-size: 2.1rem; }
    .hero-lede { font-size: 1rem !important; }
  }

  .story-scroll-step.tall {
    min-height: 200vh;
    padding: 0;
    align-items: flex-start;
  }
  .price-sticky {
    position: sticky;
    top: 0;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 40px 60px;
  }

  .income-compare {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 520px;
    max-width: 100%;
    padding: 18px 22px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 2px 14px rgba(0,0,0,0.05);
  }
  .income-caption {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-bottom: 2px;
  }
  .income-row {
    display: grid;
    grid-template-columns: 110px 1fr 170px;
    gap: 12px;
    align-items: center;
    font-size: 0.88rem;
    opacity: 0;
    transform: translateX(-6px);
    transition: opacity 0.4s, transform 0.4s;
  }
  .income-row.revealed { opacity: 1; transform: translateX(0); }
  .income-name { font-weight: 700; color: #1a1a1a; }
  .income-bar {
    position: relative;
    height: 24px;
    background: #f1f1f1;
    border-radius: 12px;
    overflow: hidden;
  }
  .owner-fill {
    position: absolute;
    inset: 0 auto 0 0;
    height: 100%;
    background: #d6dee8;
    border-radius: 12px;
    transition: width 0.55s cubic-bezier(0.2, 0.9, 0.3, 1);
  }
  .renter-fill {
    position: absolute;
    inset: 4px auto 4px 0;
    height: calc(100% - 8px);
    border-radius: 8px;
    transition: width 0.55s cubic-bezier(0.2, 0.9, 0.3, 1);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  }
  .income-val {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    line-height: 1.15;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .renter-val { font-weight: 700; }
  .owner-val { font-weight: 500; color: #888; font-size: 0.78rem; }
  .tenure-tag {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 5px;
  }
  .tenure-tag.muted { color: #aaa; }
  .income-tenure-key {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 0.72rem;
    color: #555;
    margin-bottom: 8px;
  }
  .key-item { display: inline-flex; align-items: center; gap: 6px; }
  .key-swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid rgba(0,0,0,0.12);
  }
  .key-swatch.renter {
    background: #2563eb;
  }
  .key-swatch.owner {
    background: #d6dee8;
  }
  .income-row.boston {
    margin-top: 4px;
    padding-top: 10px;
    border-top: 1px dashed #ddd;
  }
  .boston-name { color: #555 !important; font-size: 0.78rem; line-height: 1.1; }
  .boston-renter { background: #2d3748; }
  .boston-owner { background: #c2cad4; }

  .flow-section .story-text,
  .flow-section .story-chart {
    flex: 1 1 0;
    min-width: 280px;
  }
  .flow-section .story-chart { max-width: 640px; }

  .flow-list {
    list-style: none;
    padding: 0;
    margin: 14px 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 380px;
  }
  .flow-list li {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
  }
  .flow-list li:last-child { border-bottom: none; }
  .fl-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    font-size: 0.92rem;
  }
  .fl-name {
    font-weight: 700;
    white-space: nowrap;
  }
  .fl-val {
    color: #666;
    font-variant-numeric: tabular-nums;
    font-size: 0.86rem;
  }
  .fl-val strong { color: #1a1a1a; font-weight: 800; }
  .fl-implication {
    font-size: 0.78rem;
    color: #555;
    line-height: 1.5;
  }
  .fl-implication strong {
    color: #1a1a1a;
    font-weight: 700;
  }

  .eviction-section {
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
  }
  .eviction-section .story-text { flex: 1 1 320px; max-width: 420px; }
  .cause-pie {
    flex: 1 1 460px;
    max-width: 520px;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 14px 16px;
  }
  .story-callout {
    display: flex;
    flex-direction: column;
    gap: 18px;
    flex: 0 0 280px;
    padding: 28px 24px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #c0392b;
    border-radius: 10px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  }
  @media (max-width: 1100px) {
    .cause-pie { flex: 0 0 100%; }
    .story-callout { flex: 0 0 100%; }
  }
  .callout-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .callout-num {
    font-size: 1.9rem;
    font-weight: 800;
    color: #c0392b;
    line-height: 1;
    letter-spacing: -0.01em;
  }
  .callout-label {
    font-size: 0.85rem;
    color: #555;
    line-height: 1.3;
  }

  .dot-inline {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin: 0 2px 1px 2px;
    vertical-align: middle;
    border: 1px solid rgba(0,0,0,0.15);
  }
  .dot-inline.red { background: #c0392b; }
  .dot-inline.green { background: #2d8c2d; }
  .dot-inline.blue { background: #2563eb; }
  .dot-inline.orange { background: #e67e22; }

  p :global(strong.lost), p .lost {
    color: #c0392b !important;
  }
  p :global(strong.blue-strong) {
    color: #2563eb !important;
  }
  p :global(strong.orange-strong) {
    color: #e67e22 !important;
  }

  .cta-btn {
    display: inline-block;
    margin-top: 24px;
    padding: 16px 40px;
    background: #2d8c2d;
    color: #fff;
    border: none;
    border-radius: 10px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s, transform 0.15s;
  }

  .cta-btn:hover {
    background: #236b23;
    transform: translateY(-1px);
  }

  @media (max-width: 900px) {
    .story-section {
      flex-direction: column;
      gap: 24px;
    }
    .story-scroll-step {
      padding: 40px 24px;
    }
    h1 {
      font-size: 1.5rem;
    }
  }
</style>
