# Data Profiling & Exploratory Data Analysis Report

## Global Terrorism Database (GTD) — Comprehensive EDA

**Dataset**: `globalterrorismdb_0718dist.csv`
**Source**: START (University of Maryland) via Kaggle
**Analysis Date**: March 2026

---

## 1. Dataset Overview

| Metric | Value |
|--------|-------|
| Total Records | 181,691 |
| Total Features | 135 |
| Memory Usage | 629.8 MB |
| Time Span | 1970–2017 (47 years) |
| Countries Covered | 205 |
| Regions | 12 |
| Unique Terrorist Groups | 3,537 |
| File Format | CSV (Latin-1 encoding) |
| Duplicate Records | 0 |
| Duplicate Event IDs | 0 |

### Data Type Distribution
| Type | Count |
|------|-------|
| Object (string) | 58 |
| Float64 | 55 |
| Int64 | 22 |

---

## 2. Key Feature Categories

### 2.1 Temporal Features
- `iyear` (1970–2017): Year of incident — **no missing values**
- `imonth` (0–12): Month — 0 indicates unknown month
- `iday` (0–31): Day — 0 indicates unknown day
- `approxdate`: Free-text approximate date — 94.9% missing (used when exact date unknown)

### 2.2 Geographic Features
- `country_txt` / `country`: 205 unique countries — **no missing**
- `region_txt` / `region`: 12 world regions — **no missing**
- `provstate`: Province/state — 0.2% missing
- `city`: City name — 0.2% missing
- `latitude` / `longitude`: GPS coordinates — 2.5% missing

### 2.3 Attack Characteristics
- `attacktype1_txt`: 9 attack types — **no missing**
- `targtype1_txt`: 22 target types — **no missing**
- `weaptype1_txt`: 12 weapon types — **no missing**
- `success`: Binary (0/1) — **no missing**
- `suicide`: Binary (0/1) — **no missing**

### 2.4 Perpetrator Information
- `gname`: Group name — **no missing** (but 45.6% are "Unknown")
- `individual`: Whether lone actor (0/1) — **no missing**
- `nperps`: Number of perpetrators — 39.1% missing
- `claimed`: Whether attack was claimed — 36.4% missing

### 2.5 Casualty Data
- `nkill`: Number killed — 5.7% missing
- `nwound`: Number wounded — 9.0% missing
- `nkillter`: Perpetrators killed — 36.9% missing
- `nwoundte`: Perpetrators wounded — 38.1% missing

### 2.6 Text Fields
- `summary`: Narrative description — **36.4% missing** (available for 115,562 records)
- `motive`: Attack motive — **72.2% missing** (available for 50,561 records)

---

## 3. Statistical Summary of Key Numeric Features

### 3.1 Casualty Statistics

| Feature | Count | Mean | Median | Max | Total | Std Dev |
|---------|-------|------|--------|-----|-------|---------|
| nkill | 171,378 | 2.40 | 0.0 | 1,570 | 411,868 | 11.45 |
| nwound | 165,380 | 3.17 | 0.0 | 8,191 | 523,869 | 28.00 |
| nkillter | 114,733 | 0.51 | 0.0 | 500 | 58,291 | 4.33 |
| nwoundte | 112,548 | 0.11 | 0.0 | 200 | 12,061 | 1.34 |

**Key Insight**: Both killed and wounded distributions are extremely right-skewed. The median is 0 for all casualty fields — the majority of attacks result in no casualties. A small number of catastrophic events (outliers) drive the totals.

### 3.2 Temporal Distribution

| Metric | Value |
|--------|-------|
| Peak year | 2014 (16,903 attacks) |
| Lowest year | 1971 (471 attacks) |
| Year with missing data | 1993 (not collected) |
| Growth trend | Dramatic increase from 2004–2014, decline 2015–2017 |

---

## 4. Data Quality Assessment

### 4.1 Missing Values Analysis

**Columns with no missing values (29/135):**
Core identifiers and primary classifications are complete — `eventid`, `iyear`, `imonth`, `iday`, `country`, `country_txt`, `region`, `region_txt`, `attacktype1`, `attacktype1_txt`, `targtype1`, `targtype1_txt`, `gname`, `success`, `suicide`, etc.

**Columns with >90% missing (62/135):**
Mostly secondary/tertiary target, weapon, claim, and group fields (e.g., `attacktype3`, `targtype3`, `weaptype4`, `gname3`, `claimmode3`). These represent rare multi-target, multi-weapon, or multi-group events and are expected to be sparse.

**Columns with meaningful partial missingness (1%–90%):**

| Column | Missing % | Impact |
|--------|-----------|--------|
| summary | 36.4% | Limits NLP text analysis to 64% of records |
| motive | 72.2% | Heavy missingness; only useful for subset analysis |
| claimed | 36.4% | May affect attribution analysis |
| nperps | 39.1% | Limits perpetrator count analysis |
| nkill | 5.7% | Low impact; can impute or analyze complete cases |
| nwound | 9.0% | Moderate; same approach as nkill |
| latitude/longitude | 2.5% | Low impact on geographic analysis |

