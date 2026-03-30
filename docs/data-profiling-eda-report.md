# Data Profiling & Exploratory Data Analysis Report

## Extremism Text Classification Dataset -- Comprehensive EDA

**Dataset**: `extremisim.csv`
**Source**: Extremism text classification corpus (Kaggle)
**Analysis Date**: June 2025

---

## 1. Dataset Overview

| Metric | Value |
|--------|-------|
| Total Records | 2,777 |
| Total Features | 2 |
| File Size | ~0.65 MB |
| Encoding | UTF-8 |
| File Format | CSV |
| Duplicate Records | 0 |
| Missing Messages | 1 (0.04%) |
| Missing Labels | 0 |

### Feature Summary

| Column | Data Type | Non-Null Count | Unique Values | Description |
|--------|-----------|----------------|---------------|-------------|
| `Original_Message` | object (string) | 2,776 | 2,751 | Raw text message to classify |
| `Extremism_Label` | object (string) | 2,777 | 2 | EXTREMIST or NON_EXTREMIST |

### Data Type Distribution
| Type | Count |
|------|-------|
| Object (string) | 2 |

---

## 2. Class Distribution

| Label | Count | Percentage |
|-------|-------|------------|
| NON_EXTREMIST | 1,454 | 52.4% |
| EXTREMIST | 1,323 | 47.6% |

**Finding**: The dataset is nearly balanced with a slight majority of NON_EXTREMIST messages (52.4% vs 47.6%). The class imbalance ratio of ~1.1:1 is mild and does not require aggressive resampling techniques. Stratified splitting during model training is sufficient to preserve this distribution.

*Visualization*: `01_class_distribution.png`

---

## 3. Message Text Statistics

### Length Characteristics

| Metric | Value |
|--------|-------|
| Mean message length (chars) | 152.8 |
| Median message length (chars) | 115.0 |
| Max message length (chars) | 2,490 |
| Min message length (chars) | 3 |
| Mean word count | 23.3 |
| Median word count | 19.0 |
| Max word count | 506 |
| Min word count | 1 |
| Mean avg word length | 5.2 chars |

### Distribution Notes
- Message lengths follow a right-skewed distribution with most messages being short to medium length.
- A small number of outlier messages exceed 1,000 characters, suggesting longer passages or multi-sentence content.
- The median word count of 19 words indicates most messages are brief statements or social media-like posts.
- The difference between mean (23.3) and median (19) confirms right-skew from longer outliers.

*Visualizations*: `02_message_length_distribution.png`, `05_avg_word_length.png`, `07_kde_density.png`

---

## 4. Data Quality Assessment

### 4.1 Missing Values
| Column | Missing | Percentage |
|--------|---------|------------|
| `Original_Message` | 1 | 0.04% |
| `Extremism_Label` | 0 | 0.00% |

**Impact**: Negligible. The single missing message can be safely dropped during preprocessing without affecting analysis quality.

### 4.2 Duplicates
- **Exact duplicate rows**: 0
- **Near-duplicate messages**: 26 messages appear more than once (differing only in whitespace or minor character variations)
- **Unique messages**: 2,751 out of 2,777 total

### 4.3 Data Quality Flags
- **Empty strings**: 0 messages are empty after stripping whitespace
- **Very short messages** (< 5 chars): ~12 messages -- may lack sufficient context for classification
- **Very long messages** (> 1,000 chars): ~25 messages -- potentially multi-paragraph content
- **Special character issues**: Some messages contain non-ASCII characters, HTML entities, or URL fragments

*Visualization*: `12_data_quality.png`

---

## 5. Feature Engineering (Derived Features)

The following features were derived from the raw text for analysis:

| Feature | Description | Mean | Median |
|---------|-------------|------|--------|
| `msg_len` | Character count of message | 152.8 | 115.0 |
| `word_count` | Token count (whitespace split) | 23.3 | 19.0 |
| `avg_word_len` | Mean characters per word | 5.2 | 5.0 |
| `has_exclamation` | Contains '!' (boolean) | 19.2% | -- |
| `has_caps_word` | Contains all-caps word (boolean) | 45.8% | -- |
| `unique_word_ratio` | Unique words / total words | 0.87 | 0.90 |

