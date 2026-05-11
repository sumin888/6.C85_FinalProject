"""
eda_viz.py — Visualizations backing the displacement narrative
Focuses on East Boston (02128) and South Boston Waterfront (02210)

Run: python3 eda_viz.py
Outputs saved to: out/eda_charts/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OUT  = BASE / "out" / "eda_charts"
OUT.mkdir(parents=True, exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────────────────
EB_COLOR  = "#c0392b"   # red — East Boston
SBW_COLOR = "#2471a3"   # blue — South Boston Waterfront
GRAY      = "#aaaaaa"
BG        = "#f9f9f9"

# ── Load data ─────────────────────────────────────────────────────────────────
sales = pd.read_csv(
    DATA / "Residential_sales_transactions_data"
         / "Residential_sales_transactions_in_City_of_Boston_2000-2023"
         / "boston_residential_sales.csv"
)
corp_time = pd.read_csv(
    DATA / "Corporate_ownership_rates_and_owner_occupancy_rates_in_Boston_neighborhoods_2004-2024"
         / "Corp_Ownership_and_Occupancy_Over_Time.csv"
)
filings = pd.read_csv(BASE / "out" / "viz_eviction_filings_with_landlord_type.csv")

# Clean sales
sales['zip'] = sales['zip'].astype('Int64')
sales['year'] = pd.to_numeric(sales['year'], errors='coerce')
sales['price'] = pd.to_numeric(sales['price'], errors='coerce')

NEIGHBORHOODS = {
    2128:  ("East Boston",           EB_COLOR),
    2210:  ("South Boston Waterfront", SBW_COLOR),
}
ZIPS_FILINGS = {
    "02128": ("East Boston",           EB_COLOR),
    "02210": ("South Boston Waterfront", SBW_COLOR),
}

def prep_sales(zip_code):
    df = sales[sales['zip'] == zip_code].copy()
    df = df[(df['year'] >= 2015) & (df['price'] > 50000) & (df['price'] < 5_000_000)]
    df['monthly_rent'] = df['price'] / (20 * 12)
    df['is_investor'] = (
        df['investor_type_purchase'].notna() &
        (df['investor_type_purchase'] != 'Non-investor')
    )
    return df

# ══════════════════════════════════════════════════════════════════════════════
# CHART 1: Corporate Ownership Rate Over Time (2004–2024)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
fig.suptitle("Corporate Ownership Rate Over Time (2004–2024)", fontsize=14, fontweight='bold', y=1.01)

for ax, (hood, color) in zip(axes, [
    ("East Boston", EB_COLOR),
    ("South Boston Waterfront", SBW_COLOR)
]):
    df = corp_time[corp_time['Neighborhood'] == hood].sort_values('Year')
    ax.fill_between(df['Year'], df['corp_own_rate'] * 100, alpha=0.15, color=color)
    ax.plot(df['Year'], df['corp_own_rate'] * 100, color=color, linewidth=2.5, marker='o', markersize=4)
    ax.plot(df['Year'], df['own_occ_rate'] * 100, color=GRAY, linewidth=1.5, linestyle='--', label='Owner-occupancy rate')

    # Annotate start and end
    start = df[df['Year'] == 2004]['corp_own_rate'].values[0] * 100
    end   = df[df['Year'] == 2024]['corp_own_rate'].values[0] * 100
    ax.annotate(f"{start:.0f}%", xy=(2004, start), xytext=(2005, start + 2), fontsize=9, color=color)
    ax.annotate(f"{end:.0f}%", xy=(2024, end), xytext=(2021, end + 2), fontsize=9, color=color, fontweight='bold')

    ax.set_title(hood, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel("Year")
    ax.set_ylabel("Rate (%)")
    ax.set_facecolor(BG)
    ax.set_ylim(0, 55)
    ax.legend(["Corporate ownership", "Owner-occupancy"], fontsize=8, loc='upper left')
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "01_corp_ownership_over_time.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 01_corp_ownership_over_time.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 2: Median Estimated Rent by Year (2015–2022)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
fig.suptitle("Median Estimated Monthly Rent by Year\n(from sale prices, price-to-rent ratio = 20)", fontsize=13, fontweight='bold', y=1.02)

for ax, (zip_code, (hood, color)) in zip(axes, NEIGHBORHOODS.items()):
    df = prep_sales(zip_code)
    rent = df.groupby('year')['monthly_rent'].median()

    ax.bar(rent.index, rent.values, color=color, alpha=0.8, width=0.6)

    # Add 2018 reference line
    med_2018 = rent.get(2018, None)
    if med_2018:
        ax.axhline(med_2018, color='black', linestyle='--', linewidth=1.2, alpha=0.7)
        ax.text(rent.index[-1] + 0.3, med_2018 + 30, f"2018 baseline\n${med_2018:,.0f}/mo",
                fontsize=8, color='black', va='bottom')

    # Annotate each bar
    for yr, val in rent.items():
        ax.text(yr, val + 40, f"${val:,.0f}", ha='center', fontsize=7.5, color='#333')

    ax.set_title(hood, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel("Year")
    ax.set_ylabel("Median Est. Monthly Rent ($)")
    ax.set_facecolor(BG)
    ax.set_ylim(0, rent.max() * 1.25)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "02_median_rent_by_year.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 02_median_rent_by_year.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 3: Investor Purchase Share by Year
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
fig.suptitle("Investor Purchase Share by Year (%)", fontsize=14, fontweight='bold', y=1.01)

for ax, (zip_code, (hood, color)) in zip(axes, NEIGHBORHOODS.items()):
    df = prep_sales(zip_code)
    inv = df.groupby('year').agg(
        total=('price', 'count'),
        investor=('is_investor', 'sum')
    ).assign(inv_share=lambda x: x['investor'] / x['total'] * 100)

    bars = ax.bar(inv.index, inv['inv_share'], color=color, alpha=0.8, width=0.6)

    # Highlight peak year
    peak_yr = inv['inv_share'].idxmax()
    peak_val = inv['inv_share'].max()
    bars[list(inv.index).index(peak_yr)].set_color('#e67e22')
    ax.text(peak_yr, peak_val + 0.8, f"Peak\n{peak_val:.1f}%", ha='center',
            fontsize=8, color='#e67e22', fontweight='bold')

    ax.axhline(50, color='red', linestyle=':', linewidth=1, alpha=0.5)
    ax.text(inv.index[-1] + 0.3, 50.5, "50%", fontsize=8, color='red', alpha=0.7)

    ax.set_title(hood, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel("Year")
    ax.set_ylabel("Investor Purchase Share (%)")
    ax.set_facecolor(BG)
    ax.set_ylim(0, 70)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "03_investor_share_by_year.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 03_investor_share_by_year.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 4: Before/After Affordability
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
fig.suptitle("Before/After Affordability: % of Sales Above 2018 Median Budget",
             fontsize=13, fontweight='bold', y=1.02)

for ax, (zip_code, (hood, color)) in zip(axes, NEIGHBORHOODS.items()):
    df = prep_sales(zip_code)
    med_2018 = df[df['year'] == 2018]['monthly_rent'].median()
    if pd.isna(med_2018):
        continue

    years = sorted(df['year'].dropna().unique())
    pct_above = []
    for yr in years:
        subset = df[df['year'] == yr]['monthly_rent']
        pct_above.append((subset > med_2018).mean() * 100)

    bar_colors = ['#2ecc71' if p < 50 else color for p in pct_above]
    bars = ax.bar(years, pct_above, color=bar_colors, alpha=0.85, width=0.6)

    ax.axhline(50, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(2018, color='black', linestyle=':', linewidth=1.2, alpha=0.6)
    ax.text(2018.1, max(pct_above) * 0.95, "2018\nbaseline", fontsize=8, color='black')

    for yr, val in zip(years, pct_above):
        ax.text(yr, val + 1, f"{val:.0f}%", ha='center', fontsize=7.5, color='#333')

    ax.set_title(f"{hood}\n2018 baseline: ${med_2018:,.0f}/mo", fontsize=11, fontweight='bold', color=color)
    ax.set_xlabel("Year")
    ax.set_ylabel("% of Sales Above 2018 Median Budget")
    ax.set_facecolor(BG)
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    green_patch = mpatches.Patch(color='#2ecc71', label='< 50% above budget (affordable era)')
    red_patch   = mpatches.Patch(color=color,     label='≥ 50% above budget (displacement era)')
    ax.legend(handles=[green_patch, red_patch], fontsize=8, loc='upper left')

plt.tight_layout()
plt.savefig(OUT / "04_before_after_affordability.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 04_before_after_affordability.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 5: Eviction Filings by Year
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
fig.suptitle("Eviction Filings by Year and Case Type", fontsize=14, fontweight='bold', y=1.01)

filings['zip'] = filings['zip'].astype(str).str.zfill(5)

for ax, (zip_code, (hood, color)) in zip(axes, ZIPS_FILINGS.items()):
    df = filings[filings['zip'] == zip_code].copy()
    df = df[df['eviction_year'].between(2019, 2022)]

    if len(df) == 0:
        ax.set_title(f"{hood}\n(no data)", fontsize=11)
        continue

    # Stack by case type simplified
    df['case_simple'] = df['case_type'].apply(lambda x:
        'Non-payment of Rent' if x == 'Non-payment of Rent'
        else 'No Cause' if x == 'No Cause'
        else 'Other'
    )

    pivot = df.groupby(['eviction_year', 'case_simple']).size().unstack(fill_value=0)
    case_colors = {
        'Non-payment of Rent': color,
        'No Cause':            '#e67e22',
        'Other':               GRAY,
    }
    bottom = np.zeros(len(pivot))
    for case in ['Non-payment of Rent', 'No Cause', 'Other']:
        if case in pivot.columns:
            vals = pivot[case].values
            ax.bar(pivot.index, vals, bottom=bottom,
                   label=case, color=case_colors[case], alpha=0.85, width=0.5)
            bottom += vals

    # Annotate total
    for yr, tot in zip(pivot.index, bottom):
        ax.text(yr, tot + 1, str(int(tot)), ha='center', fontsize=9, fontweight='bold')

    pct_nonpay = (df['case_type'] == 'Non-payment of Rent').mean() * 100
    ax.set_title(f"{hood}\n{pct_nonpay:.1f}% non-payment of rent", fontsize=11, fontweight='bold', color=color)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Filings")
    ax.set_facecolor(BG)
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "05_eviction_filings_by_year.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 05_eviction_filings_by_year.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 6: Combined Summary — Corp Ownership vs Evictions (East Boston)
# ══════════════════════════════════════════════════════════════════════════════
fig, ax1 = plt.subplots(figsize=(11, 5), facecolor=BG)
fig.suptitle("East Boston: Corporate Ownership vs Eviction Filings Over Time",
             fontsize=13, fontweight='bold')

eb_corp = corp_time[corp_time['Neighborhood'] == 'East Boston'].sort_values('Year')
eb_corp = eb_corp[eb_corp['Year'].between(2015, 2024)]

eb_fil = filings[filings['zip'] == '02128'].copy()
eb_fil = eb_fil[eb_fil['eviction_year'].between(2015, 2022)]
fil_by_year = eb_fil.groupby('eviction_year').size()

ax2 = ax1.twinx()

ax1.fill_between(eb_corp['Year'], eb_corp['corp_own_rate'] * 100,
                 alpha=0.15, color=EB_COLOR)
ax1.plot(eb_corp['Year'], eb_corp['corp_own_rate'] * 100,
         color=EB_COLOR, linewidth=2.5, marker='o', label='Corp ownership rate (%)')

ax2.bar(fil_by_year.index, fil_by_year.values,
        color='#e67e22', alpha=0.6, width=0.5, label='Eviction filings')

ax1.set_xlabel("Year")
ax1.set_ylabel("Corporate Ownership Rate (%)", color=EB_COLOR)
ax2.set_ylabel("Eviction Filings (count)", color='#e67e22')
ax1.tick_params(axis='y', labelcolor=EB_COLOR)
ax2.tick_params(axis='y', labelcolor='#e67e22')
ax1.set_facecolor(BG)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc='upper left')
ax1.grid(axis='y', alpha=0.2)

plt.tight_layout()
plt.savefig(OUT / "06_eb_corp_ownership_vs_evictions.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 06_eb_corp_ownership_vs_evictions.png")

print(f"\nAll charts saved to: {OUT}")
