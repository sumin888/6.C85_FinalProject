"""
eda_new_direction.py — EDA supporting the new project direction (displacement narrative)

Run: python3 eda_new_direction.py

Investigates East Boston as focal neighborhood:
  - Corporate ownership growth 2004→2024
  - Median estimated rent by year (2015→2022)
  - Investor purchase share by year
  - Before/after affordability: 2018 budget vs 2022 market
  - Eviction filing case types and volume
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OUT  = BASE / "out"

# ── Load datasets ─────────────────────────────────────────────────────────────
sales = pd.read_csv(
    DATA / "Residential_sales_transactions_data"
         / "Residential_sales_transactions_in_City_of_Boston_2000-2023"
         / "boston_residential_sales.csv"
)
corp_time = pd.read_csv(
    DATA / "Corporate_ownership_rates_and_owner_occupancy_rates_in_Boston_neighborhoods_2004-2024"
         / "Corp_Ownership_and_Occupancy_Over_Time.csv"
)
filings = pd.read_csv(OUT / "viz_eviction_filings_with_landlord_type.csv")
evict_tract = pd.read_csv(OUT / "viz1_eviction_by_tract.csv")

# ── 1. Correlation: corp ownership vs evictions (tract level) ─────────────────
evict_clean = evict_tract[['corp_own_rate', 'total_evictions', 'r_mhi', 'pct_bipoc']].dropna()
r = evict_clean['corp_own_rate'].corr(evict_clean['total_evictions'])
print(f"r(corp_own_rate vs total_evictions) = {r:.3f}")

# ── 2. Top neighborhoods by corp ownership growth 2004→2024 ───────────────────
pivot = corp_time.pivot(index='Neighborhood', columns='Year', values='corp_own_rate')
pivot['growth'] = pivot[2024] - pivot[2004]
print("\n=== BIGGEST CORP OWNERSHIP GROWTH 2004→2024 ===")
print(pivot[['growth', 2004, 2024]].sort_values('growth', ascending=False).head(10).to_string())

# ── 3. East Boston: corp ownership over time ──────────────────────────────────
eb_corp = corp_time[corp_time['Neighborhood'] == 'East Boston'].sort_values('Year')
print("\n=== EAST BOSTON: CORP OWNERSHIP 2015→2024 ===")
print(eb_corp[eb_corp['Year'] >= 2015][['Year', 'corp_own_rate', 'own_occ_rate']].to_string())

# ── 4. East Boston: sales data ────────────────────────────────────────────────
sales['zip'] = sales['zip'].astype('Int64')
eb = sales[sales['zip'] == 2128].copy()
eb['year'] = pd.to_numeric(eb['year'], errors='coerce')
eb['price'] = pd.to_numeric(eb['price'], errors='coerce')
eb = eb[(eb['year'] >= 2015) & (eb['price'] > 50000) & (eb['price'] < 3000000)]
eb['monthly_rent'] = eb['price'] / (20 * 12)

print(f"\nEast Boston sales 2015+: {len(eb)}")

# ── 5. Median rent by year ────────────────────────────────────────────────────
print("\n=== EAST BOSTON: MEDIAN ESTIMATED RENT BY YEAR ===")
rent_by_year = eb.groupby('year')['monthly_rent'].agg(['median', 'count']).round(0)
print(rent_by_year)

# ── 6. Investor purchase share by year ───────────────────────────────────────
print("\n=== EAST BOSTON: INVESTOR TYPE BREAKDOWN ===")
print(eb['investor_type_purchase'].value_counts())

eb['is_investor'] = (
    eb['investor_type_purchase'].notna() &
    (eb['investor_type_purchase'] != 'Non-investor')
)
inv_by_year = eb.groupby('year').agg(
    total=('price', 'count'),
    investor=('is_investor', 'sum')
).assign(inv_share=lambda x: (x['investor'] / x['total'] * 100).round(1))
print("\n=== INVESTOR SHARE BY YEAR ===")
print(inv_by_year)

# ── 7. Before/after affordability ────────────────────────────────────────────
med_2018 = eb[eb['year'] == 2018]['monthly_rent'].median()
above_2022 = (eb[eb['year'] == 2022]['monthly_rent'] > med_2018).mean() * 100
print(f"\n2018 median rent: ${med_2018:.0f}/mo")
print(f"% of 2022 sales above 2018 budget: {above_2022:.1f}%")

# ── 8. Eviction filings: case types ──────────────────────────────────────────
print("\n=== CITYWIDE EVICTION CASE TYPES ===")
print(filings['case_type'].value_counts(normalize=True).mul(100).round(1))

print("\n=== EAST BOSTON EVICTION FILINGS ===")
eb_filings = filings[filings['zip'].astype(str).str.zfill(5) == '02128']
print(eb_filings['eviction_year'].value_counts().sort_index())
print(f"Total: {len(eb_filings)}")
print(f"Non-payment %: {(eb_filings['case_type'] == 'Non-payment of Rent').mean() * 100:.1f}%")
