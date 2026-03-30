"""Initial dataset exploration script for extremism dataset."""
import pandas as pd
import numpy as np
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

df = pd.read_csv('data/datasets/extremisim.csv', encoding='utf-8')

print("=" * 60)
print("EXTREMISM DATASET - COMPREHENSIVE EXPLORATION")
print("=" * 60)

print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e6:.2f} MB")
print(f"\nColumns: {list(df.columns)}")
print(f"\nData Types:\n{df.dtypes.to_string()}")

print(f"\n--- Missing Values ---")
print(df.isnull().sum().to_string())

print(f"\n--- Duplicates ---")
print(f"Exact duplicate rows: {df.duplicated().sum()}")
print(f"Duplicate messages: {df['Original_Message'].duplicated().sum()}")

print(f"\n--- Label Distribution ---")
print(df['Extremism_Label'].value_counts().to_string())
print(f"\nLabel proportions (%):")
print((df['Extremism_Label'].value_counts(normalize=True) * 100).round(2).to_string())

print(f"\n--- Message Length Statistics ---")
df['msg_len'] = df['Original_Message'].astype(str).str.len()
df['word_count'] = df['Original_Message'].astype(str).str.split().str.len()
print("Character length:")
print(df['msg_len'].describe().to_string())
print("\nWord count:")
print(df['word_count'].describe().to_string())

print(f"\n--- Stats by Label ---")
for label in sorted(df['Extremism_Label'].unique()):
    subset = df[df['Extremism_Label'] == label]
    print(f"\n  {label}:")
    print(f"    Count: {len(subset)}")
    print(f"    Avg char length: {subset['msg_len'].mean():.1f}")
    print(f"    Avg word count: {subset['word_count'].mean():.1f}")
    print(f"    Min words: {subset['word_count'].min()}")
    print(f"    Max words: {subset['word_count'].max()}")

print(f"\n--- Sample Messages ---")
for label in sorted(df['Extremism_Label'].unique()):
    print(f"\n  {label} examples:")
    samples = df[df['Extremism_Label'] == label]['Original_Message'].head(5)
    for i, s in enumerate(samples):
        print(f"    {i+1}. {str(s)[:120]}")

print(f"\n--- Data Quality ---")
empty = df['Original_Message'].isna().sum()
whitespace = (df['Original_Message'].astype(str).str.strip() == '').sum()
print(f"NaN messages: {empty}")
print(f"Whitespace-only messages: {whitespace}")
print(f"Usable rows: {len(df) - empty - whitespace}")