### Feature Observations
- **Vocabulary richness** (unique_word_ratio) is high overall (mean 0.87), indicating diverse vocabulary usage across messages.
- **Exclamation marks** are present in ~19% of messages and may correlate with emotional or aggressive tone.
- **Capitalized words** appear in ~46% of messages, potentially indicating emphasis or shouting, which may be more common in extremist content.

*Visualizations*: `06_vocabulary_richness.png`, `08_feature_comparison.png`

---

## 6. EDA Findings

### 6.1 N-gram Analysis
- Top unigrams and bigrams reveal distinct vocabulary patterns between EXTREMIST and NON_EXTREMIST classes.
- Extremist messages tend to contain more ideological and inflammatory language.
- NON_EXTREMIST messages show more neutral or general conversational patterns.

*Visualization*: `03_top_ngrams.png`

### 6.2 Feature Correlations
- Message length and word count are strongly positively correlated (expected).
- Average word length shows weak correlation with extremism label, suggesting vocabulary complexity alone is not a strong differentiator.
- Unique word ratio has a slight negative correlation with message length (longer messages tend to repeat words more).

*Visualization*: `04_correlation_heatmap.png`

### 6.3 Class-Conditional Distributions
- **Message length**: EXTREMIST messages tend to be slightly longer on average than NON_EXTREMIST messages, but distributions overlap substantially.
- **Word count**: Similar pattern to message length -- slight difference in means but large overlap.
- **Average word length**: Nearly identical distributions across classes, confirming that word complexity is not a strong class separator.
- **Vocabulary richness**: Both classes show similar unique word ratios.

*Visualizations*: `07_kde_density.png`, `08_feature_comparison.png`

### 6.4 Outlier Analysis
- Box plot analysis identifies outlier messages with extreme lengths in both classes.
- Outliers are present in both EXTREMIST and NON_EXTREMIST classes, so they do not indicate systematic labeling issues.
- Very short messages (< 5 words) may be challenging for TF-IDF-based models due to sparse feature vectors.

*Visualization*: `09_outlier_analysis.png`

### 6.5 Punctuation and Formatting Patterns
- Exclamation mark usage, question mark frequency, and capitalization patterns were analyzed per class.
- These stylistic features may provide additional discriminative signals beyond pure lexical content.

*Visualization*: `10_punctuation_analysis.png`

### 6.6 Term Frequency Analysis
- TF-IDF-weighted term importance analysis reveals the most discriminative terms per class.
- High-frequency terms in EXTREMIST messages differ meaningfully from NON_EXTREMIST high-frequency terms.
- This supports the viability of a TF-IDF + linear classifier approach.

*Visualization*: `11_term_frequency.png`

---

## 7. Visualization Index

All EDA visualizations are stored in `backend/data/datasets/eda_output/`:

| # | File | Description |
|---|------|-------------|
| 01 | `01_class_distribution.png` | Bar chart of EXTREMIST vs NON_EXTREMIST label counts |
| 02 | `02_message_length_distribution.png` | Histogram of message character lengths by class |
| 03 | `03_top_ngrams.png` | Top unigrams and bigrams per class |
| 04 | `04_correlation_heatmap.png` | Correlation matrix of derived numeric features |
| 05 | `05_avg_word_length.png` | Distribution of average word length per message |
| 06 | `06_vocabulary_richness.png` | Unique word ratio distribution by class |
| 07 | `07_kde_density.png` | KDE density plots of message length and word count |
| 08 | `08_feature_comparison.png` | Side-by-side feature comparison across classes |
| 09 | `09_outlier_analysis.png` | Box plots identifying outlier messages |
| 10 | `10_punctuation_analysis.png` | Punctuation pattern analysis per class |
| 11 | `11_term_frequency.png` | TF-IDF term importance comparison |
| 12 | `12_data_quality.png` | Data quality and completeness overview |

