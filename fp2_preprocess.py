"""
fp2_preprocess.py — Generate D3-ready data for the Boston housing scroll story.

Run:  python fp2_preprocess.py

Pipeline:
  1. Map Boston ZIP codes to neighborhoods (35 ZIPs → 20 neighborhoods)
  2. Load MAPC residential sales, filter to Boston 2018+, $50K–$5M, valid coords
  3. Estimate monthly rent: sale_price / (20 * 12)
  4. Aggregate rent stats per neighborhood (mean, median, percentiles, count)
  5. Enrich neighborhoods with census-tract-level eviction/ownership data via spatial join
  6. Write neighborhoods.geojson (24 polygons + aggregated stats)
  7. Flag individual properties near eviction filings (KD-tree, 50m radius)
  8. Write properties.json (32K records with lat/lng, rent, eviction flag)

Inputs (from data/):
  - Residential Sales Transactions Data / mapc_region_residential_sales.csv
  - Geographic Data / Boston Neighborhoods / Boston_Neighborhoods.geojson.json
  - Geographic Data / Boston Neighborhoods / Boston_Neighborhoods_Zipcodes.csv
  - Exploring corporate owners & evictions / Eviction (2020-2023) + ... .csv  (census tract level)
  - Exploring corporate owners & evictions / Evictions (2020-2024) ... _filings.csv  (individual filings)
  - Geographic Data / MAPC Region Census / 2020 Census Tracts MAPC Region.geojson

Outputs (to fp2/public/data/):
  - neighborhoods.geojson — polygons with rent stats, evictions, ownership rates
  - properties.json — individual sales with lat/lng, estimated rent, had_eviction flag
"""

import json
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import mapping

BASE = Path(__file__).parent
DATA = BASE / "data"
GEO = DATA / "Geographic Data"
OUT = BASE / "fp2" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

SALES_CSV = (DATA / "Residential Sales Transactions Data"
             / "Residential sales transactions in Metro Boston (MAPC Region) 2000-2023"
             / "mapc_region_residential_sales.csv")
HOODS_GEO = GEO / "Boston Neighborhoods" / "Boston_Neighborhoods.geojson.json"
ZIPS_CSV = GEO / "Boston Neighborhoods" / "Boston_Neighborhoods_Zipcodes.csv"
EVICTION_TRACT_CSV = (DATA / "Exploring corporate owners & evictions"
                      / "Eviction (2020-2023) + Owner Occupancy (2020) + Corporate Ownership (2020) + Residential Sales Data + Census Track (2020) "
                      / "Eviction (2020-2023) + Owner Occupancy (2020) + Corporate Ownership (2020) + Residential Sales + Census (2010).csv")
