<script>
  import { onMount, tick, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import * as d3 from 'd3';

  export let openReferences = () => {};
  import AnimatedLineChart from './AnimatedLineChart.svelte';
  import FlowDiagram from './FlowDiagram.svelte';
  import OwnershipVsFilings from './OwnershipVsFilings.svelte';
  import DonutChart from './DonutChart.svelte';
  import CorpOwnershipMap from './CorpOwnershipMap.svelte';


  const dispatch = createEventDispatcher();

  export let storyData;   // corp_ownership_timeseries.json
  export let zoriData;    // zori_by_neighborhood.json
  export let evictionDots = [];  // eviction case dots, for per-year aggregation
  export let geoData;     // neighborhoods.geojson (for median income)
  export let properties = [];    // property sale records (for corporate-ownership map dots)

  // Hero backdrop: Boston neighborhoods projected to a fixed viewBox,
  // rendered behind the title and pulsed gray ↔ orange.
  const HERO_W = 1400;
  const HERO_H = 760;
  $: heroPaths = (() => {
    if (!geoData?.features?.length) return [];
    const projection = d3.geoMercator().fitSize([HERO_W, HERO_H], geoData);
    const pathGen = d3.geoPath().projection(projection);
    return geoData.features
      .map(f => pathGen(f))
      .filter(Boolean);
  })();

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
  // Map raw legal-jargon case types to plain-language labels readers can grok
  // at a glance. "Cause" / "No Cause" are court terms — readers shouldn't
  // need a glossary to read this chart.
  const CASE_TYPE_LABEL = {
    'Non-payment of Rent': 'Missed rent',
    'Cause': 'Lease violation',
    'No Cause': 'Landlord ended lease',
    'SP Transfer- No Cause': 'Landlord ended lease',
    'Foreclosure': 'Foreclosure',
  };
  $: evictionCauseSlices = (() => {
    if (!Array.isArray(evictionDots) || evictionDots.length === 0) return null;
    const counts = new Map();
    for (const d of evictionDots) {
      const raw = (d.case_type || 'Other').trim();
      const label = CASE_TYPE_LABEL[raw] || raw;
      counts.set(label, (counts.get(label) || 0) + 1);
    }
    const total = [...counts.values()].reduce((a, b) => a + b, 0);
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const palette = ['#c0392b', '#e67e22', '#f1c40f', '#2563eb', '#888888'];
    // Per-label overrides — Foreclosure reads as brown rather than blue.
    const labelColor = {
      'Foreclosure': '#8d6e63',
    };
    const top = sorted.slice(0, 4);
    const restSum = sorted.slice(4).reduce((s, [, v]) => s + v, 0);
    const slices = top.map(([label, value], i) => ({
      label,
      value,
      color: labelColor[label] ?? palette[i],
    }));
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
  $: bostonAnnualRent = bostonLatestRent ? bostonLatestRent * 12 : null;
  $: bostonRentLeft = bostonAnnualRent && focusIncomeMax ? (bostonAnnualRent / focusIncomeMax) * 100 : null;
  $: bostonRentPct = (bostonAnnualRent && bostonMedians.renter)
    ? (bostonAnnualRent / bostonMedians.renter) * 100 : null;

  // Latest monthly rent per focus neighborhood (last ZORI point ≥ 2016)
  $: focusLatestRent = (() => {
    const out = {};
    if (!zoriData) return out;
    for (const name of focusHoods) {
      const series = zoriData[name];
      if (!Array.isArray(series) || series.length === 0) continue;
      const valid = series.filter(d => d.date >= '2016-01-01' && d.rent);
      if (valid.length) out[name] = Math.round(valid[valid.length - 1].rent);
    }
    return out;
  })();
  // Boston-wide latest median monthly rent — same value the rent line chart
  // ends on (last point of bostonMedianRent). Falls back to averaging the
  // latest neighborhood values if that series isn't ready.
  $: bostonLatestRent = (() => {
    if (Array.isArray(bostonMedianRent) && bostonMedianRent.length) {
      return Math.round(bostonMedianRent[bostonMedianRent.length - 1].y);
    }
    const vals = Object.values(focusLatestRent);
    return vals.length ? Math.round(vals.reduce((s, v) => s + v, 0) / vals.length) : null;
  })();

  // Income-axis ticks: pick a "nice" step so the axis spans 0 → focusIncomeMax.
  $: incomeTicks = (() => {
    if (!focusIncomeMax) return [];
    const target = 3;                 // ~3 intervals → ~4 labels, less crowding
    const raw = focusIncomeMax / target;
    const pow10 = Math.pow(10, Math.floor(Math.log10(raw)));
    const m = raw / pow10;
    const step = (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * pow10;
    const ticks = [];
    for (let v = 0; v <= focusIncomeMax + step * 0.5; v += step) ticks.push(v);
    return ticks;
  })();

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
      { label: 'Roxbury', color: '#8e44ad', hood: 'Roxbury' },
      { label: 'Dorchester', color: '#16a085', hood: 'Dorchester' },
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
    <div class="project-credit" aria-label="Project credits">
      <div class="pc-course">6.C85</div>
      <div class="pc-team">Arvind's Angels</div>
      <div class="pc-members">Alex Tung · Nuri Hong · Sumin Byun</div>
    </div>
    <div class="story-section hero-section" class:active={scrollStep === 0}>
      <div class="hero-col text-col">
        <div class="hero-inner">
          <h1 class="hero-title">Things are changing<br/>rapidly in Boston.</h1>
          <p class="hero-lede">Large-scale investors are buying up housing, and rent is rising beyond renters' incomes. All the while, evictions are piling up in some neighborhoods more than others.</p>
          <p class="hero-lede">Let us walk you through what this means.</p>
          <div class="hero-arrow" aria-hidden="true">↓ Scroll to begin</div>
        </div>
      </div>
      <div class="hero-col map-col">
        {#if heroPaths.length}
          <svg
            class="hero-map"
            viewBox="0 0 {HERO_W} {HERO_H}"
            preserveAspectRatio="xMidYMid meet"
            aria-hidden="true"
          >
            <g class="hero-map-shapes">
              {#each heroPaths as d}
                <path {d} />
              {/each}
            </g>
          </svg>
        {/if}
      </div>
    </div>
  </div>

  <!-- Step 2: Boston's Corporate Takeover — ownership trend -->
  <div class="story-scroll-step tall" data-step="2">
    <div class="sticky-wrap">
      <div class="story-section corp-section" class:active={scrollStep === 2}>
        <div class="story-text corp-intro">
          <h1>Boston's Corporate Takeover</h1>
          <p>
            From 2004 to 2024, Corporate ownership has risen 5x, from <strong style="color:#e67e22;">5%</strong> to <strong style="color:#e67e22;">25%</strong>.<br>Meanwhile, owner-occupancy has declined from <strong style="color:#2563eb;"> 43%</strong> to <strong style="color:#2563eb;">38%</strong>.
          </p>
          <p class="detail">
            <strong style="color:#888;">Why is this concerning?</strong> Corporate owners prioritize the maximization of profit: This is best accomplished by favoring short-term leases over long-term tenants.
          </p>
        </div>
        <div class="corp-vis-row">
          <div class="story-chart">
            <AnimatedLineChart
              lines={corpLines}
              progress={scrollStep >= 2 ? Math.max(stepProgresses[2], scrollStep > 2 ? 1 : 0) : 0}
              yFormat={v => (v * 100).toFixed(0) + '%'}
              xFormat={v => String(Math.round(v))}
              yLabel="Rate"
              width={500}
              height={300}
            />
          </div>
          <div class="story-chart">
            <CorpOwnershipMap
              {geoData}
              {properties}
              corpRates={storyData?.citywide?.corp_ownership ?? []}
              progress={scrollStep >= 2 ? Math.max(stepProgresses[2], scrollStep > 2 ? 1 : 0) : 0}
              width={360}
              height={300}
            />
          </div>
        </div>
        <p class="corp-prompt">How are corporate owners steadily acquiring properties?</p>
        <div class="hero-arrow corp-arrow" aria-hidden="true">↓ Scroll on</div>
      </div>
    </div>
  </div>

  <!-- Step 2: Who's Buying — Sankey-style flow diagram -->
  <div class="story-scroll-step tall" data-step="3">
    <div class="sticky-wrap">
    <div class="story-section flow-section" class:active={scrollStep === 3}>
      <div class="flow-intro">
        <h1>Who's Buying?</h1>
        <p>
          Every property sale in Boston flows between two classes:
          <strong style="color:#2563eb;">individual owners</strong> and
          <strong style="color:#e67e22;">corporate entities</strong>.
          Properties stay in corporate ownership and rarely return to individuals,
          and Boston's housing market is losing its individual-owner core.
        </p>
      </div>
      {#if saleFlowDiagram}
        {@const b = saleFlowDiagram.baseline}
        {@const n = saleFlowDiagram.latest}
        <div class="flow-with-stats">
          <div class="flow-chart-wrap">
            <FlowDiagram
              baseline={saleFlowDiagram.baseline}
              latest={saleFlowDiagram.latest}
              baselineYear={saleFlowDiagram.baselineYear}
              latestYear={saleFlowDiagram.latestYear}
              progress={scrollStep >= 3 ? Math.max(stepProgresses[3], scrollStep > 3 ? 1 : 0) : 0}
            />
          </div>
          <div class="flow-stats">
            <ul class="flow-stat-group flow-stat-top">
              <li class="flow-stat">
                <div class="fl-head">
                  <span class="fl-name"><span class="gray">Individual-to-</span><span class="corp">Corporate</span></span>
                  <span class="fl-val">{(b.ind_to_corp * 100).toFixed(1)}% → <strong>{(n.ind_to_corp * 100).toFixed(1)}%</strong> ▲</span>
                </div>
                <div class="fl-implication">
                  Family-owned homes are being <strong>sold to corporate buyers</strong> at 5x the rate of two decades ago.
                </div>
              </li>
              <li class="flow-stat">
                <div class="fl-head">
                  <span class="fl-name"><span class="gray">Corporate-to-</span><span class="corp">Corporate</span></span>
                  <span class="fl-val">{(b.corp_to_corp * 100).toFixed(1)}% → <strong>{(n.corp_to_corp * 100).toFixed(1)}%</strong> ▲</span>
                </div>
                <div class="fl-implication">
                  Sales from corporate owners tend to be made <strong>to other corporate entities</strong>.
                </div>
              </li>
            </ul>
            <ul class="flow-stat-group flow-stat-bot">
              <li class="flow-stat">
                <div class="fl-head">
                  <span class="fl-name"><span class="gray">Corporate-to-</span><span class="ind">Individual</span></span>
                  <span class="fl-val">{(b.corp_to_ind * 100).toFixed(1)}% → <strong>{(n.corp_to_ind * 100).toFixed(1)}%</strong> ▼</span>
                </div>
                <div class="fl-implication">
                  While some properties return to individual landlords, this percentage is slowly decreasing.
                </div>
              </li>
              <li class="flow-stat">
                <div class="fl-head">
                  <span class="fl-name"><span class="gray">Individual-to-</span><span class="ind">Individual</span></span>
                  <span class="fl-val">{(b.ind_to_ind * 100).toFixed(1)}% → <strong>{(n.ind_to_ind * 100).toFixed(1)}%</strong> ▼</span>
                </div>
                <div class="fl-implication">
                  Traditional "family-to-family sales" are decreasing over time.
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div class="hero-arrow flow-arrow" aria-hidden="true">↓ Scroll on</div>
      {/if}
    </div>
    </div>
  </div>

  <!-- Step 3: The Price You Pay — sub-scroll between rent and income views -->
  <div class="story-scroll-step tall" data-step="4">
    <div class="sticky-wrap">
      <div class="story-section" class:active={scrollStep === 4}>
        <div class="story-text">
          <h1>The Price You Pay</h1>
          {#if pricePhase === 'rent'}
            <p>
              As corporate ownership rises, so do rents. The sharpest climbs
              cluster in just a few neighborhoods —
              <strong style="color:#c0392b;">Mission Hill</strong>,
              <strong style="color:#8e44ad;">Roxbury</strong>, and
              <strong style="color:#16a085;">Dorchester</strong> lead the
              list.
            </p>
            <p><br>How much do renters in these same neighborhoods earn?</p>
            <div class="hero-arrow" aria-hidden="true">↓ Scroll on</div>
            
          {:else}
            <p>The people absorbing the steepest rent hikes are often the ones with the least room to absorb them.</p>
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
                Median household income
              </div>
              {#each focusIncome as row, i}
                {@const revealed = incomeProgress >= i * 0.05}
                {@const color = i === 0 ? '#c0392b' : i === 1 ? '#8e44ad' : '#16a085'}
                {@const ownerW = (row.owner ?? 0) / focusIncomeMax * 100}
                {@const renterW = (row.renter ?? 0) / focusIncomeMax * 100}
                {@const monthlyRent = focusLatestRent[row.name]}
                {@const annualRent = monthlyRent ? monthlyRent * 12 : null}
                {@const rentMarkerLeft = annualRent ? (annualRent / focusIncomeMax) * 100 : null}
                {@const rentPctOfIncome = (annualRent && row.renter) ? (annualRent / row.renter) * 100 : null}
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
                <span class="income-name boston-name">Boston<br/>Median</span>
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

              <!-- Shared income-axis tick row -->
              {#if incomeTicks.length}
                <div class="income-row tick-row">
                  <span class="income-name"></span>
                  <div class="tick-axis">
                    {#each incomeTicks as t}
                      <div class="tick" style="left:{(t / focusIncomeMax) * 100}%">
                        <span class="tick-line"></span>
                        <span class="tick-label">${(t >= 1000 ? Math.round(t / 1000) + 'k' : t)}</span>
                      </div>
                    {/each}
                  </div>
                  <span class="income-val tick-cap">household income</span>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- Step 4: When Rent Outruns Income — Evictions -->
  <div class="story-scroll-step tall" data-step="5">
    <div class="sticky-wrap">
      <div class="story-section eviction-section" class:active={scrollStep === 5}>
        <div class="story-text">
          <h1>When Rent Outruns Income</h1>
          <p>
            Out of over 6,000 eviction filings filed in Boston between 2020 and 2024, the most common reason is simple: tenants <em>missed rent</em>.
          </p>
          <p class="detail">
            Tenants may miss rent for a variety of personal reasons -- but as corporate landlords consolidate and rents climb, more tenants fall short on rent.
          </p>
          <p><br>Who files these evictions?</p>
          <div class="hero-arrow" aria-hidden="true">↓ Scroll on</div>
        </div>
        {#if evictionCauseSlices}
          <div class="cause-pie">
            <DonutChart
              slices={evictionCauseSlices.slices}
              size={180}
              thickness={32}
              centerValue="{Math.round(evictionCauseSlices.topPct * (scrollStep >= 5 ? Math.max(stepProgresses[5], scrollStep > 5 ? 1 : 0) : 0))}%"
              centerLabel="missed rent"
              progress={scrollStep >= 5 ? Math.max(stepProgresses[5], scrollStep > 5 ? 1 : 0) : 0}
            />
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Step 5: Who's Really Filing — normalized corp vs individual -->
  <div class="story-scroll-step tall" data-step="6">
    <div class="sticky-wrap">
      <div class="story-section ovf-section" class:active={scrollStep === 6}>
        <div class="story-text">
          <h1>Who's Filing Evictions?</h1>
          <p>
            Although corporate entities make up roughly 1/5 of Boston's ownership, they file an overwhelming majority of tenant evictions. By normalizing filings
            by ownership share, it is apparent that <strong style="color:#e67e22;">corporate landlords file evictions at several times their share of the market</strong>.
          </p>
          <div class="ftor-eqn" aria-label="Filings to Ownership Ratio formula">
            <span class="ftor-name">Filings&#8209;to&#8209;Ownership Ratio (FTOR)</span>
            <span class="ftor-eq">=</span>
            <span class="ftor-frac">
              <span class="ftor-num">Eviction Filings</span>
              <span class="ftor-bar"></span>
              <span class="ftor-den">Ownership Share</span>
            </span>
          </div>
          <p class="detail">
            For each year of available data, corporate landlords consistently file roughly <strong style="color:#e67e22;">seven in ten evictions</strong>. The same proportion of filing rate is divided across a larger ownership base, as the filings share (numerator) stays nearly constant while the ownership share (denominator) continues climbing.
          </p>
        </div>
        <OwnershipVsFilings
          evictionDots={evictionDots}
          corpOwnership={storyData?.citywide?.corp_ownership ?? []}
          progress={scrollStep >= 6 ? Math.max(stepProgresses[6], scrollStep > 6 ? 1 : 0) : 0}
        />
      </div>
    </div>
  </div>

  <!-- Step 6: CTA -->
  <div class="story-scroll-step" data-step="7">
    <div class="story-section cta-section" class:active={scrollStep === 7}>
      <h1>Let's Look Closer.</h1>
      <p class="cta-recap">
        So far we've watched corporate ownership <strong style="color:#e67e22;">climb five-fold</strong>, properties flow steadily <strong style="color:#e67e22;">from individual to corporate hands</strong>, rents <strong style="color:#e67e22;">outrun the incomes of the renters</strong>, and corporate landlords <strong style="color:#e67e22;">filing evictions disproportionately above their share of the market</strong>. These are citywide numbers that tell the shape of the problem, but they flatten the human story behind each filing.
      </p>
      <p>We'll take you through <strong>six neighborhoods</strong>, each with a different story. For each of these neighborhoods, eviction data reveals the effect of investor activity on the people who live there.</p>
      <button class="cta-btn" on:click={() => dispatch('enterDeepDive')}>
        Explore Neighborhoods
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

  .cta-recap {
    margin-bottom: 8px;
    font-size: 1rem !important;
    line-height: 1.7 !important;
    color: #444 !important;
  }
  .cta-recap :global(strong) { font-weight: 700; }

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

  .ftor-eqn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin: 18px auto;
    padding: 14px 22px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #e67e22;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
    color: #1a1a1a;
    font-variant-numeric: tabular-nums;
    flex-wrap: wrap;
    text-align: center;
  }
  .ftor-name {
    font-weight: 700;
    font-size: 0.95rem;
  }
  .ftor-eq {
    font-size: 1.4rem;
    font-weight: 700;
    color: #888;
  }
  .ftor-frac {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    line-height: 1.2;
    font-weight: 600;
    font-size: 0.92rem;
  }
  .ftor-num,
  .ftor-den {
    padding: 2px 8px;
    white-space: nowrap;
    color: #1a1a1a;
  }
  .ftor-bar {
    height: 2px;
    background: #1a1a1a;
    width: 100%;
    min-width: 140px;
    border-radius: 1px;
    margin: 2px 0;
  }

  .corp-section {
    flex-direction: column;
    align-items: stretch;
    text-align: left;
    max-width: 1020px;
    gap: 24px;
    /* Anchor near the top of the sticky viewport so the heading sits
       higher on the screen. */
    align-self: flex-start;
    margin-top: 24px;
  }
  .corp-intro {
    max-width: 900px;
    min-width: 0;
  }
  .corp-intro p :global(strong) { color: inherit; }
  .corp-vis-row {
    display: flex;
    flex-wrap: wrap;
    gap: 32px;
    align-items: center;
    justify-content: center;
    width: 100%;
  }
  .corp-prompt {
    margin: 0;
    font-size: 1.05rem;
    color: #444;
    text-align: left;
  }
  .corp-arrow {
    margin-top: 4px;
    text-align: left;
  }
  @media (max-width: 900px) {
    .corp-vis-row { gap: 20px; }
  }

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
  .trust-lede-list {
    font-size: 1rem !important;
    color: #1a1a1a !important;
    line-height: 1.7 !important;
    margin: 0 0 12px 36px !important;
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
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 0;
    width: 100%;
    max-width: none;
    padding: 20px 0;
    position: relative;
    isolation: isolate;
  }
  .hero-col {
    flex: 1 1 50%;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 24px;
  }
  /* Pull the text column toward the middle of the screen — anchored to the
     right edge of the left half rather than centered in it. */
  .hero-col.text-col {
    justify-content: flex-end;
    padding-right: 56px;
  }
  .hero-col.map-col {
    justify-content: flex-start;
    padding-left: 24px;
  }
  .project-credit {
    position: absolute;
    top: 18px;
    right: 22px;
    text-align: right;
    z-index: 2;
    line-height: 1.25;
    font-family: 'Inter', system-ui, sans-serif;
    color: #444;
    pointer-events: none;
  }
  .pc-course {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888;
  }
  .pc-team {
    font-size: 0.86rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-top: 1px;
  }
  .pc-members {
    font-size: 0.7rem;
    color: #666;
    margin-top: 2px;
  }
  @media (max-width: 700px) {
    .project-credit { top: 12px; right: 14px; }
    .pc-course { font-size: 0.62rem; }
    .pc-team { font-size: 0.76rem; }
    .pc-members { font-size: 0.62rem; }
  }
  .hero-map {
    width: 100%;
    max-width: 760px;
    height: auto;
    pointer-events: none;
    opacity: 0.95;
  }
  @media (max-width: 900px) {
    .hero-section { flex-direction: column; gap: 28px; padding: 20px 24px; }
    .hero-col { flex: 1 1 auto; width: 100%; padding: 0; }
    .hero-map { max-width: min(520px, 86vw); }
  }
  .hero-map-shapes path {
    fill: #d9d9d9;
    stroke: #aaa;
    stroke-width: 0.8;
    stroke-linejoin: round;
    animation: heroMapPulse 2s ease-in-out infinite alternate;
  }
  /* Staggered start so the orange wave rolls across the city rather than
     every neighborhood pulsing in unison. */
  .hero-map-shapes path:nth-child(3n)   { animation-delay: 0.6s; }
  .hero-map-shapes path:nth-child(3n+1) { animation-delay: 1.2s; }
  .hero-map-shapes path:nth-child(5n+2) { animation-delay: 1.8s; }
  @keyframes heroMapPulse {
    0%   { fill: #d9d9d9; stroke: #aaa; }
    100% { fill: #e67e22; stroke: #b86413; }
  }
  @media (prefers-reduced-motion: reduce) {
    .hero-map-shapes path { animation: none; }
  }
  .hero-inner {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
    text-align: left;
    max-width: 480px;
    width: 100%;
    position: relative;
    z-index: 1;
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
    font-size: 2.6rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: #1a1a1a;
    margin: 0;
  }
  .hero-lede {
    font-size: 1rem !important;
    line-height: 1.65 !important;
    color: #333 !important;
    max-width: 100%;
    margin: 0 !important;
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
  /* The hero's "Scroll to begin" arrow flows directly under the lede,
     with a little extra breathing room so it reads as a clear prompt. */
  .hero-inner > .hero-arrow {
    margin-top: 28px;
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
  .sticky-wrap {
    position: sticky;
    top: 0;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 40px 60px;
  }
  @media (max-width: 900px) {
    .sticky-wrap { padding: 40px 24px; }
  }

  .income-compare {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 580px;
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
    grid-template-columns: 110px minmax(0, 1fr) 170px;
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
    inset: 0 auto 0 0;
    height: 100%;
    border-radius: 12px;
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

  .rent-marker {
    position: absolute;
    top: -6px;
    bottom: -6px;
    width: 2px;
    background: #1a1a1a;
    transform: translateX(-1px);
    z-index: 3;
    pointer-events: none;
  }
  .rent-marker::before,
  .rent-marker::after {
    content: '';
    position: absolute;
    left: 50%;
    width: 0;
    height: 0;
    transform: translateX(-50%);
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
  }
  .rent-marker::before { top: -1px; border-bottom: 5px solid #1a1a1a; }
  .rent-marker::after { bottom: -1px; border-top: 5px solid #1a1a1a; }
  .rent-marker-tip {
    position: absolute;
    top: -22px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.62rem;
    font-weight: 700;
    color: #1a1a1a;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 1px 5px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .rent-marker.boston { background: #2d3748; }
  .rent-marker.boston::before { border-bottom-color: #2d3748; }
  .rent-marker.boston::after { border-top-color: #2d3748; }

  .rent-pct-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .rent-pct-num {
    font-size: 1.1rem;
    font-weight: 800;
    color: #1a1a1a;
  }
  .rent-pct-lbl {
    font-size: 0.65rem;
    color: #888;
    margin-top: 2px;
    text-align: right;
  }

  .income-row.tick-row {
    opacity: 1 !important;
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px solid #eee;
  }
  .tick-axis {
    position: relative;
    height: 18px;
  }
  .tick {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .tick-line {
    width: 1px;
    height: 5px;
    background: #aaa;
  }
  .tick-label {
    margin-top: 1px;
    font-size: 0.62rem;
    color: #888;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .tick-cap {
    font-size: 0.62rem !important;
    color: #888;
    font-style: italic;
    text-align: right !important;
    align-items: flex-end !important;
    justify-self: end;
  }
  .boston-name { color: #555 !important; font-size: 0.78rem; line-height: 1.1; }
  .boston-renter { background: #2d3748; }
  .boston-owner {}

  .flow-section {
    flex-direction: column;
    align-items: stretch;
    text-align: left;
    max-width: 1020px;
    gap: 18px;
    /* Anchor near the top of the sticky viewport so the heading has buffer
       above it and the scroll arrow appears higher on the screen instead
       of being centered. */
    align-self: flex-start;
    margin-top: 24px;
  }
  .flow-arrow {
    /* Pull the arrow up so it sits right below the visualization, instead
       of trailing the bottom padding of the stats column. */
    margin-top: -60px;
  }
  .flow-intro { max-width: none; width: 100%; }

  .flow-with-stats {
    display: flex;
    align-items: stretch;
    gap: 28px;
    width: 100%;
    margin: 0 auto;
  }
  .flow-chart-wrap {
    flex: 1 1 540px;
    min-width: 0;
    max-width: 600px;
  }
  .flow-stats {
    flex: 0 0 360px;
    display: flex;
    flex-direction: column;
    /* Top group sits near the Corporate box (top), bottom group near the
       Individual box (bottom). FlowDiagram's corp row ~22% from top,
       ind row ~78% from top. */
    justify-content: space-between;
    gap: 48px;
    padding: 1% 0 12%;
  }
  .flow-stat-group {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .flow-stat {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
  }
  .flow-stat + .flow-stat {
    border-top: 1px solid #eee;
  }
  .fl-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    font-size: 0.92rem;
    flex-wrap: nowrap;
    white-space: nowrap;
  }
  .fl-name {
    font-weight: 700;
    white-space: nowrap;
    flex: 0 0 auto;
  }
  .fl-name .gray { color: #888; }
  .fl-name .corp { color: #e67e22; }
  .fl-name .ind  { color: #2563eb; }
  .fl-val {
    color: #666;
    font-variant-numeric: tabular-nums;
    font-size: 0.86rem;
    white-space: nowrap;
    flex: 0 0 auto;
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
  @media (max-width: 900px) {
    .flow-with-stats { flex-direction: column; }
    .flow-stats { flex: 1 1 auto; padding: 0; }
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
