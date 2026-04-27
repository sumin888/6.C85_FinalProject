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
cols = ["address", "street", "city", "zip", "proptype", "year", "price", "usage", "bedrooms", "bathrooms",
        "yearbuilt", "totrooms", "intersf", "lotsize", "style", "date", "lat", "lon",
        "buyer_llc_ind", "buyer_bus_ind", "investor_type_purchase", "tot_owned",
        "cash_sale", "flip_ind", "investor_type_sale", "seller_llc_ind"]
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

# 3. Estimate rent from sale price, then calibrate with ZORI later
RENT_RATIO = 20
sales["raw_rent"] = (sales["price"] / (RENT_RATIO * 12)).round(0).astype(int)
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

# 3b. Filter to rental properties only
#     Multi-family (2-FAM, 3-FAM, 4-8 UNIT, 9+ UNIT, APT) = all rental
#     Condos bought by investors (LLC, business, multi-property owner) = rental
#     Exclude single-family homes, owner-occupied condos, and commercial
MULTIFAMILY = {"2-FAM RES", "3-FAM RES", "4-8 UNIT APT", "9 + UNIT APT", "APT BLDG",
               "BOARDING HSE", "SUBSDZ HSNG", "RES-MTL BLDG"}
RENTAL_CONDO = {"CONDOMINIUM", "CNDO PKG-RES"}
sales["tot_owned"] = pd.to_numeric(sales["tot_owned"], errors="coerce").fillna(0)
sales["buyer_llc_ind"] = pd.to_numeric(sales["buyer_llc_ind"], errors="coerce").fillna(0)
sales["buyer_bus_ind"] = pd.to_numeric(sales["buyer_bus_ind"], errors="coerce").fillna(0)

is_multifamily = sales["usage"].isin(MULTIFAMILY)
is_investor_owned = (sales["tot_owned"] > 1) | (sales["buyer_llc_ind"] == 1) | (sales["buyer_bus_ind"] == 1)
is_condo = sales["usage"].isin(RENTAL_CONDO)

# Keep: all multi-family + condos bought by investors/multi-property owners
sales = sales[is_multifamily | (is_condo & is_investor_owned)].copy()
print(f"Rental properties after filter: {len(sales):,}")

# 4. (Deferred — neighborhood rent stats computed after ZORI assignment in step 9b)

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
    tracts["o_mhi"] = pd.to_numeric(tracts["o_mhi"], errors="coerce")
    # Household counts per tract for weighting tract-level medians.
    tracts["hh"] = pd.to_numeric(tracts["hh"], errors="coerce")
    tracts["renter_hh"] = tracts["hh"] * (1 - tracts["own_occ_rate"])
    tracts["owner_hh"] = tracts["hh"] * tracts["own_occ_rate"]

    tract_geo = gpd.read_file(CENSUS_GEO)
    tract_geo["geoid"] = tract_geo["geoid"].astype(str)
    tracts["GEOID"] = tracts["GEOID"].astype(str)

    tract_merged = tract_geo.merge(tracts, left_on="geoid", right_on="GEOID", how="inner").to_crs(epsg=4326)
    hoods_geo = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
    hoods_geo = hoods_geo.rename(columns={"blockgr2020_ctr_neighb_name": "name"})

    joined = gpd.sjoin(
        tract_merged[["geoid", "total_evictions", "corp_own_rate", "own_occ_rate",
                       "r_mhi", "o_mhi", "renter_hh", "owner_hh", "geometry"]],
        hoods_geo[["name", "geometry"]],
        how="left", predicate="intersects",
    )

    # Population-weighted tract-level medians per neighborhood.
    # For each neighborhood, weight every tract's renter MHI by its renter
    # household count (and owner MHI by owner HH count) so a tract with 100
    # renters doesn't out-weigh a tract with 10.
    def _weighted_mean(df, val_col, w_col):
        sub = df.dropna(subset=[val_col, w_col])
        sub = sub[sub[w_col] > 0]
        if sub.empty:
            return float("nan")
        return (sub[val_col] * sub[w_col]).sum() / sub[w_col].sum()

    hood_records = []
    for name, grp in joined.groupby("name"):
        hood_records.append({
            "name": name,
            "total_evictions": grp["total_evictions"].sum(),
            "avg_corp_own_rate": grp["corp_own_rate"].mean(),
            "avg_own_occ_rate": grp["own_occ_rate"].mean(),
            "avg_renter_mhi": _weighted_mean(grp, "r_mhi", "renter_hh"),
            "avg_owner_mhi":  _weighted_mean(grp, "o_mhi", "owner_hh"),
        })
    hood_evict = pd.DataFrame(hood_records)
    hood_evict[["avg_corp_own_rate", "avg_own_occ_rate", "avg_renter_mhi", "avg_owner_mhi"]] = \
        hood_evict[["avg_corp_own_rate", "avg_own_occ_rate", "avg_renter_mhi", "avg_owner_mhi"]].round(3)

    # Citywide values: weight every tract by its household-tenure count, so
    # the citywide renter median is a true population-weighted aggregate of
    # tract-level renter medians (and owner equivalent).
    citywide_renter_mhi = _weighted_mean(tracts, "r_mhi", "renter_hh")
    citywide_owner_mhi = _weighted_mean(tracts, "o_mhi", "owner_hh")

    eviction_loaded = True
