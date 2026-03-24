"""
fp2_preprocess.py  —  Generate D3-ready data for the FP2 choropleth map
Run once from the project root:   python fp2_preprocess.py

Outputs (written to fp2/public/data/):
  neighborhoods.geojson  —  Boston neighborhood polygons with metrics merged in
  parcels_sample.json    —  Sampled parcels per neighborhood (for scatter layer)
"""

import json, os
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / 'data' / 'Geographic Data'
EVICT  = BASE / 'data' / 'Exploring_corporate_owners_and_evictions'

PARCEL_CSV   = DATA / 'Metro Boston (MAPC Region) Parcel' / 'metro_boston_parcel.csv'
HOODS_GEO    = DATA / 'Boston Neighborhoods' / 'Boston_Neighborhoods.geojson.json'
ZIPS_CSV     = DATA / 'Boston Neighborhoods' / 'Boston_Neighborhoods_Zipcodes.csv'
EVICTION_CSV = (BASE / 'data' / 'Exploring_corporate_owners_and_evictions' /
                'Eviction (2020-2023) + Owner Occupancy (2020) + Corporate Ownership (2020) + Residential Sales Data + Census Track (2020) ' /
                'Eviction (2020-2023) + Owner Occupancy (2020) + Corporate Ownership (2020) + Residential Sales + Census (2010).csv')

OUT_DIR = BASE / 'fp2' / 'public' / 'data'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Load zip → neighborhood mapping ───────────────────────────────────────
print('Loading zip → neighborhood mapping…')
df_zips = pd.read_csv(ZIPS_CSV)
df_zips['Zip Code'] = df_zips['Zip Code'].astype(str).str.zfill(5)
dict_zip2hood = dict(zip(df_zips['Zip Code'], df_zips['Neighborhood']))
boston_zips   = set(dict_zip2hood.keys())
print(f'  {len(boston_zips)} Boston ZIP codes → {len(set(dict_zip2hood.values()))} neighborhoods')

# ── 2. Load & process parcel data ────────────────────────────────────────────
print('Loading parcel data (this takes ~30 seconds)…')
df_parcels = pd.read_csv(PARCEL_CSV, dtype='unicode', low_memory=False)

# Keep only Boston parcels with valid price and units
df_parcels['ZIP_5']     = df_parcels['ZIP'].astype(str).str.strip().str.zfill(5)
df_parcels['LS_PRICE_S']  = pd.to_numeric(df_parcels['LS_PRICE_S'],  errors='coerce')
df_parcels['UNITS_CONDO'] = pd.to_numeric(df_parcels['UNITS_CONDO'], errors='coerce')

df_boston = df_parcels[
    df_parcels['ZIP_5'].isin(boston_zips) &
    df_parcels['LS_PRICE_S'].notna()  &
    df_parcels['UNITS_CONDO'].notna() &
    (df_parcels['LS_PRICE_S']  > 0)   &
    (df_parcels['UNITS_CONDO'] > 0)
].copy()

# Core metrics (matching Alex's notebook)
df_boston['price_per_unit']    = df_boston['LS_PRICE_S']  / df_boston['UNITS_CONDO']
df_boston['monthly_payment']   = df_boston['price_per_unit'] / (20 * 12)  # naive 20yr / 0% term
df_boston['neighborhood']      = df_boston['ZIP_5'].map(dict_zip2hood)

print(f'  {len(df_boston):,} Boston parcels with valid price + units')

# ── 3. Aggregate to neighborhood level ────────────────────────────────────────
print('Aggregating to neighborhood level…')
hood_agg = (
    df_boston.groupby('neighborhood')['monthly_payment']
    .agg(
        avg_monthly_payment  = 'mean',
        median_monthly_payment = 'median',
        parcel_count         = 'count',
        p25_payment          = lambda x: x.quantile(0.25),
        p75_payment          = lambda x: x.quantile(0.75),
    )
    .reset_index()
    .rename(columns={'neighborhood': 'name'})
)
hood_agg[['avg_monthly_payment', 'median_monthly_payment',
          'p25_payment', 'p75_payment']] = hood_agg[[
    'avg_monthly_payment', 'median_monthly_payment',
    'p25_payment', 'p75_payment']].round(0)

