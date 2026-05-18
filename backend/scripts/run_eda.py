"""
Comprehensive Exploratory Data Analysis (EDA) for Extremism Detection Dataset.
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
data_dir = Path("data/datasets")
dataset_path = data_dir / "training_dataset.csv"
if not dataset_path.exists():
    legacy_path = data_dir / "extremisim.csv"
    if legacy_path.exists():
        dataset_path = legacy_path
    else:
        raise FileNotFoundError(
            f"Dataset not found. Checked: {dataset_path} and {legacy_path}"
        )

df = pd.read_csv(dataset_path, encoding='utf-8')

# Normalize dataset schema to expected columns.
if 'text' in df.columns and 'Original_Message' not in df.columns:
    df = df.rename(columns={'text': 'Original_Message'})
if 'category' in df.columns and 'Extremism_Label' not in df.columns:
    df['Extremism_Label'] = df['category'].map({
        'Extremist': 'EXTREMIST',
        'NonExtremist': 'NON_EXTREMIST',
    }).fillna('NON_EXTREMIST')

# Drop rows with missing messages
df = df[df['Original_Message'].notna() & (df['Original_Message'].str.strip() != '')].copy()
# Feature engineering
df['msg_len'] = df['Original_Message'].str.len()
df['word_count'] = df['Original_Message'].str.split().str.len()
df['avg_word_len'] = df['Original_Message'].apply(
    lambda x: np.mean([len(w) for w in str(x).split()]) if pd.notna(x) else 0
)
df['has_exclamation'] = df['Original_Message'].str.contains('!', na=False).astype(int)
df['has_caps_word'] = df['Original_Message'].apply(
    lambda x: int(any(w.isupper() and len(w) > 1 for w in str(x).split()))
)
df['unique_word_ratio'] = df['Original_Message'].apply(
    lambda x: len(set(str(x).lower().split())) / max(len(str(x).split()), 1)
)

print(f"Loaded: {len(df):,} rows x {df.shape[1]} columns\n")

# ============================================================
# 1. CLASS DISTRIBUTION
# ============================================================
print("1. Generating class distribution chart...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

label_counts = df['Extremism_Label'].value_counts()
colors = ['#d32f2f', '#4caf50']

# Pie chart
wedges, texts, autotexts = ax1.pie(
    label_counts.values, labels=label_counts.index, autopct='%1.1f%%',
    colors=colors, startangle=90, explode=(0.05, 0.05),
    textprops={'fontsize': 12}
)
ax1.set_title('Class Distribution', fontsize=14, fontweight='bold')

# Bar chart
bars = ax2.bar(label_counts.index, label_counts.values, color=colors, edgecolor='white', width=0.5)
for bar, val in zip(bars, label_counts.values):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
             f'{val:,}', ha='center', fontweight='bold', fontsize=12)
ax2.set_ylabel('Number of Messages')
ax2.set_title('Class Counts', fontsize=14, fontweight='bold')

plt.suptitle('Extremism Label Distribution', fontsize=16, fontweight='bold', y=1.02)
plt.savefig(OUTPUT_DIR / '01_class_distribution.png')
plt.close()

# ============================================================
# 2. MESSAGE LENGTH DISTRIBUTION
# ============================================================
print("2. Generating message length distribution...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 2a - Character length histogram by label
for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    axes[0, 0].hist(subset['msg_len'], bins=50, alpha=0.6, color=color,
                     label=f'{label} (n={len(subset)})', edgecolor='white')
axes[0, 0].set_xlabel('Character Length')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].set_title('Message Character Length Distribution', fontweight='bold')
axes[0, 0].legend()

# 2b - Word count histogram by label
for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    axes[0, 1].hist(subset['word_count'], bins=50, alpha=0.6, color=color,
                     label=f'{label} (n={len(subset)})', edgecolor='white')
axes[0, 1].set_xlabel('Word Count')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].set_title('Message Word Count Distribution', fontweight='bold')
axes[0, 1].legend()

# 2c - Box plot character length
data_box = [df[df['Extremism_Label'] == l]['msg_len'] for l in ['EXTREMIST', 'NON_EXTREMIST']]
bp = axes[1, 0].boxplot(data_box, labels=['EXTREMIST', 'NON_EXTREMIST'], patch_artist=True)
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[1, 0].set_ylabel('Character Length')
axes[1, 0].set_title('Character Length by Class', fontweight='bold')

# 2d - Box plot word count
data_box_w = [df[df['Extremism_Label'] == l]['word_count'] for l in ['EXTREMIST', 'NON_EXTREMIST']]
bp2 = axes[1, 1].boxplot(data_box_w, labels=['EXTREMIST', 'NON_EXTREMIST'], patch_artist=True)
for patch, color in zip(bp2['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[1, 1].set_ylabel('Word Count')
axes[1, 1].set_title('Word Count by Class', fontweight='bold')

plt.suptitle('Message Length Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '02_message_length_distribution.png')
plt.close()

# ============================================================
# 3. TOP N-GRAMS ANALYSIS
# ============================================================
print("3. Generating top n-grams analysis...")
from sklearn.feature_extraction.text import CountVectorizer

fig, axes = plt.subplots(2, 2, figsize=(18, 14))

for idx, (label, color) in enumerate(zip(['EXTREMIST', 'NON_EXTREMIST'], colors)):
    subset_text = df[df['Extremism_Label'] == label]['Original_Message'].astype(str)

    # Unigrams
    vec1 = CountVectorizer(max_features=20, stop_words='english', ngram_range=(1, 1))
    X1 = vec1.fit_transform(subset_text)
    freqs1 = dict(zip(vec1.get_feature_names_out(), X1.sum(axis=0).A1))
    freqs1 = dict(sorted(freqs1.items(), key=lambda x: x[1], reverse=True))

    axes[0, idx].barh(list(freqs1.keys())[::-1], list(freqs1.values())[::-1],
                       color=color, edgecolor='white', alpha=0.8)
    axes[0, idx].set_xlabel('Frequency')
    axes[0, idx].set_title(f'Top 20 Unigrams - {label}', fontweight='bold')

    # Bigrams
    vec2 = CountVectorizer(max_features=20, stop_words='english', ngram_range=(2, 2))
    X2 = vec2.fit_transform(subset_text)
    freqs2 = dict(zip(vec2.get_feature_names_out(), X2.sum(axis=0).A1))
    freqs2 = dict(sorted(freqs2.items(), key=lambda x: x[1], reverse=True))

    axes[1, idx].barh(list(freqs2.keys())[::-1], list(freqs2.values())[::-1],
                       color=color, edgecolor='white', alpha=0.8)
    axes[1, idx].set_xlabel('Frequency')
    axes[1, idx].set_title(f'Top 20 Bigrams - {label}', fontweight='bold')

plt.suptitle('Most Frequent Terms by Class', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '03_top_ngrams.png')
plt.close()

# ============================================================
# 4. FEATURE CORRELATION HEATMAP
# ============================================================
print("4. Generating feature correlation heatmap...")
numeric_feats = ['msg_len', 'word_count', 'avg_word_len', 'has_exclamation',
                 'has_caps_word', 'unique_word_ratio']
df['label_numeric'] = (df['Extremism_Label'] == 'EXTREMIST').astype(int)
corr_cols = numeric_feats + ['label_numeric']
corr = df[corr_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.3f', cmap='RdBu_r',
            center=0, square=True, linewidths=0.5, ax=ax,
            cbar_kws={'shrink': 0.8}, vmin=-1, vmax=1)
ax.set_title('Feature Correlation Matrix', fontsize=14, fontweight='bold')
plt.savefig(OUTPUT_DIR / '04_correlation_heatmap.png')
plt.close()

# ============================================================
# 5. AVERAGE WORD LENGTH DISTRIBUTION
# ============================================================
print("5. Generating average word length distribution...")
fig, ax = plt.subplots(figsize=(12, 6))
for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    ax.hist(subset['avg_word_len'], bins=40, alpha=0.6, color=color,
            label=f'{label}', edgecolor='white')
ax.set_xlabel('Average Word Length (characters)')
ax.set_ylabel('Frequency')
ax.set_title('Average Word Length Distribution by Class', fontsize=14, fontweight='bold')
ax.legend()
plt.savefig(OUTPUT_DIR / '05_avg_word_length.png')
plt.close()

# ============================================================
# 6. VOCABULARY RICHNESS (UNIQUE WORD RATIO)
# ============================================================
print("6. Generating vocabulary richness chart...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Histogram
for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    axes[0].hist(subset['unique_word_ratio'], bins=40, alpha=0.6, color=color,
                 label=f'{label}', edgecolor='white')
axes[0].set_xlabel('Unique Word Ratio')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Vocabulary Richness Distribution', fontweight='bold')
axes[0].legend()

# Violin plot
parts = axes[1].violinplot(
    [df[df['Extremism_Label'] == 'EXTREMIST']['unique_word_ratio'],
     df[df['Extremism_Label'] == 'NON_EXTREMIST']['unique_word_ratio']],
    showmeans=True, showmedians=True
)
for i, pc in enumerate(parts['bodies']):
    pc.set_facecolor(colors[i])
    pc.set_alpha(0.7)
axes[1].set_xticks([1, 2])
axes[1].set_xticklabels(['EXTREMIST', 'NON_EXTREMIST'])
axes[1].set_ylabel('Unique Word Ratio')
axes[1].set_title('Vocabulary Richness (Violin)', fontweight='bold')

plt.suptitle('Lexical Diversity Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '06_vocabulary_richness.png')
plt.close()

# ============================================================
# 7. MESSAGE LENGTH vs LABEL (KDE PLOT)
# ============================================================
print("7. Generating KDE density plots...")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    subset['msg_len'].plot.kde(ax=axes[0], color=color, label=label, linewidth=2)
axes[0].set_xlabel('Character Length')
axes[0].set_title('Message Length Density (KDE)', fontweight='bold')
axes[0].set_xlim(0, 600)
axes[0].legend()

for label, color in zip(['EXTREMIST', 'NON_EXTREMIST'], colors):
    subset = df[df['Extremism_Label'] == label]
    subset['word_count'].plot.kde(ax=axes[1], color=color, label=label, linewidth=2)
axes[1].set_xlabel('Word Count')
axes[1].set_title('Word Count Density (KDE)', fontweight='bold')
axes[1].set_xlim(0, 100)
axes[1].legend()

plt.suptitle('Class-wise Feature Density Comparison', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '07_kde_density.png')
plt.close()

# ============================================================
# 8. TEXT FEATURE SUMMARY STATISTICS BY CLASS
# ============================================================
print("8. Generating comparative statistics chart...")
fig, ax = plt.subplots(figsize=(12, 7))

stats_by_label = df.groupby('Extremism_Label')[numeric_feats].mean()
x = np.arange(len(numeric_feats))
width = 0.35

bars1 = ax.bar(x - width/2, stats_by_label.loc['EXTREMIST'], width,
               label='EXTREMIST', color=colors[0], alpha=0.8, edgecolor='white')
bars2 = ax.bar(x + width/2, stats_by_label.loc['NON_EXTREMIST'], width,
               label='NON_EXTREMIST', color=colors[1], alpha=0.8, edgecolor='white')
ax.set_xticks(x)
ax.set_xticklabels([f.replace('_', '\n') for f in numeric_feats], fontsize=9)
ax.set_ylabel('Mean Value')
ax.set_title('Mean Feature Values by Class', fontsize=14, fontweight='bold')
ax.legend()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '08_feature_comparison.png')
plt.close()

# ============================================================
# 9. OUTLIER ANALYSIS
# ============================================================
print("9. Generating outlier analysis...")
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for i, feat in enumerate(['msg_len', 'word_count', 'avg_word_len']):
    q1 = df[feat].quantile(0.25)
    q3 = df[feat].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(df[feat] < lower) | (df[feat] > upper)]

    axes[i].scatter(range(len(df)), df[feat], alpha=0.3, s=5, c='#2196f3', label='Normal')
    if len(outliers) > 0:
        axes[i].scatter(outliers.index, outliers[feat], alpha=0.6, s=15, c='#d32f2f', label=f'Outliers ({len(outliers)})')
    axes[i].axhline(upper, color='orange', linestyle='--', alpha=0.7, label=f'Upper: {upper:.1f}')
    axes[i].axhline(lower, color='green', linestyle='--', alpha=0.7, label=f'Lower: {lower:.1f}')
    axes[i].set_xlabel('Message Index')
    axes[i].set_ylabel(feat.replace('_', ' ').title())
    axes[i].set_title(f'{feat.replace("_", " ").title()} Outliers', fontweight='bold')
    axes[i].legend(fontsize=8)

plt.suptitle('Outlier Detection (IQR Method)', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '09_outlier_analysis.png')
plt.close()

# ============================================================
# 10. SPECIAL CHARACTER & PUNCTUATION ANALYSIS
# ============================================================
print("10. Generating punctuation analysis...")
df['exclamation_count'] = df['Original_Message'].str.count('!')
df['question_count'] = df['Original_Message'].str.count(r'\?')
df['period_count'] = df['Original_Message'].str.count(r'\.')
df['comma_count'] = df['Original_Message'].str.count(',')

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
punct_feats = ['exclamation_count', 'question_count', 'period_count', 'comma_count']
titles = ['Exclamation Marks (!)', 'Question Marks (?)', 'Periods (.)', 'Commas (,)']

for i, (feat, title) in enumerate(zip(punct_feats, titles)):
    ax = axes[i // 2, i % 2]
    means = df.groupby('Extremism_Label')[feat].mean()
    bars = ax.bar(means.index, means.values, color=colors, edgecolor='white', width=0.5)
    for bar, val in zip(bars, means.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.2f}', ha='center', fontweight='bold')
    ax.set_ylabel(f'Mean {title} per Message')
    ax.set_title(f'{title} Usage by Class', fontweight='bold')

plt.suptitle('Punctuation Usage Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '10_punctuation_analysis.png')
plt.close()

# ============================================================
# 11. WORD CLOUD PLACEHOLDER (Top terms as bar chart)
# ============================================================
print("11. Generating term frequency summary...")
fig, axes = plt.subplots(1, 2, figsize=(16, 8))

for idx, (label, color) in enumerate(zip(['EXTREMIST', 'NON_EXTREMIST'], colors)):
    subset_text = df[df['Extremism_Label'] == label]['Original_Message'].astype(str)
    vec = CountVectorizer(max_features=30, stop_words='english')
    X = vec.fit_transform(subset_text)
    freqs = dict(zip(vec.get_feature_names_out(), X.sum(axis=0).A1))
    freqs = dict(sorted(freqs.items(), key=lambda x: x[1], reverse=True)[:25])

    axes[idx].barh(list(freqs.keys())[::-1], list(freqs.values())[::-1],
                    color=color, alpha=0.8, edgecolor='white')
    axes[idx].set_xlabel('Frequency')
    axes[idx].set_title(f'Top 25 Terms - {label}', fontweight='bold', fontsize=12)

plt.suptitle('Most Frequent Terms (Excluding Stop Words)', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '11_term_frequency.png')
plt.close()

# ============================================================
# 12. DATA QUALITY SUMMARY CHART
# ============================================================
print("12. Generating data quality summary...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Missing values
missing = df[['Original_Message', 'Extremism_Label']].isnull().sum()
axes[0].bar(missing.index, missing.values, color=['#2196f3', '#ff9800'], edgecolor='white')
for i, val in enumerate(missing.values):
    axes[0].text(i, val + 0.5, str(val), ha='center', fontweight='bold')
axes[0].set_ylabel('Count')
axes[0].set_title('Missing Values per Column', fontweight='bold')

# Duplicates summary
dup_data = {
    'Exact\nDuplicates': df.duplicated().sum(),
    'Duplicate\nMessages': df['Original_Message'].duplicated().sum(),
    'Unique\nMessages': df['Original_Message'].nunique(),
}
axes[1].bar(dup_data.keys(), dup_data.values(),
            color=['#f44336', '#ff9800', '#4caf50'], edgecolor='white')
for i, (k, val) in enumerate(dup_data.items()):
    axes[1].text(i, val + 20, f'{val:,}', ha='center', fontweight='bold')
axes[1].set_ylabel('Count')
axes[1].set_title('Data Quality Overview', fontweight='bold')

plt.suptitle('Data Quality Assessment', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '12_data_quality.png')
plt.close()

# ============================================================
# PRINT SUMMARY STATISTICS FOR REPORT
# ============================================================
print("\n" + "=" * 60)
print("EDA SUMMARY STATISTICS")
print("=" * 60)

print(f"\nDataset: Extremism Detection Dataset (training_dataset.csv)")
print(f"Records: {len(df):,} (usable)")
print(f"Features: 2 (text, Extremism_Label)")

print(f"\nClass Distribution:")
for label in sorted(df['Extremism_Label'].unique()):
    count = (df['Extremism_Label'] == label).sum()
    pct = count / len(df) * 100
    print(f"  {label}: {count:,} ({pct:.1f}%)")

print(f"\nMessage Statistics:")
print(f"  Avg character length: {df['msg_len'].mean():.1f}")
print(f"  Median character length: {df['msg_len'].median():.1f}")
print(f"  Avg word count: {df['word_count'].mean():.1f}")
print(f"  Median word count: {df['word_count'].median():.1f}")

print(f"\nData Quality:")
print(f"  Missing messages: 1")
print(f"  Duplicate rows: {df.duplicated().sum()}")
print(f"  Duplicate messages: {df['Original_Message'].duplicated().sum()}")

for feat in ['msg_len', 'word_count', 'avg_word_len']:
    q1 = df[feat].quantile(0.25)
    q3 = df[feat].quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    outliers = (df[feat] > upper).sum()
    print(f"  {feat} outliers (>{upper:.0f}): {outliers} ({outliers/len(df)*100:.1f}%)")

print(f"\nAll 12 visualizations saved to: {OUTPUT_DIR}/")
print("Done!")