except Exception as e:
    print(f"Warning: census-tract eviction data unavailable ({e})")

# 6. (Deferred — neighborhoods.geojson written after ZORI calibration in step 9b)
hoods_geo_base = gpd.read_file(HOODS_GEO).to_crs(epsg=4326)
hoods_geo_base = hoods_geo_base.rename(columns={"blockgr2020_ctr_neighb_name": "name"})
hoods_geo_base = hoods_geo_base[~hoods_geo_base["name"].isin(EXCLUDE_HOODS)]

# Placeholder — neighborhoods.geojson written after ZORI calibration

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

# 8. Flag investor buyers (LLC, business, multi-property owner, or classified investor)
sales["investor_buyer"] = (
    (sales["buyer_llc_ind"] == 1) |
    (sales["buyer_bus_ind"] == 1) |
    (sales["tot_owned"] > 1) |
    (~sales["investor_type_purchase"].isin(["Non-investor", None, np.nan]))
).astype(bool)

# 9. Calibrate rents using ZORI — scale raw_rent (price/240) by ZORI correction per neighborhood-year
#    monthly_rent = raw_rent * (ZORI / raw_median) for that neighborhood-year
#    monthly_rent_now = monthly_rent * (latest_ZORI / sale_year_ZORI)
ZORI_CSV = BASE / "fp2" / "public" / "data" / "zori_zip.csv"
zori = pd.read_csv(ZORI_CSV)
zori["RegionName"] = zori["RegionName"].astype(str).str.zfill(5)

# Build lookup: (neighborhood, year) -> ZORI rent
zori_bos = zori[zori["RegionName"].isin(boston_zips)].copy()
zori_lookup = {}
for _, row in zori_bos.iterrows():
    hood = zip_to_hood.get(row["RegionName"])
    if not hood:
        continue
    for yr in range(2015, 2027):
        for month_col in [f"{yr}-07-31", f"{yr}-06-30", f"{yr}-01-31"]:
            if month_col in row.index and pd.notna(row[month_col]):
                zori_lookup.setdefault((hood, yr), []).append(row[month_col])
                break

zori_avg = {k: np.mean(v) for k, v in zori_lookup.items()}

# Compute correction factor per (neighborhood, year): ZORI / raw_median
correction = {}
for (hood, yr), zori_rent in zori_avg.items():
    mask = (sales["neighborhood"] == hood) & (sales["year"] == yr)
    if mask.sum() < 3:
        continue
    our_median = sales.loc[mask, "raw_rent"].median()
    if our_median > 0:
        correction[(hood, yr)] = zori_rent / our_median

