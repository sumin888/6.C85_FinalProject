# FP2 — Instructions for Nuri (from Sumin)

I set up the project scaffold, data pipeline, and narrative framework, so now we can build the `NeighborhoodMap` D3 component and deploy to GitHub Pages.

---

## 1. First-time setup

**Step 1 — generate the data files** (run once from the project root, not inside fp2/):
```bash
python fp2_preprocess.py    # takes ~1 min; writes to fp2/public/data/
```
This produces:
- `fp2/public/data/neighborhoods.geojson` — Boston neighborhood polygons + metrics
- `fp2/public/data/parcels_sample.json`   — ~60 jittered parcel points per neighborhood

**Step 2 — start the dev server:**
```bash
cd fp2
npm install
npm run dev
```
Open http://localhost:5173. You should see the page with the metric toggle working and the map placeholder showing "24 neighborhoods loaded · N scatter points loaded".

---

## 2. What's already done (don't change these)

| File | What it does |
|------|-------------|
| `src/lib/data.js` | Data loaders, color scales, METRICS array |
| `src/App.svelte` | Page layout, metric toggle, narrative text, data loading |
| `public/data/neighborhoods.geojson` | Boston neighborhood GeoJSON with all metrics |
| `public/data/parcels_sample.json` | Sampled parcel scatter points |
| `package.json` | All dependencies (d3, svelte, vite) |

---

## 3. To do: build the map

### Step 1: Create the component
Create `src/components/NeighborhoodMap.svelte`

### Step 2: Wire it into App.svelte
At the top of `src/App.svelte`, add:
```js
import NeighborhoodMap from './components/NeighborhoodMap.svelte'
```
Then replace the `<div class="map-placeholder">` block with:
```svelte
<NeighborhoodMap {geoData} {scatter} {activeMetric} />
```

### Step 3: Build the component

The component receives three props:

```js
// geoData — GeoJSON FeatureCollection
// Each feature.properties has:
{
  name:                   'South Boston',   // neighborhood name
  avg_monthly_payment:    4200,             // avg naive monthly payment ($)
  median_monthly_payment: 3800,
  p25_payment:            2900,
  p75_payment:            5100,
  parcel_count:           412,
  total_evictions:        87,               // 2020–2023 total
  avg_corp_own_rate:      0.142,            // 0–1
  avg_own_occ_rate:       0.381,
  avg_renter_mhi:         29335,
}

// scatter — array of jittered parcel points
{ neighborhood: 'South Boston', lng: -71.034, lat: 42.338, monthly_payment: 4500 }

// activeMetric — current metric from METRICS array (switches on toggle click)
{
  key:       'avg_monthly_payment',   // which property to read from feature.properties
  label:     'Avg Monthly Payment',
  unit:      '/mo',
  format:    d => `$${d.toLocaleString()}`,   // call this for tooltip / legend labels
  makeScale: makePaymentColorScale,           // call with no args to get a D3 color scale
  palette:   'Housing Transition',
}
```

**What the map should render:**
1. **Boston neighborhood polygons** — use `d3.geoPath()` + `d3.geoMercator()` projected to the SVG
2. **Choropleth fill** — color each polygon using `activeMetric.makeScale()(feature.properties[activeMetric.key])`
   - If value is `null`, use `#3a3a3a` (Neutral gray = no data)
3. **Tooltip** — on hover: neighborhood name + `activeMetric.format(value)`
4. **Legend** — color scale legend below or beside the map
5. **Scatter layer** — dots from `scatter` array positioned by `lng`/`lat`
   - Color dots by `monthly_payment` using `makePaymentColorScale()`
   - Toggle button to show/hide dots

### Step 4: Non-trivial interaction (required by rubric — we can pick one among these)

**Option A — Click → neighborhood detail panel** (recommended)
Click a neighborhood polygon → sidebar or panel slides in showing all metrics:
- Avg monthly payment, corporate ownership %, total evictions, renter MHI

**Option B — Metric comparison mode**
Side-by-side or overlaid small multiples for two metrics at once.

**Option C — Neighborhood search**
Dropdown to search and highlight a specific neighborhood.

---

## 4. D3 imports available

```js
import * as d3 from 'd3'
import { loadNeighborhoodGeo, loadParcelSample, METRICS, makePaymentColorScale,
         makeCorpOwnColorScale, makeEvictionColorScale, STATS } from '../lib/data.js'
```

---

## 5. Color palette (our Visual Design Study)

| Semantic role | Light | Dark | Use for |
|---------------|-------|------|---------|
| **Pressure / Harm** | `#f4b8b8` | `#c0392b` | Evictions |
| **Stability / Protection** | `#b8d4f4` | `#2471a3` | Owner-occupancy |
| **Investor Activity** | `#a8e6d8` | `#1a7a5e` | Corporate ownership |
| **Housing Transition** | `#f4e4a8` | `#d4730a` | Monthly payment / price |
| **Neutral / Missing** | `#d0d0d0` | `#5a5a5a` | No data |

Background `#0d0d0d` · Card `#111111` · Text `#ffffff` / `#888888`

---

## 6. Key stats (in STATS in data.js)

| Stat | Value |
|------|-------|
| Total conversions 2016–2024 | 2,245 |
| Total new condo units | 10,118 |
| Conversions in 2023 | 868 (nearly 4×) |
| Estimated people displaced | ~22,000 |
| Avg property value jump | +40.6% |

Notable data findings:

1) South Boston Waterfront ($108k/mo avg) and Chinatown ($51k/mo) are extreme outliers —> likely commercial/luxury.
2) Roslindale ($1,252/mo) and Mattapan ($1,604/mo) are most affordable
3) Eviction + corporate ownership data merged for 23/24 neighborhoods
---