**Recommendation**: For primary analysis, focus on the 29 fully-populated core columns. For text mining, use the 115,562 records with summaries. Drop columns with >90% missing as they offer minimal analytical value.

### 4.2 Duplicate Analysis
- **Exact duplicates**: 0 — No data integrity issues
- **Duplicate event IDs**: 0 — Every incident has a unique identifier

### 4.3 Outlier Analysis

**Casualty Outliers (IQR Method):**
- nkill > 5 (upper fence): 16,242 records (9.5% of non-null)
- Most extreme: 1,570 killed in a single event (likely 9/11 WTC attack)
- Second most extreme: 8,191 wounded in a single event

**Recommendation**: Use capping (winsorization) or log transformation for casualty features in ML models. Do not remove outliers — they represent genuine high-impact events critical for threat detection.

### 4.4 Data Gaps
- **1993**: Entire year missing — GTD data was not collected that year. This creates a gap in temporal trend analysis.
- **Post-2017**: Dataset ends in 2017. No recent events available.

---

## 5. Exploratory Analysis Findings

### 5.1 Temporal Trends
*(See: 01_yearly_trend.png)*

- Terrorism incidents increased dramatically from ~1,000/year (early 2000s) to a peak of **16,903 in 2014**, largely driven by conflicts in Iraq, Syria, Afghanistan, and Nigeria.
- A decline is observed from 2015–2017, coinciding with the territorial losses of ISIL.
- The late 1970s–1980s saw a first wave of terrorism (Cold War era conflicts).
- 1993 is entirely missing from the dataset.

### 5.2 Geographic Distribution
*(See: 02_top_countries.png, 06_regional_analysis.png, 13_geographic_scatter.png)*

**Top 5 Countries:**
1. Iraq — 24,636 attacks (13.6%)
2. Pakistan — 14,368 (7.9%)
3. Afghanistan — 12,731 (7.0%)
4. India — 11,960 (6.6%)
5. Colombia — 8,306 (4.6%)

**Regional Breakdown:**
1. Middle East & North Africa — 50,474 (27.8%)
2. South Asia — 44,974 (24.7%)
3. South America — 18,978 (10.4%)
4. Sub-Saharan Africa — 17,550 (9.7%)
5. Western Europe — 16,639 (9.2%)

**Key Insight**: The Middle East & South Asia account for **52.5%** of all terrorism globally. Western Europe, despite prominent high-profile attacks, ranks 5th by volume.

### 5.3 Attack Types
*(See: 03_attack_types.png)*

| Attack Type | Count | % |
|-------------|-------|---|
| Bombing/Explosion | 88,255 | 48.6% |
| Armed Assault | 42,669 | 23.5% |
| Assassination | 19,312 | 10.6% |
| Hostage Taking (Kidnapping) | 11,158 | 6.1% |
| Facility/Infrastructure Attack | 10,356 | 5.7% |
| Unknown | 7,276 | 4.0% |
| Unarmed Assault | 1,015 | 0.6% |
| Hostage Taking (Barricade) | 991 | 0.5% |
| Hijacking | 659 | 0.4% |

**Key Insight**: Bombings dominate at nearly half of all attacks. Combined with Armed Assault, these two types account for **72.1%** of all terrorism.

### 5.4 Target Types
*(See: 04_target_types.png)*

Top 5 targets: Private Citizens (24.0%), Military (15.4%), Police (13.5%), Government (11.7%), Business (11.4%). Civilian targeting being the #1 category underscores the indiscriminate nature of terrorism.

### 5.5 Weapon Types
*(See: 05_weapon_types.png)*

Explosives (50.9%) and Firearms (32.2%) account for **83.1%** of all attacks. Chemical, biological, and radiological weapons are extremely rare (<0.2% combined).

### 5.6 Casualty Patterns
*(See: 07_casualty_analysis.png)*

- **Total killed**: 411,868 across all recorded incidents
- **Total wounded**: 523,869
- **Most lethal attack type**: Hostage Taking (Barricade) has the highest average fatalities (8.34/attack), followed by Armed Assault (3.74)
- Casualty trends mirror the overall attack trend — peaking around 2014
- The majority of attacks (median = 0 killed) are non-lethal

### 5.7 Terrorist Groups
*(See: 08_terror_groups.png)*

**Attribution Challenge**: 82,782 attacks (45.6%) have "Unknown" perpetrators.

**Top Known Groups by Attack Count:**
1. Taliban — 7,478
2. ISIL — 5,613
3. Shining Path — 4,555
4. FMLN — 3,351
5. Al-Shabaab — 3,288

**Most Lethal Groups (by total kills):** Taliban, ISIL, Boko Haram, Al-Shabaab, and Sri Lankan LTTE dominate.

### 5.8 Success Rate Analysis
*(See: 09_success_analysis.png)*

- Overall success rate: **89.0%** — most attempted attacks succeed
- Hostage/barricade situations have the lowest success rate (~66%)
- Bombing/Explosion has a very high success rate (~91%)
- Success rate has remained remarkably stable over time (80–95%)