# Fallbacks
hood_corrections = {}
for hood in sales["neighborhood"].unique():
    ratios = [v for (h, y), v in correction.items() if h == hood]
    hood_corrections[hood] = np.median(ratios) if ratios else None
global_correction = np.median(list(correction.values())) if correction else 0.73

def get_correction(row):
    c = correction.get((row["neighborhood"], int(row["year"])))
    if c is not None: return c
    c = hood_corrections.get(row["neighborhood"])
    if c is not None: return c
    return global_correction

sales["monthly_rent"] = (sales["raw_rent"] * sales.apply(get_correction, axis=1)).round(0).astype(int)

# monthly_rent_now: use ZORI appreciation (latest / sale_year)
zori_latest = {}
for hood in sales["neighborhood"].unique():
    for try_yr in range(2026, 2022, -1):
        val = zori_avg.get((hood, try_yr))
        if val is not None:
            zori_latest[hood] = val
            break

city_early = [v for (h, y), v in zori_avg.items() if y in (2018, 2019)]
city_late = [v for v in zori_latest.values()]
city_appreciation = (np.mean(city_late) / np.mean(city_early)) if city_early and city_late else 1.25

def get_now_rent(row):
    hood = row["neighborhood"]
    sale_yr = int(row["year"])
    zori_sale = zori_avg.get((hood, sale_yr))
    zori_now = zori_latest.get(hood)
    if zori_sale and zori_now and zori_sale > 0:
        return round(row["monthly_rent"] * (zori_now / zori_sale))
    early_z = zori_avg.get((hood, 2018)) or zori_avg.get((hood, 2019))
    if early_z and zori_now and early_z > 0:
        return round(row["monthly_rent"] * (zori_now / early_z))
    return round(row["monthly_rent"] * city_appreciation)

sales["monthly_rent_now"] = sales.apply(get_now_rent, axis=1)

print("ZORI-calibrated rents:")
for hood in sorted(sales["neighborhood"].unique())[:6]:
    sub = sales[sales["neighborhood"] == hood]
    print(f"  {hood}: raw ${sub['raw_rent'].median():,.0f} -> calibrated ${sub['monthly_rent'].median():,.0f}, now ${sub['monthly_rent_now'].median():,.0f}")

# 9b. Re-aggregate neighborhood stats with ZORI-calibrated rents and write geojson
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

if eviction_loaded:
    hood_stats = hood_stats.merge(hood_evict, on="name", how="left")

hoods_out = hoods_geo_base[["name", "geometry"]].merge(hood_stats, on="name", how="left")

