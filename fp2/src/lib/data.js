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

// ── Dot color scale (rent → color) ────────────────────────────────────────────
// Fixed domain [200, 10000] matching slider range so dot colors stay stable as
// the slider moves. Strictly light → dark: pale yellow → deep red.
export const DOT_RENT_DOMAIN = [200, 5000];
export const dotColorScale = d3.scaleSequential(
  d3.interpolate('#ffcccc', '#8b0000')
).domain(DOT_RENT_DOMAIN).clamp(true);

// ── Filter helper ─────────────────────────────────────────────────────────────
// Returns properties at or below maxRent, optionally excluding those with eviction history.
export function filterProperties(properties, maxRent, excludeEvicted = false) {
  return properties.filter((p) =>
    p.monthly_rent <= maxRent && (!excludeEvicted || !p.had_eviction)
  );
}
