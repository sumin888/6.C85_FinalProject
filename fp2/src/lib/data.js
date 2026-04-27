import * as d3 from 'd3';

export async function loadNeighborhoodGeo() {
  const geo = await d3.json('./data/neighborhoods.geojson');
  // Rewind polygon rings for D3 compatibility.
  // D3 expects clockwise exterior rings; GeoJSON RFC 7946 (shapely/geopandas)
  // uses counter-clockwise. Without this fix D3 fills the *complement* of each
  // polygon, producing one giant blob instead of individual neighborhoods.
  rewindForD3(geo);
  return geo;
}

function rewindForD3(geojson) {
  for (const feature of geojson.features) {
    const geom = feature.geometry;
    if (!geom) continue;
    if (geom.type === 'Polygon') {
      rewindPolygon(geom.coordinates);
    } else if (geom.type === 'MultiPolygon') {
      for (const polygon of geom.coordinates) {
        rewindPolygon(polygon);
      }
    }
  }
}

function rewindPolygon(rings) {
  for (let i = 0; i < rings.length; i++) {
    const cw = ringIsClockwise(rings[i]);
    // Exterior ring (i===0) must be clockwise for D3; holes must be CCW
    if (i === 0 && !cw) rings[i].reverse();
    else if (i > 0 && cw) rings[i].reverse();
  }
}

function ringIsClockwise(ring) {
  let sum = 0;
  for (let i = 0, len = ring.length - 1; i < len; i++) {
    sum += (ring[i + 1][0] - ring[i][0]) * (ring[i + 1][1] + ring[i][1]);
  }
  return sum > 0;
}

export async function loadProperties() {
  return d3.json('./data/properties.json');
}

export async function loadZoriByNeighborhood() {
  return d3.json('./data/zori_by_neighborhood.json');
}

export async function loadEvictionsByNeighborhood() {
  return d3.json('./data/evictions_by_neighborhood.json');
}

export async function loadStoryData() {
  return d3.json('./data/corp_ownership_timeseries.json');
}

export async function loadEvictionDots() {
  const raw = await d3.json('./data/eviction_dots.json');
  if (!Array.isArray(raw)) return raw;
  // Drop records whose geocoded lat/lng fall outside the Boston area — these
  // are bad geocodes (wrong city, or off by a tenth of a degree in lat/lng).
  return raw.filter(d => {
    const { lat, lng } = d ?? {};
    return typeof lat === 'number' && typeof lng === 'number'
      && lat >= 42.22 && lat <= 42.40
      && lng >= -71.20 && lng <= -70.99;
  });
}

// Filter eviction dots by rent budget and year
export function filterEvictionDots(dots, maxRent, { useCurrentRent = false, maxYear = 2024 } = {}) {
  const rentKey = useCurrentRent ? 'rent_now' : 'rent_at_filing';
  return dots.filter(d =>
    d[rentKey] != null &&
    d[rentKey] <= maxRent + 2000 &&
    (d.file_year == null || d.file_year <= maxYear)
  );
}

// ── Metric definitions ────────────────────────────────────────────────────────
// Each entry describes one neighborhood-level metric that can be used to color
// the choropleth layer.
export const METRICS = [
  {
    key: 'avg_corp_own_rate',
    label: 'Corporate Ownership',
    format: (v) => (v != null ? `${(v * 100).toFixed(1)}%` : 'N/A'),
  },
  {
    key: 'total_evictions',
    label: 'Total Evictions',
    format: (v) => (v != null ? v.toLocaleString() : 'N/A'),
  },
];

// ── Color scale factory ───────────────────────────────────────────────────────
// Vivid, visually distinct palettes that read well on a dark background.
// Each metric gets its own hue so switching is immediately obvious.
export function buildColorScale(features, metricKey) {
  const values = features
    .map((f) => f.properties[metricKey])
    .filter((v) => v != null && !isNaN(v));

  const extent = d3.extent(values);

  const interpolators = {
    'avg_corp_own_rate': d3.interpolateGnBu,         // green → blue
    'total_evictions':   d3.interpolateOrRd,          // orange → red
  };

  const interp = interpolators[metricKey] ?? d3.interpolateYlOrRd;

  // Map domain [min, max] → interpolator range [0.15, 1.0] to avoid
  // near-white tones at the low end that vanish on light fills.
  const scale = (v) => interp(0.15 + 0.85 * ((v - extent[0]) / (extent[1] - extent[0] || 1)));

  return { scale, extent };
}

// ── Dot color scale (continuous light → dark blue by rent) ──────────────────
export function makeDotColorScale(maxRent) {
  return d3.scaleLinear()
    .domain([0, maxRent + 2000])
    .range(['#bcd3f2', '#1d3f7a'])
    .clamp(true);
}

// ── Investor dot color scale (continuous light → dark orange by rent) ────────
export function makeInvestorColorScale(maxRent) {
  return d3.scaleLinear()
    .domain([0, maxRent + 2000])
    .range(['#fdd9b5', '#b35900'])
    .clamp(true);
}

// ── Corporate/investor dot color scale (continuous light → dark orange by rent) ─
export function makeEvictionColorScale(maxRent) {
  return d3.scaleLinear()
    .domain([0, maxRent + 2000])
    .range(['#fdd9b5', '#a04600'])
    .clamp(true);
}

// ── Filter helper ─────────────────────────────────────────────────────────────
// Returns properties up to budget+2000, optionally excluding eviction-flagged.
export function filterProperties(properties, maxRent, { useCurrentRent = false, excludeEvicted = false } = {}) {
  const rentKey = useCurrentRent ? 'monthly_rent_now' : 'monthly_rent';
  return properties.filter((p) =>
    p[rentKey] <= maxRent + 2000 && (!excludeEvicted || !p.had_eviction)
  );
}