### 5.9 Suicide Attacks
*(See: 10_suicide_analysis.png)*

- Total suicide attacks: 6,633 (3.7% of all attacks)
- Suicide attacks are **far more lethal**: average 10+ killed vs. 2.1 for non-suicide
- Dramatic increase post-2001, peaking around 2014-2016 (linked to ISIL operations)

### 5.10 Feature Correlations
*(See: 11_correlation_heatmap.png)*

Notable correlations:
- `nkill` ↔ `nwound`: 0.57 (moderate positive — deadly attacks tend to wound more)
- `suicide` ↔ `nkill`: 0.13 (weak but positive — suicide attacks are deadlier)
- `iyear` ↔ `claimed`: 0.26 (claims became more common in recent years)
- `suicide` ↔ `claimed`: 0.21 (suicide attacks are more often claimed)
- Most attack/target type codes show weak correlations, suggesting they are relatively independent features

### 5.11 Seasonal Patterns
*(See: 14_seasonal_patterns.png)*

- Attacks are relatively evenly distributed across months, with slight peaks in **March, May, and July**
- No strong day-of-month pattern, though the 1st and 15th of each month show slightly elevated counts
- No dramatic seasonal effect — terrorism is not strongly seasonal

---

## 6. Data Quality Recommendations

### For Machine Learning Pipeline
1. **Feature Selection**: Use the ~30 core columns with low/no missing values for primary modeling. Drop 62 columns with >90% missingness.
2. **Text Features**: Leverage `summary` (64% available) and `motive` (28% available) for NLP-based threat classification.
3. **Target Variable**: Use `success` (binary), `suicide` (binary), or binned `nkill` for classification tasks. Use `attacktype1_txt` or `weaptype1_txt` for multi-class classification.
4. **Imputation**: For `nkill`/`nwound` (5-9% missing), median imputation (0) is appropriate given the distribution.
5. **Encoding**: One-hot encode low-cardinality categoricals (attack type, weapon type). Use target encoding for high-cardinality features (country, group name).
6. **Scaling**: Apply log1p transformation to `nkill`, `nwound` due to extreme right skew.
7. **Temporal Split**: Use time-based train/test split (e.g., train on 1970–2014, test on 2015–2017) to avoid data leakage.

### For Text Mining
1. The `summary` field provides rich free-text narratives suitable for TF-IDF, word embeddings, or transformer-based analysis.
2. Combine `summary` + `motive` for maximum text coverage.
3. Use attack type and threat level as supervised labels for text classification models.

### For Monitoring System
1. The GTD's attack type and threat categorizations can inform the rule-based keyword detection already implemented in the `TextAnalyzer` service.
2. Extract common terrorism-related terminology from the `summary` field to enhance keyword dictionaries.
3. Use regional and temporal patterns to calibrate threat scoring weights.

---

## 7. Visualization Index

All visualizations are saved in `backend/data/datasets/eda_output/`:

| File | Description |
|------|-------------|
| `01_yearly_trend.png` | Global terrorism incidents over time (1970–2017) |
| `02_top_countries.png` | Top 15 countries by number of attacks |
| `03_attack_types.png` | Attack type distribution (pie + bar) |
| `04_target_types.png` | Top 15 target types |
| `05_weapon_types.png` | Weapon type distribution |
| `06_regional_analysis.png` | Regional counts + trend by top 5 regions |
| `07_casualty_analysis.png` | Casualty distributions, trends, and lethality by attack type |
| `08_terror_groups.png` | Top 15 groups by attacks and by lethality |
| `09_success_analysis.png` | Attack success rates by type and over time |
| `10_suicide_analysis.png` | Suicide attack trends and comparative lethality |
| `11_correlation_heatmap.png` | Correlation matrix of 15 key numeric features |
| `12_missing_values.png` | Missing value percentages for columns with 1–99% missing |
| `13_geographic_scatter.png` | Geographic scatter of attacks colored by year |
| `14_seasonal_patterns.png` | Monthly and day-of-month attack distributions |
| `15_feature_distributions.png` | Box plots and histograms for key features |

---

## 8. Domain Context: Cybersecurity & Terrorism Data Mining

The Global Terrorism Database provides a foundation for understanding terrorism through data mining by covering:

- **Pattern Recognition**: Temporal clustering (e.g., 2012–2014 surge) reveals conflict escalation windows
- **Geographic Hotspot Detection**: Concentrated activity in Middle East/South Asia enables region-specific models
- **Group Behavior Analysis**: Attack type preferences, target selection, and lethality profiles differ by group
- **Emerging Threat Indicators**: Rising suicide attack rates, expanding geographic spread, and new group emergence serve as early warning signals
- **Text Intelligence**: Summary narratives contain entity references, location mentions, and tactic descriptions amenable to NLP extraction

This baseline understanding directly informs the TDM system's threat detection algorithms, keyword dictionaries, and threat scoring calibration.
