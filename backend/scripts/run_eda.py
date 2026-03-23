"""
Comprehensive Exploratory Data Analysis (EDA) for Global Terrorism Database.
Generates all visualizations and statistical analysis for the TDM project.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path
import os
import warnings
warnings.filterwarnings('ignore')

# --- Setup ---
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = Path("data/datasets/eda_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
plt.rcParams.update({
    'figure.figsize': (12, 7),
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.3,
})

print("Loading dataset...")
df = pd.read_csv('data/datasets/gtd.csv', encoding='latin-1', low_memory=False)
print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} columns\n")

# ============================================================
# 1. YEARLY TREND OF TERRORIST ATTACKS
# ============================================================
print("1. Generating yearly trend chart...")
fig, ax = plt.subplots(figsize=(14, 6))
yearly = df.groupby('iyear').size()
ax.fill_between(yearly.index, yearly.values, alpha=0.3, color='#d32f2f')
ax.plot(yearly.index, yearly.values, color='#d32f2f', linewidth=2)
ax.set_xlabel('Year')
ax.set_ylabel('Number of Attacks')
ax.set_title('Global Terrorism Incidents Over Time (1970-2017)', fontsize=14, fontweight='bold')
ax.annotate('Data gap:\n1993 missing', xy=(1993, 0), xytext=(1993, 8000),
            arrowprops=dict(arrowstyle='->', color='gray'), fontsize=9, color='gray', ha='center')
ax.annotate(f'Peak: {yearly.max():,}\n({yearly.idxmax()})', xy=(yearly.idxmax(), yearly.max()),
            xytext=(yearly.idxmax()-5, yearly.max()+1500),
            arrowprops=dict(arrowstyle='->', color='#d32f2f'), fontsize=10, fontweight='bold', color='#d32f2f')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '01_yearly_trend.png')
plt.close()

# ============================================================
# 2. TOP 15 COUNTRIES BY ATTACKS
# ============================================================
print("2. Generating top countries chart...")
fig, ax = plt.subplots(figsize=(12, 7))
top_countries = df['country_txt'].value_counts().head(15)
colors = sns.color_palette("Reds_r", n_colors=15)
bars = ax.barh(top_countries.index[::-1], top_countries.values[::-1], color=colors[::-1], edgecolor='white')
for bar, val in zip(bars, top_countries.values[::-1]):
    ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height()/2,
            f'{val:,}', va='center', fontsize=9)
ax.set_xlabel('Number of Attacks')
ax.set_title('Top 15 Countries by Number of Terrorist Attacks', fontsize=14, fontweight='bold')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '02_top_countries.png')
plt.close()

# ============================================================
# 3. ATTACK TYPE DISTRIBUTION
# ============================================================
print("3. Generating attack type distribution...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

attack_counts = df['attacktype1_txt'].value_counts()
colors_pie = sns.color_palette("Set2", n_colors=len(attack_counts))
wedges, texts, autotexts = ax1.pie(attack_counts.values, labels=None, autopct='%1.1f%%',
                                     colors=colors_pie, startangle=90, pctdistance=0.85)
ax1.set_title('Attack Types Distribution', fontsize=13, fontweight='bold')
for t in autotexts:
    t.set_fontsize(8)
ax1.legend(attack_counts.index, loc='center left', bbox_to_anchor=(-0.3, 0.5), fontsize=8)

ax2.barh(attack_counts.index[::-1], attack_counts.values[::-1],
         color=colors_pie[::-1], edgecolor='white')
ax2.set_xlabel('Number of Attacks')
ax2.set_title('Attack Types - Bar Chart', fontsize=13, fontweight='bold')
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '03_attack_types.png')
plt.close()

# ============================================================
# 4. TARGET TYPE DISTRIBUTION
# ============================================================
print("4. Generating target type distribution...")
fig, ax = plt.subplots(figsize=(12, 8))
targ_counts = df['targtype1_txt'].value_counts().head(15)
colors_targ = sns.color_palette("Blues_r", n_colors=15)
ax.barh(targ_counts.index[::-1], targ_counts.values[::-1], color=colors_targ[::-1], edgecolor='white')
for i, (idx, val) in enumerate(zip(targ_counts.index[::-1], targ_counts.values[::-1])):
    ax.text(val + 200, i, f'{val:,}', va='center', fontsize=9)
ax.set_xlabel('Number of Attacks')
ax.set_title('Top 15 Target Types in Terrorist Attacks', fontsize=14, fontweight='bold')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '04_target_types.png')
plt.close()

# ============================================================
# 5. WEAPON TYPE DISTRIBUTION
# ============================================================
print("5. Generating weapon type distribution...")
fig, ax = plt.subplots(figsize=(12, 7))
weap_counts = df['weaptype1_txt'].value_counts()
colors_weap = sns.color_palette("Oranges_r", n_colors=len(weap_counts))
ax.barh(weap_counts.index[::-1], weap_counts.values[::-1], color=colors_weap[::-1], edgecolor='white')
ax.set_xlabel('Number of Attacks')
ax.set_title('Weapon Types Used in Terrorist Attacks', fontsize=14, fontweight='bold')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '05_weapon_types.png')
plt.close()

# ============================================================
# 6. REGIONAL ANALYSIS
# ============================================================
print("6. Generating regional analysis...")
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# 6a - Regional counts
reg_counts = df['region_txt'].value_counts()
axes[0].barh(reg_counts.index[::-1], reg_counts.values[::-1],
             color=sns.color_palette("viridis", n_colors=12)[::-1], edgecolor='white')
axes[0].set_xlabel('Number of Attacks')
axes[0].set_title('Attacks by Region', fontsize=13, fontweight='bold')
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

# 6b - Regional trend over time
top_regions = df['region_txt'].value_counts().head(5).index
for region in top_regions:
    region_yearly = df[df['region_txt'] == region].groupby('iyear').size()
    axes[1].plot(region_yearly.index, region_yearly.values, linewidth=2, label=region)
axes[1].set_xlabel('Year')
axes[1].set_ylabel('Number of Attacks')
axes[1].set_title('Attack Trends by Top 5 Regions', fontsize=13, fontweight='bold')
axes[1].legend(fontsize=8, loc='upper left')
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '06_regional_analysis.png')
plt.close()

# ============================================================
# 7. CASUALTY ANALYSIS
# ============================================================
print("7. Generating casualty analysis...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 7a - Killed distribution (log scale)
kills = df['nkill'].dropna()
kills_capped = kills[kills <= 50]
axes[0, 0].hist(kills_capped, bins=50, color='#d32f2f', alpha=0.7, edgecolor='white')
axes[0, 0].set_xlabel('Number Killed')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].set_title('Distribution of Fatalities per Attack (capped at 50)', fontweight='bold')
axes[0, 0].axvline(kills.mean(), color='black', linestyle='--', label=f'Mean: {kills.mean():.2f}')
axes[0, 0].axvline(kills.median(), color='blue', linestyle='--', label=f'Median: {kills.median():.1f}')
axes[0, 0].legend()

# 7b - Wounded distribution
wounds = df['nwound'].dropna()
wounds_capped = wounds[wounds <= 50]
axes[0, 1].hist(wounds_capped, bins=50, color='#ff9800', alpha=0.7, edgecolor='white')
axes[0, 1].set_xlabel('Number Wounded')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].set_title('Distribution of Wounded per Attack (capped at 50)', fontweight='bold')
axes[0, 1].axvline(wounds.mean(), color='black', linestyle='--', label=f'Mean: {wounds.mean():.2f}')
axes[0, 1].axvline(wounds.median(), color='blue', linestyle='--', label=f'Median: {wounds.median():.1f}')
axes[0, 1].legend()

# 7c - Yearly casualties trend
yearly_kills = df.groupby('iyear')['nkill'].sum()
yearly_wounds = df.groupby('iyear')['nwound'].sum()
axes[1, 0].fill_between(yearly_kills.index, yearly_kills.values, alpha=0.3, color='#d32f2f')
axes[1, 0].plot(yearly_kills.index, yearly_kills.values, color='#d32f2f', linewidth=2, label='Killed')
axes[1, 0].fill_between(yearly_wounds.index, yearly_wounds.values, alpha=0.3, color='#ff9800')
axes[1, 0].plot(yearly_wounds.index, yearly_wounds.values, color='#ff9800', linewidth=2, label='Wounded')
axes[1, 0].set_xlabel('Year')
axes[1, 0].set_ylabel('Total Casualties')
axes[1, 0].set_title('Annual Casualties from Terrorism', fontweight='bold')
axes[1, 0].legend()
axes[1, 0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

# 7d - Avg kills per attack type
avg_kills = df.groupby('attacktype1_txt')['nkill'].mean().sort_values(ascending=True)
axes[1, 1].barh(avg_kills.index, avg_kills.values, color=sns.color_palette("Reds_r", n_colors=len(avg_kills)))
axes[1, 1].set_xlabel('Average Fatalities per Attack')
axes[1, 1].set_title('Average Lethality by Attack Type', fontweight='bold')
plt.savefig(OUTPUT_DIR / '07_casualty_analysis.png')
plt.close()

# ============================================================
# 8. TERROR GROUP ANALYSIS
# ============================================================
print("8. Generating terror group analysis...")
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Top 15 groups (excluding Unknown)
known_groups = df[df['gname'] != 'Unknown']
top_groups = known_groups['gname'].value_counts().head(15)

axes[0].barh(top_groups.index[::-1], top_groups.values[::-1],
             color=sns.color_palette("magma", n_colors=15)[::-1], edgecolor='white')
axes[0].set_xlabel('Number of Attacks')
axes[0].set_title('Top 15 Terrorist Groups by Attack Count', fontsize=13, fontweight='bold')
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

# Lethality of top groups
group_lethality = known_groups.groupby('gname')['nkill'].sum().sort_values(ascending=False).head(15)
axes[1].barh(group_lethality.index[::-1], group_lethality.values[::-1],
             color=sns.color_palette("flare", n_colors=15)[::-1], edgecolor='white')
axes[1].set_xlabel('Total Fatalities')
axes[1].set_title('Top 15 Most Lethal Terrorist Groups', fontsize=13, fontweight='bold')
axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '08_terror_groups.png')
plt.close()

# ============================================================
# 9. SUCCESS RATE ANALYSIS
# ============================================================
print("9. Generating success rate analysis...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Success by attack type
success_by_attack = df.groupby('attacktype1_txt')['success'].mean().sort_values(ascending=True)
colors_success = ['#4caf50' if v > 0.8 else '#ff9800' if v > 0.6 else '#f44336' for v in success_by_attack.values]
axes[0].barh(success_by_attack.index, success_by_attack.values * 100, color=colors_success, edgecolor='white')
axes[0].set_xlabel('Success Rate (%)')
axes[0].set_title('Attack Success Rate by Type', fontsize=13, fontweight='bold')
axes[0].set_xlim(0, 100)

# Success rate trend
yearly_success = df.groupby('iyear')['success'].mean() * 100
axes[1].plot(yearly_success.index, yearly_success.values, color='#2196f3', linewidth=2)
axes[1].fill_between(yearly_success.index, yearly_success.values, alpha=0.2, color='#2196f3')
axes[1].set_xlabel('Year')
axes[1].set_ylabel('Success Rate (%)')
axes[1].set_title('Attack Success Rate Over Time', fontsize=13, fontweight='bold')
axes[1].set_ylim(70, 100)
plt.savefig(OUTPUT_DIR / '09_success_analysis.png')
plt.close()

# ============================================================
# 10. SUICIDE ATTACKS ANALYSIS
# ============================================================
print("10. Generating suicide attack analysis...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Suicide attacks over time
suicide_yearly = df.groupby('iyear')['suicide'].sum()
axes[0].fill_between(suicide_yearly.index, suicide_yearly.values, alpha=0.3, color='#9c27b0')
axes[0].plot(suicide_yearly.index, suicide_yearly.values, color='#9c27b0', linewidth=2)
axes[0].set_xlabel('Year')
axes[0].set_ylabel('Number of Suicide Attacks')
axes[0].set_title('Suicide Attacks Over Time', fontsize=13, fontweight='bold')

# Suicide vs non-suicide lethality
suicide_data = df.groupby('suicide')['nkill'].mean()
labels = ['Non-Suicide', 'Suicide']
vals = [suicide_data.get(0, 0), suicide_data.get(1, 0)]
axes[1].bar(labels, vals, color=['#2196f3', '#9c27b0'], edgecolor='white', width=0.5)
for i, v in enumerate(vals):
    axes[1].text(i, v + 0.2, f'{v:.2f}', ha='center', fontweight='bold')
axes[1].set_ylabel('Average Fatalities per Attack')
axes[1].set_title('Avg Fatalities: Suicide vs Non-Suicide Attacks', fontsize=13, fontweight='bold')
plt.savefig(OUTPUT_DIR / '10_suicide_analysis.png')
plt.close()

# ============================================================
# 11. CORRELATION HEATMAP (Numeric Features)
# ============================================================
print("11. Generating correlation heatmap...")
numeric_cols = ['iyear', 'extended', 'success', 'suicide', 'attacktype1',
                'targtype1', 'nkill', 'nwound', 'nkillter', 'nwoundte',
                'individual', 'nperps', 'claimed', 'weaptype1', 'region']
numeric_df = df[numeric_cols].dropna()
corr = numeric_df.corr()

fig, ax = plt.subplots(figsize=(14, 11))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
            center=0, square=True, linewidths=0.5, ax=ax,
            cbar_kws={'shrink': 0.8}, vmin=-1, vmax=1)
ax.set_title('Correlation Matrix of Key Numeric Features', fontsize=14, fontweight='bold')
plt.savefig(OUTPUT_DIR / '11_correlation_heatmap.png')
plt.close()

# ============================================================
# 12. MISSING VALUES ANALYSIS
# ============================================================
print("12. Generating missing values chart...")
missing_pct = df.isnull().mean().sort_values(ascending=False)
# Show columns with meaningful missingness (between 1% and 99%)
interesting_missing = missing_pct[(missing_pct > 0.01) & (missing_pct < 0.99)]

fig, ax = plt.subplots(figsize=(12, 10))
colors_miss = ['#f44336' if v > 0.5 else '#ff9800' if v > 0.2 else '#4caf50' for v in interesting_missing.values]
ax.barh(interesting_missing.index[::-1], interesting_missing.values[::-1] * 100,
        color=colors_miss[::-1], edgecolor='white')
ax.set_xlabel('Missing Values (%)')
ax.set_title('Missing Values by Column (1%-99% range)', fontsize=14, fontweight='bold')
ax.axvline(50, color='red', linestyle='--', alpha=0.5, label='50% threshold')
ax.legend()
plt.savefig(OUTPUT_DIR / '12_missing_values.png')
plt.close()

# ============================================================
# 13. GEOGRAPHIC DISTRIBUTION (Scatter on axes)
# ============================================================
print("13. Generating geographic scatter...")
geo_df = df.dropna(subset=['latitude', 'longitude'])
geo_sample = geo_df.sample(min(30000, len(geo_df)), random_state=42)

fig, ax = plt.subplots(figsize=(16, 9))
scatter = ax.scatter(geo_sample['longitude'], geo_sample['latitude'],
                     c=geo_sample['iyear'], cmap='YlOrRd', alpha=0.3, s=3)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Geographic Distribution of Terrorist Attacks (colored by year)', fontsize=14, fontweight='bold')
ax.set_xlim(-180, 180)
ax.set_ylim(-60, 80)
cbar = plt.colorbar(scatter, ax=ax, shrink=0.7)
cbar.set_label('Year')
plt.savefig(OUTPUT_DIR / '13_geographic_scatter.png')
plt.close()

# ============================================================
# 14. MONTHLY/SEASONAL PATTERNS
# ============================================================
print("14. Generating seasonal pattern chart...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Monthly distribution
monthly = df[df['imonth'] > 0].groupby('imonth').size()
month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
axes[0].bar(range(1, 13), monthly.values, color=sns.color_palette("coolwarm", 12), edgecolor='white')
axes[0].set_xticks(range(1, 13))
axes[0].set_xticklabels(month_names)
axes[0].set_xlabel('Month')
axes[0].set_ylabel('Number of Attacks')
axes[0].set_title('Seasonal Distribution of Attacks', fontsize=13, fontweight='bold')
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

# Day of month
daily = df[df['iday'] > 0].groupby('iday').size()
axes[1].plot(daily.index, daily.values, color='#2196f3', linewidth=2)
axes[1].fill_between(daily.index, daily.values, alpha=0.2, color='#2196f3')
axes[1].set_xlabel('Day of Month')
axes[1].set_ylabel('Number of Attacks')
axes[1].set_title('Attacks by Day of Month', fontsize=13, fontweight='bold')
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
plt.savefig(OUTPUT_DIR / '14_seasonal_patterns.png')
plt.close()

# ============================================================
# 15. FEATURE DISTRIBUTION BOXPLOTS
# ============================================================
print("15. Generating feature boxplots...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Kills by region (top 6)
top_6_regions = df['region_txt'].value_counts().head(6).index
region_kills = df[df['region_txt'].isin(top_6_regions)]
box_data = [region_kills[region_kills['region_txt'] == r]['nkill'].dropna().clip(upper=20) for r in top_6_regions]
bp = axes[0, 0].boxplot(box_data, labels=[r[:20] for r in top_6_regions], patch_artist=True)
for patch, color in zip(bp['boxes'], sns.color_palette("Set2", 6)):
    patch.set_facecolor(color)
axes[0, 0].set_ylabel('Fatalities (capped at 20)')
axes[0, 0].set_title('Fatalities Distribution by Region', fontweight='bold', fontsize=11)
axes[0, 0].tick_params(axis='x', rotation=30, labelsize=8)

# Kills by attack type (top 6)
top_6_attacks = df['attacktype1_txt'].value_counts().head(6).index
box_data2 = [df[df['attacktype1_txt'] == a]['nkill'].dropna().clip(upper=20) for a in top_6_attacks]
bp2 = axes[0, 1].boxplot(box_data2, labels=[a[:20] for a in top_6_attacks], patch_artist=True)
for patch, color in zip(bp2['boxes'], sns.color_palette("Set3", 6)):
    patch.set_facecolor(color)
axes[0, 1].set_ylabel('Fatalities (capped at 20)')
axes[0, 1].set_title('Fatalities Distribution by Attack Type', fontweight='bold', fontsize=11)
axes[0, 1].tick_params(axis='x', rotation=30, labelsize=8)

# Year distribution
axes[1, 0].hist(df['iyear'], bins=48, color='#607d8b', edgecolor='white', alpha=0.8)
axes[1, 0].set_xlabel('Year')
axes[1, 0].set_ylabel('Number of Attacks')
axes[1, 0].set_title('Year Distribution of All Attacks', fontweight='bold', fontsize=11)

# Kills distribution (log scale)
kills_nonzero = df['nkill'].dropna()
kills_nonzero = kills_nonzero[kills_nonzero > 0]
axes[1, 1].hist(np.log10(kills_nonzero), bins=50, color='#d32f2f', edgecolor='white', alpha=0.8)
axes[1, 1].set_xlabel('log10(Fatalities)')
axes[1, 1].set_ylabel('Frequency')
axes[1, 1].set_title('Fatalities Distribution (log scale)', fontweight='bold', fontsize=11)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '15_feature_distributions.png')
plt.close()

# ============================================================
# PRINT SUMMARY STATISTICS FOR REPORT
# ============================================================
print("\n" + "=" * 60)
print("EDA SUMMARY STATISTICS")
print("=" * 60)

print(f"\nDataset: Global Terrorism Database (GTD)")
print(f"Records: {df.shape[0]:,}")
print(f"Features: {df.shape[1]}")
print(f"Time span: {df['iyear'].min()} - {df['iyear'].max()}")
print(f"Missing 1993 data: Yes (data not collected that year)")

print(f"\nKey Metrics:")
print(f"  Total attacks: {len(df):,}")
print(f"  Total killed: {df['nkill'].sum():,.0f}")
print(f"  Total wounded: {df['nwound'].sum():,.0f}")
print(f"  Countries affected: {df['country_txt'].nunique()}")
print(f"  Unique groups: {df['gname'].nunique():,}")
print(f"  Unknown perpetrator: {(df['gname']=='Unknown').sum():,} ({(df['gname']=='Unknown').mean()*100:.1f}%)")

print(f"\nData Quality:")
cols_all_present = (df.isnull().mean() == 0).sum()
cols_mostly_missing = (df.isnull().mean() > 0.9).sum()
print(f"  Columns with no missing: {cols_all_present}/{df.shape[1]}")
print(f"  Columns >90% missing: {cols_mostly_missing}/{df.shape[1]}")
print(f"  Duplicate records: {df.duplicated().sum()}")
print(f"  Duplicate event IDs: {df['eventid'].duplicated().sum()}")

# Outlier detection for casualties
kills = df['nkill'].dropna()
q1, q3 = kills.quantile(0.25), kills.quantile(0.75)
iqr = q3 - q1
upper = q3 + 1.5 * iqr
outliers = (kills > upper).sum()
print(f"\n  Casualty outliers (IQR method, nkill > {upper:.0f}): {outliers:,} ({outliers/len(kills)*100:.1f}%)")

print(f"\nAll 15 visualizations saved to: {OUTPUT_DIR}/")
print("Done!")