EVICTION_FILINGS_CSV = (DATA / "Exploring corporate owners & evictions"
                        / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details "
                        / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details_filings.csv")
CENSUS_GEO = (GEO / "MAPC Region Census"
              / "MAPC region - Census tracts 2020"
              / "2020 Census Tracts MAPC Region.geojson")

RENT_RATIO = 20
MIN_YEAR = 2018
MIN_PRICE = 50_000
MAX_PRICE = 5_000_000
MATCH_RADIUS = 50
EXCLUDE_HOODS = {"Harbor Islands"}


def safe_int(v):
    return None if pd.isna(v) else int(v)

def safe_float(v, d=3):
    return None if pd.isna(v) else round(float(v), d)


# 1. ZIP → neighborhood lookup
zips = pd.read_csv(ZIPS_CSV)
zips["Zip Code"] = zips["Zip Code"].astype(str).str.zfill(5)
zip_to_hood = dict(zip(zips["Zip Code"], zips["Neighborhood"]))
boston_zips = set(zip_to_hood.keys())

# 2. Load and filter sales
cols = ["city", "zip", "proptype", "year", "price", "usage", "bedrooms", "bathrooms", "yearbuilt", "lat", "lon"]
sales = pd.read_csv(SALES_CSV, usecols=cols, dtype={"zip": str})
sales["zip"] = sales["zip"].str.strip().str.zfill(5)
for c in ["year", "price", "lat", "lon"]:
    sales[c] = pd.to_numeric(sales[c], errors="coerce")

sales = sales[
    sales["zip"].isin(boston_zips) &
    (sales["year"] >= MIN_YEAR) &
    sales["price"].between(MIN_PRICE, MAX_PRICE) &
    sales["lat"].notna() &
    sales["lon"].notna()
].copy()

# 3. Estimate rent, assign neighborhood via spatial join (not ZIP)
sales["monthly_rent"] = (sales["price"] / (RENT_RATIO * 12)).round(0).astype(int)
sales["bedrooms"] = pd.to_numeric(sales["bedrooms"], errors="coerce")

hoods_for_join = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
hoods_for_join = hoods_for_join.rename(columns={"blockgr2020_ctr_neighb_name": "name"})
hoods_for_join = hoods_for_join[~hoods_for_join["name"].isin(EXCLUDE_HOODS)]

sales_geo = gpd.GeoDataFrame(
    sales, geometry=gpd.points_from_xy(sales["lon"], sales["lat"]), crs="EPSG:4326"
)
sales_geo = gpd.sjoin(sales_geo, hoods_for_join[["name", "geometry"]], how="left", predicate="within")
sales_geo = sales_geo.rename(columns={"name": "neighborhood"})
sales_geo = sales_geo[sales_geo["neighborhood"].notna()].drop(columns=["index_right", "geometry"])
sales = pd.DataFrame(sales_geo)

# 4. Aggregate to neighborhood level
hood_stats = (
    sales.groupby("neighborhood")["monthly_rent"]
    .agg(avg_rent="mean", median_rent="median", min_rent="min", max_rent="max",
         p25_rent=lambda x: x.quantile(0.25), p75_rent=lambda x: x.quantile(0.75),
         count="count")
    .reset_index()
    .rename(columns={"neighborhood": "name"})
)
for c in ["avg_rent", "median_rent", "p25_rent", "p75_rent"]:
    hood_stats[c] = hood_stats[c].round(0).astype(int)

# 5. Enrich with census-tract eviction/ownership data
eviction_loaded = False
try:
    tracts = pd.read_csv(EVICTION_TRACT_CSV)
    evict_cols = ["2020_eviction", "2021_eviction", "2022_eviction", "2023_eviction"]
    for c in evict_cols:
        tracts[c] = pd.to_numeric(tracts[c], errors="coerce").fillna(0)
    tracts["total_evictions"] = tracts[evict_cols].sum(axis=1)
    tracts["corp_own_rate"] = pd.to_numeric(tracts["corp_own_rate"], errors="coerce")
    tracts["own_occ_rate"] = pd.to_numeric(tracts["own_occ_rate"], errors="coerce")
    tracts["r_mhi"] = pd.to_numeric(tracts["r_mhi"], errors="coerce")

    tract_geo = gpd.read_file(CENSUS_GEO)
    tract_geo["geoid"] = tract_geo["geoid"].astype(str)
    tracts["GEOID"] = tracts["GEOID"].astype(str)

    tract_merged = tract_geo.merge(tracts, left_on="geoid", right_on="GEOID", how="inner").to_crs(epsg=4326)
    hoods_geo = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
    hoods_geo = hoods_geo.rename(columns={"blockgr2020_ctr_neighb_name": "name"})

    joined = gpd.sjoin(
        tract_merged[["geoid", "total_evictions", "corp_own_rate", "own_occ_rate", "r_mhi", "geometry"]],
        hoods_geo[["name", "geometry"]],
        how="left", predicate="intersects",
    )

    hood_evict = (
        joined.groupby("name")
        .agg(total_evictions=("total_evictions", "sum"),
             avg_corp_own_rate=("corp_own_rate", "mean"),
             avg_own_occ_rate=("own_occ_rate", "mean"),
             avg_renter_mhi=("r_mhi", "mean"))
        .reset_index()
    )
    hood_evict[["avg_corp_own_rate", "avg_own_occ_rate", "avg_renter_mhi"]] = \
        hood_evict[["avg_corp_own_rate", "avg_own_occ_rate", "avg_renter_mhi"]].round(3)

    hood_stats = hood_stats.merge(hood_evict, on="name", how="left")
    eviction_loaded = True
except Exception as e:
    print(f"Warning: census-tract eviction data unavailable ({e})")

# 6. Write neighborhoods.geojson
hoods_geo = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
hoods_geo = hoods_geo.rename(columns={"blockgr2020_ctr_neighb_name": "name"})
hoods_geo = hoods_geo[~hoods_geo["name"].isin(EXCLUDE_HOODS)]
hoods_out = hoods_geo[["name", "geometry"]].merge(hood_stats, on="name", how="left")

features = []
for _, row in hoods_out.iterrows():
    props = {
        "name": row["name"],
        "avg_rent": safe_int(row.get("avg_rent")),
        "median_rent": safe_int(row.get("median_rent")),
        "min_rent": safe_int(row.get("min_rent")),
        "max_rent": safe_int(row.get("max_rent")),
        "p25_rent": safe_int(row.get("p25_rent")),
        "p75_rent": safe_int(row.get("p75_rent")),
        "count": safe_int(row.get("count")),
    }
    if eviction_loaded:
        props["total_evictions"] = safe_int(row.get("total_evictions"))
        props["avg_corp_own_rate"] = safe_float(row.get("avg_corp_own_rate"))
        props["avg_own_occ_rate"] = safe_float(row.get("avg_own_occ_rate"))
        props["avg_renter_mhi"] = safe_int(row.get("avg_renter_mhi"))
    features.append({
        "type": "Feature",
        "properties": props,
        "geometry": mapping(row["geometry"]) if row["geometry"] else None,
    })

with open(OUT / "neighborhoods.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f)

# 7. Flag properties near eviction filings (KD-tree, 50m)
try:
    from scipy.spatial import cKDTree
    from pyproj import Transformer

    filings = pd.read_csv(EVICTION_FILINGS_CSV, dtype={"zip": str})
    filings["zip"] = filings["zip"].astype(str).str.zfill(5)
    filings = filings[
        filings["zip"].isin(boston_zips) & filings["lat"].notna() & filings["long"].notna()
    ].copy()

    filings["lat_r"] = filings["lat"].round(5)
    filings["lng_r"] = filings["long"].round(5)
    locs = filings.drop_duplicates(subset=["lat_r", "lng_r"])[["lat_r", "lng_r"]]

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)
    ex, ey = to_utm.transform(locs["lng_r"].values, locs["lat_r"].values)
    px, py = to_utm.transform(sales["lon"].values, sales["lat"].values)

    tree = cKDTree(np.column_stack([ex, ey]))
    dist, _ = tree.query(np.column_stack([px, py]), k=1)
    sales["had_eviction"] = dist <= MATCH_RADIUS
except Exception as e:
    print(f"Warning: eviction filing match unavailable ({e})")
    sales["had_eviction"] = False

# 8. Write properties.json
out_cols = ["lat", "lon", "monthly_rent", "neighborhood", "bedrooms", "proptype", "usage", "price", "had_eviction"]
props = sales[out_cols].copy().rename(columns={"lon": "lng"})
props["lat"] = props["lat"].round(6)
props["lng"] = props["lng"].round(6)
props["bedrooms"] = props["bedrooms"].fillna(0).astype(int)
props["price"] = props["price"].astype(int)
props["had_eviction"] = props["had_eviction"].astype(bool)

records = props.where(props.notna(), None).to_dict(orient="records")
with open(OUT / "properties.json", "w") as f:
    json.dump(records, f)

print(f"Done: {len(features)} neighborhoods, {len(records):,} properties")