print(f'  Aggregated {len(hood_agg)} neighborhoods')
print(hood_agg[['name', 'avg_monthly_payment', 'parcel_count']].to_string(index=False))

# ── 4. Load eviction + ownership data ────────────────────────────────────────
print('\nLoading eviction / ownership data…')
try:
    df_evict = pd.read_csv(EVICTION_CSV)
    # Total evictions 2020–2023 per census tract
    for c in ['2020_eviction','2021_eviction','2022_eviction','2023_eviction']:
        df_evict[c] = pd.to_numeric(df_evict[c], errors='coerce').fillna(0)
    df_evict['total_evictions'] = (df_evict[['2020_eviction','2021_eviction',
                                              '2022_eviction','2023_eviction']].sum(axis=1))
    df_evict['corp_own_rate']   = pd.to_numeric(df_evict['corp_own_rate'], errors='coerce')
    df_evict['own_occ_rate']    = pd.to_numeric(df_evict['own_occ_rate'],  errors='coerce')
    df_evict['r_mhi']           = pd.to_numeric(df_evict['r_mhi'],         errors='coerce')

    # GEOID → neighborhood via census tract geometry spatial join
    # Simpler approach: the eviction CSV covers the MAPC region, not just Boston.
    # We'll join census tracts to neighborhoods spatially.
    CENSUS_GEO = DATA / 'MAPC Region Census' / 'MAPC region - Census tracts 2020' / '2020 Census Tracts MAPC Region.geojson'
    gpdf_tracts = gpd.read_file(CENSUS_GEO)
    gpdf_tracts['geoid'] = gpdf_tracts['geoid'].astype(str)
    df_evict['GEOID']    = df_evict['GEOID'].astype(str)

    # Merge eviction data onto census tract geometries
    gpdf_evict = gpdf_tracts.merge(df_evict, left_on='geoid', right_on='GEOID', how='inner')
    gpdf_evict = gpdf_evict.to_crs(epsg=4326)

    # Load neighborhood polygons and spatial-join tracts → neighborhoods
    gpdf_hoods = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
    gpdf_hoods = gpdf_hoods.rename(columns={'blockgr2020_ctr_neighb_name': 'name'})

    gpdf_joined = gpd.sjoin(
        gpdf_evict[['geoid','total_evictions','corp_own_rate','own_occ_rate','r_mhi','geometry']],
        gpdf_hoods[['name','geometry']],
        how='left', predicate='intersects'
    )

    hood_evict = (
        gpdf_joined.groupby('name')
        .agg(
            total_evictions  = ('total_evictions',  'sum'),
            avg_corp_own_rate = ('corp_own_rate',   'mean'),
            avg_own_occ_rate  = ('own_occ_rate',    'mean'),
            avg_renter_mhi    = ('r_mhi',           'mean'),
        )
        .reset_index()
    )
    hood_evict[['avg_corp_own_rate','avg_own_occ_rate','avg_renter_mhi']] = \
        hood_evict[['avg_corp_own_rate','avg_own_occ_rate','avg_renter_mhi']].round(3)

    hood_agg = hood_agg.merge(hood_evict, on='name', how='left')
    print(f'  Eviction/ownership data merged for {hood_evict["name"].nunique()} neighborhoods')
    eviction_loaded = True

except Exception as e:
    print(f'  Warning: Could not load eviction data ({e}). Continuing without it.')
    eviction_loaded = False

# ── 5. Merge metrics onto neighborhood GeoJSON ────────────────────────────────
print('\nMerging into neighborhood GeoJSON…')
gpdf_hoods = gpd.read_file(HOODS_GEO)
gpdf_hoods = gpdf_hoods.rename(columns={'blockgr2020_ctr_neighb_name': 'name'})
gpdf_hoods = gpdf_hoods.to_crs(epsg=4326)