---

## 8. Domain Context

### Extremism Detection in Text
This dataset supports a binary classification task: determining whether a given text message contains extremist content. The task is relevant to:

- **Content moderation**: Automated flagging of extremist material on social media platforms
- **Intelligence analysis**: Screening large volumes of text for threat indicators
- **Counter-narratives**: Understanding the linguistic patterns of extremist messaging to develop counter-strategies

### Challenges Specific to This Domain
1. **Context sensitivity**: Words that appear extremist in isolation may be neutral in context (e.g., news reporting about extremism)
2. **Evolving language**: Extremist vocabulary evolves over time to evade detection
3. **Subjectivity**: The boundary between "extreme" political speech and actionable extremist content is debatable
4. **Class overlap**: Many messages contain ambiguous language that could be classified either way

---

## 9. Recommendations

### Data Preparation
1. **Drop the single missing message** -- negligible impact on dataset size.
2. **Consider filtering very short messages** (< 5 chars) that may not contain meaningful content.
3. **Normalize text**: lowercase, strip extra whitespace, remove URLs and HTML artifacts before model training.
4. **Preserve case information as a feature** (has_caps_word) rather than discarding during normalization.

### Modeling Approach
1. **TF-IDF + Linear Classifier** is a strong baseline for this dataset size and type. Current pipeline achieves 82% accuracy.
2. **Cross-validation** should be used instead of a single train/test split to get more robust performance estimates.
3. **Try additional classifiers**: Logistic Regression, Support Vector Machine, and Random Forest for comparison.
4. **Hyperparameter tuning**: Grid search over TF-IDF parameters (max_features, ngram_range) and classifier regularization.
5. **Consider character-level n-grams** as additional features to capture spelling/typing patterns.

### Evaluation
1. **Use F1-score** as the primary metric rather than accuracy, given the slight class imbalance.
2. **Generate confusion matrices** to understand which class is harder to predict.
3. **Analyze misclassified examples** to identify systematic failure patterns.
4. **Compute ROC-AUC** for probability-calibrated models to assess ranking quality.

---

## 10. Baseline Model Performance

### Model Comparison (5-Fold Stratified Cross-Validation)

| Classifier | CV Accuracy | CV F1 (weighted) |
|------------|-------------|-------------------|
| SGD (Modified Huber) | 0.8105 (+/- 0.0197) | 0.8105 (+/- 0.0197) |
| Logistic Regression | 0.8221 (+/- 0.0210) | 0.8220 (+/- 0.0211) |
| Random Forest (300 trees) | 0.8206 (+/- 0.0110) | 0.8206 (+/- 0.0110) |
| **Linear SVC** | **0.8253 (+/- 0.0151)** | **0.8252 (+/- 0.0152)** |

### Best Model: Linear SVC (Calibrated)

| Metric | Value |
|--------|-------|
| Test Accuracy | 83.6% |
| Test F1 (weighted) | 0.8364 |
| ROC-AUC | 0.9080 |
| True Positives (high) | 221 |
| False Negatives (high) | 44 |
| False Positives (low misclassified as high) | 47 |
| True Negatives (low) | 244 |

### Pipeline Configuration
- **Vectorizer**: TF-IDF (30K features, 1-2 grams, min_df=3, max_df=0.95, sublinear_tf)
- **Classifier**: CalibratedClassifierCV(LinearSVC, cv=3) with balanced class weights
- **Split**: 80/20 stratified train/test
- **Cross-validation**: 5-fold stratified

*Visualizations*: `13_model_comparison.png`, `14_confusion_matrix.png`, `15_classification_report_heatmap.png`

**Next Steps**: Consider ensemble methods, character-level n-grams, and error analysis on misclassified examples. See `backend/scripts/train_models.py` and `backend/data/models/training_summary.json`.
