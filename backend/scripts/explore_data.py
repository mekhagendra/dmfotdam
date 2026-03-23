"""Initial dataset exploration script for GTD."""
import pandas as pd
import numpy as np
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

df = pd.read_csv('data/datasets/gtd.csv', encoding='latin-1', low_memory=False)

print("=" * 60)
print("GLOBAL TERRORISM DATABASE - INITIAL EXPLORATION")
print("=" * 60)

print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

print(f"\nYear range: {df['iyear'].min()} - {df['iyear'].max()}")
print(f"Countries: {df['country_txt'].nunique()}")
print(f"Regions: {df['region_txt'].nunique()}")
print(f"Attack types: {df['attacktype1_txt'].nunique()}")
print(f"Target types: {df['targtype1_txt'].nunique()}")
print(f"Weapon types: {df['weaptype1_txt'].nunique()}")
print(f"Terrorist groups: {df['gname'].nunique()}")
print(f"Successful attacks: {df['success'].sum():,} / {len(df):,} ({df['success'].mean()*100:.1f}%)")
print(f"Suicide attacks: {df['suicide'].sum():,}")

print("\n--- Top 10 Countries ---")
print(df['country_txt'].value_counts().head(10).to_string())

print("\n--- Attack Types ---")
print(df['attacktype1_txt'].value_counts().to_string())

print("\n--- Target Types (Top 10) ---")
print(df['targtype1_txt'].value_counts().head(10).to_string())

print("\n--- Weapon Types ---")
print(df['weaptype1_txt'].value_counts().to_string())

print("\n--- Top 10 Regions ---")
print(df['region_txt'].value_counts().head(12).to_string())

print("\n--- Top 15 Groups ---")
top_groups = df['gname'].value_counts().head(16)
print(top_groups.to_string())

print("\n--- Yearly Trend ---")
yearly = df.groupby('iyear').size()
print(yearly.to_string())

print("\n--- Casualty Statistics ---")
for col in ['nkill', 'nwound', 'nkillter', 'nwoundte']:
    if col in df.columns:
        s = df[col].dropna()
        print(f"  {col}: count={len(s):,}, mean={s.mean():.2f}, median={s.median():.1f}, max={s.max():.0f}, sum={s.sum():.0f}")

print("\n--- Missing Value Summary (columns with >0% missing, top 20) ---")
missing = df.isnull().mean().sort_values(ascending=False)
for col, pct in missing.head(20).items():
    if pct > 0:
        print(f"  {col}: {pct*100:.1f}%")

print("\n--- Data Types Summary ---")
print(df.dtypes.value_counts().to_string())

print("\n--- Duplicate Rows ---")
print(f"  Exact duplicates: {df.duplicated().sum()}")
print(f"  Duplicate eventids: {df['eventid'].duplicated().sum()}")