gpdf_out = gpdf_hoods[['name','geometry']].merge(hood_agg, on='name', how='left')

# Build GeoJSON manually so D3 can use it directly
features = []
for _, row in gpdf_out.iterrows():
    props = {
        'name':                   row['name'],
        'avg_monthly_payment':    None if pd.isna(row.get('avg_monthly_payment',    np.nan)) else int(row['avg_monthly_payment']),
        'median_monthly_payment': None if pd.isna(row.get('median_monthly_payment', np.nan)) else int(row['median_monthly_payment']),
        'p25_payment':            None if pd.isna(row.get('p25_payment',            np.nan)) else int(row['p25_payment']),
        'p75_payment':            None if pd.isna(row.get('p75_payment',            np.nan)) else int(row['p75_payment']),
        'parcel_count':           None if pd.isna(row.get('parcel_count',           np.nan)) else int(row['parcel_count']),
    }
    if eviction_loaded:
        props['total_evictions']   = None if pd.isna(row.get('total_evictions',   np.nan)) else int(row['total_evictions'])
        props['avg_corp_own_rate'] = None if pd.isna(row.get('avg_corp_own_rate', np.nan)) else round(float(row['avg_corp_own_rate']), 3)
        props['avg_own_occ_rate']  = None if pd.isna(row.get('avg_own_occ_rate',  np.nan)) else round(float(row['avg_own_occ_rate']),  3)
        props['avg_renter_mhi']    = None if pd.isna(row.get('avg_renter_mhi',    np.nan)) else int(row['avg_renter_mhi'])

    from shapely.geometry import mapping
    features.append({
        'type': 'Feature',
        'properties': props,
        'geometry': mapping(row['geometry']) if row['geometry'] else None,
    })

geojson_out = {'type': 'FeatureCollection', 'features': features}
out_path = OUT_DIR / 'neighborhoods.geojson'
with open(out_path, 'w') as f:
    json.dump(geojson_out, f)
print(f'  Saved: {out_path}  ({len(features)} features)')

# ── 6. Scatter sample: ~50 points per neighborhood ───────────────────────────
print('\nGenerating scatter sample…')
SAMPLE_PER_HOOD = 60
rng = np.random.default_rng(42)

# Compute neighborhood centroids for jitter center
centroids = {row['name']: row['geometry'].centroid
             for _, row in gpdf_hoods.iterrows() if row['geometry']}

scatter_rows = []
for hood, group in df_boston.groupby('neighborhood'):
    if hood not in centroids:
        continue
    centroid = centroids[hood]
    sample = group['monthly_payment'].dropna()
    if len(sample) == 0:
        continue
    n = min(SAMPLE_PER_HOOD, len(sample))
    sampled = sample.sample(n, random_state=42).values
    # Jitter around centroid (scale matches Alex's 0.003)
    jitter_x = rng.normal(0, 0.003, n)
    jitter_y = rng.normal(0, 0.003, n)
    for i in range(n):
        scatter_rows.append({
            'neighborhood':    hood,
            'lng':             round(centroid.x + jitter_x[i], 6),
            'lat':             round(centroid.y + jitter_y[i], 6),
            'monthly_payment': round(float(sampled[i]), 0),
        })

out_scatter = OUT_DIR / 'parcels_sample.json'
with open(out_scatter, 'w') as f:
    json.dump(scatter_rows, f)
print(f'  Saved: {out_scatter}  ({len(scatter_rows)} points)')

# ── Summary ───────────────────────────────────────────────────────────────────
print('\nDone. Files ready for D3:')
print(f'  {OUT_DIR}/neighborhoods.geojson')
print(f'  {OUT_DIR}/parcels_sample.json')
print('\nPayment ranges by neighborhood:')
print(hood_agg[['name','avg_monthly_payment','parcel_count']].sort_values('avg_monthly_payment', ascending=False).to_string(index=False))