features = []
for _, row in hoods_out.iterrows():
    fprops = {
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
        fprops["total_evictions"] = safe_int(row.get("total_evictions"))
        fprops["avg_corp_own_rate"] = safe_float(row.get("avg_corp_own_rate"))
        fprops["avg_own_occ_rate"] = safe_float(row.get("avg_own_occ_rate"))
        fprops["avg_renter_mhi"] = safe_int(row.get("avg_renter_mhi"))
        fprops["avg_owner_mhi"] = safe_int(row.get("avg_owner_mhi"))
    features.append({
        "type": "Feature",
        "properties": fprops,
        "geometry": mapping(row["geometry"]) if row["geometry"] else None,
    })

geojson_out = {"type": "FeatureCollection", "features": features}
if eviction_loaded:
    geojson_out["metadata"] = {
        "citywide_renter_mhi": safe_int(citywide_renter_mhi),
        "citywide_owner_mhi": safe_int(citywide_owner_mhi),
    }
with open(OUT / "neighborhoods.geojson", "w") as f:
    json.dump(geojson_out, f)

# 10. Write properties.json — include all detail fields for interactive popups
out_cols = ["lat", "lon", "monthly_rent", "monthly_rent_now", "year", "neighborhood",
            "address", "street", "zip",
            "bedrooms", "bathrooms", "totrooms", "proptype", "usage", "style",
            "yearbuilt", "intersf", "lotsize",
            "price", "date", "cash_sale", "flip_ind",
            "investor_buyer", "investor_type_purchase", "seller_llc_ind",
            "tot_owned", "had_eviction"]
# Keep only columns that actually exist
out_cols = [c for c in out_cols if c in sales.columns]
props = sales[out_cols].copy().rename(columns={"lon": "lng"})
props["lat"] = props["lat"].round(6)
props["lng"] = props["lng"].round(6)
props["bedrooms"] = props["bedrooms"].fillna(0).astype(int)
props["year"] = props["year"].fillna(0).astype(int)
props["price"] = props["price"].astype(int)
props["had_eviction"] = props["had_eviction"].astype(bool)
props["investor_buyer"] = props["investor_buyer"].astype(bool)
for c in ["bathrooms", "totrooms", "yearbuilt", "cash_sale", "flip_ind", "seller_llc_ind", "tot_owned"]:
    if c in props.columns:
        props[c] = pd.to_numeric(props[c], errors="coerce")
for c in ["intersf", "lotsize"]:
    if c in props.columns:
        props[c] = pd.to_numeric(props[c], errors="coerce").round(0)

records = props.astype(object).where(props.notna(), None).to_dict(orient="records")
with open(OUT / "properties.json", "w") as f:
    json.dump(records, f, allow_nan=False)

print(f"  {len(features)} neighborhoods, {len(records):,} properties")

# 11. Generate zori_by_neighborhood.json — monthly ZORI rent per neighborhood
zori_out = {}
for _, row in zori_bos.iterrows():
    hood = zip_to_hood.get(row["RegionName"])
    if not hood:
        continue
    if hood not in zori_out:
        zori_out[hood] = {}
    for dc in [c for c in row.index if c.startswith("20")]:
        if pd.notna(row[dc]):
            zori_out[hood].setdefault(dc, []).append(row[dc])

# Average across ZIPs per neighborhood, output as sorted list
zori_neighborhood = {}
for hood, date_vals in zori_out.items():
    entries = []
    for date_str in sorted(date_vals.keys()):
        entries.append({"date": date_str, "rent": round(np.mean(date_vals[date_str]))})
    zori_neighborhood[hood] = entries

with open(OUT / "zori_by_neighborhood.json", "w") as f:
    json.dump(zori_neighborhood, f)
print(f"  zori_by_neighborhood.json: {len(zori_neighborhood)} neighborhoods")

# 12. Generate evictions_by_neighborhood.json — aggregated eviction stats
EVICTION_FILINGS_CSV2 = (DATA / "Exploring corporate owners & evictions"
                         / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details "
                         / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details_filings.csv")
EVICTION_PLAINTIFFS_CSV = (DATA / "Exploring corporate owners & evictions"
                           / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details "
                           / "Evictions (2020-2024) Court Filings + Case Type + Property  ZIP + Attorney Details + Plaintiff Details_plaintiffs.csv")

try:
    ev_filings = pd.read_csv(EVICTION_FILINGS_CSV2)
    ev_ptf = pd.read_csv(EVICTION_PLAINTIFFS_CSV)

    # Tag corporate plaintiffs
    ev_ptf["name_upper"] = ev_ptf["name"].str.upper().fillna("")
    ev_ptf["is_corp"] = ev_ptf["name_upper"].str.contains(
        r"LLC|INC|CORP|LP |L\.P\.|TRUST|REALTY|MANAGEMENT|PROPERTIES|PARTNERS|"
        r"ASSOCIATES|HOUSING|AUTHORITY|CAPITAL|INVESTMENT|EQUITY|FUND|GROUP|"
        r"HOLDINGS|VENTURES|DEVELOPMENT", regex=True)
    corp_dockets = ev_ptf.groupby("docket_id")["is_corp"].any().reset_index()
    corp_dockets.columns = ["docket_id", "corp_landlord"]
    ev_filings = ev_filings.merge(corp_dockets, on="docket_id", how="left")
    ev_filings["corp_landlord"] = ev_filings["corp_landlord"].fillna(False)

    # Map to neighborhoods
    ev_filings["zip"] = ev_filings["zip"].astype(str).str.strip().str.zfill(5)
    ev_filings = ev_filings[ev_filings["zip"].isin(boston_zips)].copy()
    ev_filings["neighborhood"] = ev_filings["zip"].map(zip_to_hood)
    ev_filings["file_date"] = pd.to_datetime(ev_filings["file_date"], errors="coerce")
    ev_filings["file_year"] = ev_filings["file_date"].dt.year

    # Top plaintiffs per neighborhood
    ev_with_names = ev_filings.merge(
        ev_ptf[ev_ptf["is_corp"]][["docket_id", "name"]].drop_duplicates(),
        on="docket_id", how="left")

    eviction_data = {}
    for hood, grp in ev_filings.groupby("neighborhood"):
        total = len(grp)
        corp_count = int(grp["corp_landlord"].sum())
        case_types = grp["case_type"].value_counts().to_dict()
        by_year = grp.groupby("file_year").size().to_dict()
        by_year = {str(int(k)): int(v) for k, v in by_year.items() if pd.notna(k)}

        # Top 5 corporate plaintiffs
        hood_names = ev_with_names[ev_with_names["neighborhood"] == hood]
        top_ptf = (hood_names.dropna(subset=["name"])
                   .groupby("name")["docket_id"].nunique()
                   .sort_values(ascending=False).head(5))
        top_plaintiffs = [{"name": n, "count": int(c)} for n, c in top_ptf.items()]

        eviction_data[hood] = {
            "total_filings": total,
            "case_types": {k: int(v) for k, v in case_types.items()},
            "corp_filings": corp_count,
            "individual_filings": total - corp_count,
            "corp_rate": round(corp_count / total, 3) if total > 0 else 0,
            "by_year": by_year,
            "top_plaintiffs": top_plaintiffs,
        }

    with open(OUT / "evictions_by_neighborhood.json", "w") as f:
        json.dump(eviction_data, f)
    print(f"  evictions_by_neighborhood.json: {len(eviction_data)} neighborhoods, {ev_filings.shape[0]:,} filings")
except Exception as e:
    print(f"Warning: eviction aggregation failed ({e})")

# 13. Generate corp_ownership_timeseries.json — story intro data
CORP_OWN_CSV = (DATA / "Exploring corporate owners & evictions"
                / "Owner Occupancy (2004-2023) + Corporate Ownership (2004-2023) + Census Neighborhood Data (2020) "
                / "Corp_Ownership_and_Occupancy_Over_Time.csv")

try:
    corp = pd.read_csv(CORP_OWN_CSV)
    corp["own_occ_rate"] = pd.to_numeric(corp["own_occ_rate"], errors="coerce")
    corp["corp_own_rate"] = pd.to_numeric(corp["corp_own_rate"], errors="coerce")
    corp["Year"] = pd.to_numeric(corp["Year"], errors="coerce").astype(int)

    # Citywide averages
    city = corp.groupby("Year").agg(
        corp_own=("corp_own_rate", "mean"),
        own_occ=("own_occ_rate", "mean")
    ).reset_index()

    story_data = {
        "citywide": {
            "corp_ownership": [{"year": int(r["Year"]), "rate": round(r["corp_own"], 4)} for _, r in city.iterrows()],
            "owner_occupancy": [{"year": int(r["Year"]), "rate": round(r["own_occ"], 4)} for _, r in city.iterrows()],
        },
        "neighborhoods": {}
    }

    for hood in corp["Neighborhood"].unique():
        sub = corp[corp["Neighborhood"] == hood].sort_values("Year")
        story_data["neighborhoods"][hood] = {
            "corp_ownership": [{"year": int(r["Year"]), "rate": round(r["corp_own_rate"], 4)} for _, r in sub.iterrows()],
            "owner_occupancy": [{"year": int(r["Year"]), "rate": round(r["own_occ_rate"], 4)} for _, r in sub.iterrows()],
        }

    # Individual-to-corporate sales rate + investor type distribution from raw sales
    all_sales = pd.read_csv(SALES_CSV,
        usecols=["zip", "year", "buyer_llc_ind", "seller_llc_ind", "investor_type_purchase"],
        dtype={"zip": str})
    all_sales["zip"] = all_sales["zip"].str.strip().str.zfill(5)
    all_sales = all_sales[all_sales["zip"].isin(boston_zips)]
    all_sales["year"] = pd.to_numeric(all_sales["year"], errors="coerce")
    all_sales = all_sales[all_sales["year"].between(2004, 2023)].copy()
    all_sales["buyer_llc_ind"] = pd.to_numeric(all_sales["buyer_llc_ind"], errors="coerce").fillna(0)
    all_sales["seller_llc_ind"] = pd.to_numeric(all_sales["seller_llc_ind"], errors="coerce").fillna(0)

    # Sale-flow directions (by year) between individuals and LLC/corporate entities
    all_sales["ind_to_corp"] = (all_sales["seller_llc_ind"] == 0) & (all_sales["buyer_llc_ind"] == 1)
    all_sales["corp_to_ind"] = (all_sales["seller_llc_ind"] == 1) & (all_sales["buyer_llc_ind"] == 0)
    all_sales["ind_to_ind"]  = (all_sales["seller_llc_ind"] == 0) & (all_sales["buyer_llc_ind"] == 0)
    all_sales["corp_to_corp"] = (all_sales["seller_llc_ind"] == 1) & (all_sales["buyer_llc_ind"] == 1)

    by_year = all_sales.groupby("year").agg(
        total=("year", "count"),
        ind_to_corp=("ind_to_corp", "sum"),
        corp_to_ind=("corp_to_ind", "sum"),
        ind_to_ind=("ind_to_ind", "sum"),
        corp_to_corp=("corp_to_corp", "sum"),
    ).reset_index()
    for k in ("ind_to_corp", "corp_to_ind", "ind_to_ind", "corp_to_corp"):
        by_year[f"{k}_rate"] = (by_year[k] / by_year["total"]).round(4)

    story_data["citywide"]["ind_to_corp_rate"] = [
        {"year": int(r["year"]), "rate": float(r["ind_to_corp_rate"]), "count": int(r["ind_to_corp"])}
        for _, r in by_year.iterrows()
    ]
    story_data["citywide"]["sale_flow_rates"] = [
        {
            "year": int(r["year"]),
            "ind_to_corp": float(r["ind_to_corp_rate"]),
            "corp_to_ind": float(r["corp_to_ind_rate"]),
            "ind_to_ind":  float(r["ind_to_ind_rate"]),
            "corp_to_corp": float(r["corp_to_corp_rate"]),
        }
        for _, r in by_year.iterrows()
    ]

    # Investor type breakdown
    inv_types = all_sales.groupby(["year", "investor_type_purchase"]).size().unstack(fill_value=0)
    inv_pct = inv_types.div(inv_types.sum(axis=1), axis=0)
    investor_data = []
    for yr in sorted(inv_pct.index):
        row = {"year": int(yr)}
        for col in inv_pct.columns:
            key = col.lower().replace("-", "_").replace(" ", "_")
            row[key] = round(float(inv_pct.loc[yr, col]), 4)
        investor_data.append(row)
    story_data["citywide"]["investor_types"] = investor_data

    with open(OUT / "corp_ownership_timeseries.json", "w") as f:
        json.dump(story_data, f)
    print(f"  corp_ownership_timeseries.json: {len(story_data['neighborhoods'])} neighborhoods, {len(city)} years")

except Exception as e:
    print(f"Warning: story data generation failed ({e})")
    import traceback; traceback.print_exc()

# 14. Generate eviction_dots.json — individual eviction filings as map dots
#     Each dot = one eviction case with ZORI rent at filing time and now
try:
    ev_filings2 = pd.read_csv(EVICTION_FILINGS_CSV2)
    ev_ptf2 = pd.read_csv(EVICTION_PLAINTIFFS_CSV)

    # Corp plaintiff tagging
    ev_ptf2["name_upper"] = ev_ptf2["name"].str.upper().fillna("")
    ev_ptf2["is_corp"] = ev_ptf2["name_upper"].str.contains(
        r"LLC|INC|CORP|LP |L\.P\.|TRUST|REALTY|MANAGEMENT|PROPERTIES|PARTNERS|"
        r"ASSOCIATES|HOUSING|AUTHORITY|CAPITAL|INVESTMENT|EQUITY|FUND|GROUP|"
        r"HOLDINGS|VENTURES|DEVELOPMENT", regex=True)
    corp_dockets2 = ev_ptf2.groupby("docket_id").agg(
        corp_landlord=("is_corp", "any"),
        plaintiff_name=("name", "first")
    ).reset_index()
    ev_filings2 = ev_filings2.merge(corp_dockets2, on="docket_id", how="left")
    ev_filings2["corp_landlord"] = ev_filings2["corp_landlord"].fillna(False)

    # Filter to Boston with valid coords
    ev_filings2["zip"] = ev_filings2["zip"].astype(str).str.strip().str.zfill(5)
    ev_filings2 = ev_filings2[
        ev_filings2["zip"].isin(boston_zips) &
        ev_filings2["lat"].notna() &
        ev_filings2["long"].notna()
    ].copy()
    ev_filings2["neighborhood"] = ev_filings2["zip"].map(zip_to_hood)
    ev_filings2 = ev_filings2[ev_filings2["neighborhood"].notna()]

    # Parse dates
    ev_filings2["file_date"] = pd.to_datetime(ev_filings2["file_date"], errors="coerce")
    ev_filings2["file_year"] = ev_filings2["file_date"].dt.year
    ev_filings2["file_month"] = ev_filings2["file_date"].dt.strftime("%Y-%m")

    # Attach ZORI rent at filing time and now
    def get_zori_at_filing(row):
        hood = row["neighborhood"]
        yr = int(row["file_year"]) if pd.notna(row["file_year"]) else 2021
        val = zori_avg.get((hood, yr))
        if val: return round(val)
        for delta in [1, -1, 2]:
            val = zori_avg.get((hood, yr + delta))
            if val: return round(val)
        return None

    ev_filings2["rent_at_filing"] = ev_filings2.apply(get_zori_at_filing, axis=1)
    ev_filings2["rent_now"] = ev_filings2["neighborhood"].map(zori_latest)

    # Build output records
    def safe_str(v):
        return str(v) if pd.notna(v) else None

    dots = []
    for _, r in ev_filings2.iterrows():
        dots.append({
            "lat": round(r["lat"], 6),
            "lng": round(r["long"], 6),
            "address": safe_str(r.get("add1")) or safe_str(r.get("street")) or "",
            "unit": safe_str(r.get("add2")),
            "neighborhood": r["neighborhood"],
            "zip": r["zip"],
            "case_type": safe_str(r.get("case_type")),
            "file_date": r["file_date"].strftime("%Y-%m-%d") if pd.notna(r["file_date"]) else None,
            "file_year": int(r["file_year"]) if pd.notna(r["file_year"]) else None,
            "case_status": safe_str(r.get("case_status")),
            "dispo": safe_str(r.get("dispo")),
            "corp_landlord": bool(r["corp_landlord"]),
            "plaintiff": safe_str(r.get("plaintiff_name")),
            "rent_at_filing": int(r["rent_at_filing"]) if pd.notna(r.get("rent_at_filing")) else None,
            "rent_now": int(r["rent_now"]) if pd.notna(r.get("rent_now")) else None,
        })

    with open(OUT / "eviction_dots.json", "w") as f:
        json.dump(dots, f)
    print(f"  eviction_dots.json: {len(dots):,} cases")

except Exception as e:
    print(f"Warning: eviction dots generation failed ({e})")
    import traceback; traceback.print_exc()

print("Done.")
