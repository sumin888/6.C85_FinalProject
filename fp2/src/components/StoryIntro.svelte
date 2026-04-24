<script>
  import { onMount, tick, createEventDispatcher } from 'svelte';
  import AnimatedLineChart from './AnimatedLineChart.svelte';
  import AnimatedBarChart from './AnimatedBarChart.svelte';

  const dispatch = createEventDispatcher();

  export let storyData;   // corp_ownership_timeseries.json
  export let zoriData;    // zori_by_neighborhood.json

  let scrollStep = 0;
  let stepProgresses = [0, 0, 0, 0, 0]; // per-step scroll progress 0–1

  // ── Prepare chart data ─────────────────────────────────────────────────
  $: corpLines = storyData ? [
    {
      label: 'Corporate',
      color: '#c0392b',
      data: storyData.citywide.corp_ownership.map(d => ({ x: d.year, y: d.rate })),
    },
    {
      label: 'Owner-Occupied',
      color: '#2d8c2d',
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
    { key: 'non_investor', label: 'Non-Investor', color: '#2d8c2d' },
    { key: 'small', label: 'Small Investor', color: '#e67e22' },
    { key: 'medium', label: 'Medium', color: '#d35400' },
    { key: 'large', label: 'Large', color: '#c0392b' },
    { key: 'institutional', label: 'Institutional', color: '#7b241c' },
  ];

  // ZORI rent lines for contrasting neighborhoods
  $: rentLines = zoriData ? [
    { label: 'Mission Hill', color: '#c0392b', hood: 'Mission Hill' },
    { label: 'Roxbury', color: '#e67e22', hood: 'Roxbury' },
    { label: 'Dorchester', color: '#3498db', hood: 'Dorchester' },
    { label: 'Hyde Park', color: '#2d8c2d', hood: 'Hyde Park' },
  ].filter(l => zoriData[l.hood]).map(l => ({
    label: l.label,
    color: l.color,
    data: zoriData[l.hood]
      .filter(d => d.date >= '2016-01-01')
      .filter((_, i) => i % 3 === 0) // every 3 months to reduce density
      .map(d => ({ x: new Date(d.date).getFullYear() + (new Date(d.date).getMonth() / 12), y: d.rent })),
  })) : [];

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
          // Progress: 0 when step top enters viewport center, 1 when step center reaches viewport center
          // This means animation completes by the time you're centered on the step
          const rawProgress = (mid - rect.top) / (rect.height * 0.5);
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
  <!-- Step 0: Corporate Takeover -->
  <div class="story-scroll-step" data-step="0">
    <div class="story-section" class:active={scrollStep === 0}>
      <div class="story-text">
        <h1>Boston's Corporate Takeover</h1>
        <p>
          Over the past 20 years, corporate entities have steadily acquired
          Boston's rental housing. Corporate ownership has risen from
          <strong>5.5% in 2004</strong> to <strong>25.3% in 2024</strong> —
          nearly a 5x increase. Meanwhile, owner-occupancy has declined
          from 43.6% to 38%.
        </p>
        <p class="detail">
          In 9 neighborhoods, corporate ownership now <em>exceeds</em>
          owner-occupancy — a reversal that was unthinkable two decades ago.
        </p>
      </div>
      <div class="story-chart">
        <AnimatedLineChart
          lines={corpLines}
          progress={scrollStep >= 0 ? Math.max(stepProgresses[0], scrollStep > 0 ? 1 : 0) : 0}
          yFormat={v => (v * 100).toFixed(0) + '%'}
          xFormat={v => String(Math.round(v))}
          yLabel="Rate"
          width={520}
          height={300}
        />
      </div>
    </div>
  </div>

  <!-- Step 1: Changing Hands -->
  <div class="story-scroll-step" data-step="1">
    <div class="story-section" class:active={scrollStep === 1}>
      <div class="story-text">
        <h1>Changing Hands</h1>
        <p>
          Individual homeowners are selling to corporate buyers at an
          accelerating rate. In 2004, only <strong>2%</strong> of property
          sales went from an individual to an LLC or corporation.
          By 2019, that reached <strong>12.4%</strong> — a 6x increase.
        </p>
        <p class="detail">
          These aren't families buying homes. They're investment entities
          acquiring assets — often purchasing from long-time owners who
          can no longer afford rising costs.
        </p>
      </div>
      <div class="story-chart">
        <AnimatedLineChart
          lines={indToCorpLines}
          progress={scrollStep >= 1 ? Math.max(stepProgresses[1], scrollStep > 1 ? 1 : 0) : 0}
          yFormat={v => (v * 100).toFixed(1) + '%'}
          xFormat={v => String(Math.round(v))}
          yLabel="% of Sales"
          width={520}
          height={300}
        />
      </div>
    </div>
  </div>

  <!-- Step 2: Who's Buying -->
  <div class="story-scroll-step" data-step="2">
    <div class="story-section" class:active={scrollStep === 2}>
      <div class="story-text">
        <h1>Who's Buying?</h1>
        <p>
          The composition of buyers has shifted dramatically.
          Non-investor buyers have dropped from <strong>85%</strong> to
          <strong>73%</strong> of purchases. Small LLC investors have
          nearly doubled their share from 8.5% to 15.9%.
        </p>
        <p class="detail">
          Institutional investors peaked during the 2008 financial crisis
          at 15%, swooping in on distressed properties. Small investors —
          LLCs buying 1-5 properties — now drive the trend.
        </p>
      </div>
      <div class="story-chart">
        <AnimatedBarChart
          data={investorBarData}
          categories={investorCategories}
          progress={scrollStep >= 2 ? Math.max(stepProgresses[2], scrollStep > 2 ? 1 : 0) : 0}
          yFormat={v => (v * 100).toFixed(0) + '%'}
          width={520}
          height={300}
        />
      </div>
    </div>
  </div>

  <!-- Step 3: The Price You Pay -->
  <div class="story-scroll-step" data-step="3">
    <div class="story-section" class:active={scrollStep === 3}>
      <div class="story-text">
        <h1>The Price You Pay</h1>
        <p>
          As corporate ownership rises, so do rents. Since 2016, rents
          have climbed <strong>20–40%</strong> across Boston — with the
          steepest increases in neighborhoods seeing the most investor
          activity.
        </p>
        <p class="detail">
          Mission Hill rents surged 41%. Even traditionally affordable
          neighborhoods like Hyde Park and Dorchester saw 25–30% increases.
          Real rent data from the Zillow Observed Rent Index shows the
          divergence.
        </p>
      </div>
      <div class="story-chart">
        <AnimatedLineChart
          lines={rentLines}
          progress={scrollStep >= 3 ? Math.max(stepProgresses[3], scrollStep > 3 ? 1 : 0) : 0}
          yFormat={v => '$' + Math.round(v).toLocaleString()}
          xFormat={v => String(Math.round(v))}
          yLabel="Monthly Rent"
          width={520}
          height={300}
        />
      </div>
    </div>
  </div>

  <!-- Step 4: CTA -->
  <div class="story-scroll-step" data-step="4">
    <div class="story-section cta-section" class:active={scrollStep === 4}>
      <h1>Let's Look Closer</h1>
      <p>
        These citywide trends mask dramatic differences between neighborhoods.
        In some areas, corporate landlords file <strong>100% of evictions</strong>.
        In others, communities are still holding on.
      </p>
      <p>
        We'll take you through <strong>8 neighborhoods</strong> — each
        with a different story about what investor activity means for
        the people who live there.
      </p>
      <button class="cta-btn" on:click={() => dispatch('enterDeepDive')}>
        Explore the Neighborhoods
      </button>
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
