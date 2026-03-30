# Dataset Research & Selection Report

## 1. Datasets Identified and Evaluated

### Dataset 1: Extremism Text Classification Dataset
- **Source**: Kaggle -- extremism text classification corpus
- **Size**: 2,777 records x 2 features (~0.65 MB CSV)
- **Coverage**: Binary-labeled English text messages (EXTREMIST / NON_EXTREMIST)
- **Quality**: Good -- near-balanced classes (52.4% / 47.6%), only 1 missing value, 0 duplicate rows, clean UTF-8 encoding
- **License**: Open-access for academic/research use via Kaggle
- **Relevance**: ★★★★★ -- Directly aligned with text-based extremism detection and threat classification, which is the core objective of this project.

### Dataset 2: Hate Speech and Offensive Language Dataset (Davidson et al.)
- **Source**: GitHub / academic publication (Davidson et al., 2017)
- **Size**: ~25,000 tweets x 7 features
- **Coverage**: Three classes -- hate speech, offensive language, neither
- **Quality**: Good -- well-cited in NLP research; some labeling noise due to crowdsourced annotation
- **License**: Open for academic use
- **Relevance**: ★★★★☆ -- Focuses on hate speech rather than extremism directly. Useful for related NLP tasks but does not distinguish extremist ideology from general offensive content.

### Dataset 3: Radicalization and Extremism Online (REO) Corpus
- **Source**: Various academic compilations
- **Size**: Variable (typically 1,000-5,000 documents)
- **Coverage**: Forum posts, social media content from known extremist and non-extremist sources
- **Quality**: Variable -- depends on specific compilation; often manually curated by researchers
- **License**: Restricted -- many require institutional access or ethics board approval
- **Relevance**: ★★★★☆ -- Highly relevant domain-wise but access restrictions and inconsistent formatting limit practicality.

### Dataset 4: Global Terrorism Database (GTD)
- **Source**: START (University of Maryland) via Kaggle
- **Size**: 181,691 records x 135 features (155 MB CSV)
- **Coverage**: Terrorism incident records from 1970-2017 across 205 countries
- **Quality**: Very high -- curated by academic researchers; comprehensive documentation
- **License**: Open-access for academic use
- **Relevance**: ★★★☆☆ -- Structured incident data (not raw text). Excellent for event analysis but does not directly support text classification for extremism detection. Would require extensive preprocessing to create a text classification dataset.

### Dataset 5: Jigsaw Toxic Comment Classification Dataset
- **Source**: Kaggle (Google Jigsaw)
- **Size**: ~160,000 comments x 7 label columns
- **Coverage**: Wikipedia talk page comments labeled for toxic, severe_toxic, obscene, threat, insult, identity_hate
- **Quality**: High -- large scale, multi-label, well-documented
- **License**: Open via Kaggle competition
- **Relevance**: ★★★☆☆ -- Covers general online toxicity rather than specifically extremism. The "threat" label is loosely related but the domain context differs significantly from ideological extremism.

---

## 2. Dataset Evaluation Matrix

| Criterion         | Extremism Text | Davidson Hate Speech | REO Corpus | GTD  | Jigsaw Toxic |
|-------------------|----------------|---------------------|------------|------|--------------|
| **Size**          | ★★★            | ★★★★                | ★★★        | ★★★★★ | ★★★★★        |
| **Quality**       | ★★★★           | ★★★★                | ★★★        | ★★★★★ | ★★★★         |
| **Relevance**     | ★★★★★          | ★★★★                | ★★★★       | ★★★  | ★★★          |
| **Licensing**     | ★★★★★          | ★★★★                | ★★         | ★★★★ | ★★★★★        |
| **Text-Based**    | ★★★★★          | ★★★★★               | ★★★★★      | ★★   | ★★★★★        |
| **Binary Labels** | ★★★★★          | ★★★                 | ★★★★       | ★★   | ★★           |
| **TOTAL**         | **27**         | **23**              | **21**     | **21** | **23**       |

---

## 3. Final Selection: Extremism Text Classification Dataset

### Decision Rationale

The **Extremism Text Classification Dataset** (`extremisim.csv`) is selected as the primary dataset for this project based on the following justification:

1. **Direct Domain Alignment**: The dataset provides binary-labeled text messages for extremism detection, which is the exact task our system targets. Unlike incident databases (GTD) or general toxicity corpora (Jigsaw), this dataset directly addresses ideological extremism in text.

2. **Clean Binary Classification**: The two-class structure (EXTREMIST / NON_EXTREMIST) maps perfectly to our threat detection pipeline, where messages are classified as high-threat or low-threat. No complex multi-label preprocessing is required.

3. **Near-Balanced Classes**: With 52.4% NON_EXTREMIST and 47.6% EXTREMIST, the dataset does not suffer from severe class imbalance. This simplifies model training and evaluation, and avoids the need for heavy resampling techniques.

4. **Practical Size**: At 2,777 records, the dataset is large enough for meaningful TF-IDF + classifier training (demonstrated 82% baseline accuracy) while remaining computationally manageable for iterative experimentation.

5. **Data Quality**: Only 1 missing value out of 2,777 records (0.04%), zero duplicate rows, and clean UTF-8 encoding. Minimal preprocessing is needed before model training.

6. **Accessibility**: Freely available on Kaggle with no institutional access requirements, ethics board approvals, or redistribution restrictions.

7. **Text Mining Suitability**: Raw text messages are ideal for the NLP-based analysis pipeline that forms the core of our application (TF-IDF vectorization, keyword extraction, threat scoring).

### Limitations Acknowledged
- **Moderate size**: 2,777 records is smaller than some alternatives. May limit complex model architectures (e.g., deep learning).
- **Two features only**: No metadata (timestamps, source, author) limits analysis dimensions.
- **Static snapshot**: No temporal component -- cannot analyze trends over time.
- **English only**: Messages are in English, limiting applicability to multilingual contexts.
- **Label subjectivity**: Binary extremism labeling inherently involves subjective judgment; edge cases exist.

---

## 4. Project Scope, Objectives, and Success Criteria

### Project Scope
Build a web-based data mining system for extremism detection and threat monitoring that:
- Analyzes the extremism text dataset to extract patterns and threat indicators
- Provides document upload and automated text analysis for threat detection
- Offers real-time monitoring and alerting capabilities
- Visualizes threat data through an interactive dashboard

### Objectives
1. **Data Understanding**: Complete exploratory data analysis of the extremism dataset to establish baseline domain knowledge
2. **Pattern Detection**: Identify linguistic and statistical patterns that differentiate extremist from non-extremist text
3. **Threat Classification**: Build ML models to classify threat levels from text features
4. **Monitoring System**: Implement real-time content monitoring with automated threat scoring
5. **Visualization**: Create interactive dashboards for threat trend analysis and alert management

### Success Criteria
| Criteria | Target | Measurement |
|----------|--------|-------------|
| Dataset loaded and profiled | Complete | Both columns documented, quality assessed |
| EDA completed with visualizations | >= 12 charts | Covering distributions, correlations, text analysis, quality |
| Data quality issues documented | Complete | Missing values, outliers, and anomalies catalogued |
| Feature relationships analyzed | Complete | Correlation matrix and class-conditional distributions produced |
| Baseline domain insights documented | Complete | Written report with key findings and recommendations |
| Text analysis pipeline functional | Working | Can process uploaded documents and return threat scores |
| ML model baseline accuracy | >= 80% | Threat level classification accuracy on held-out test set |
| Dashboard displays real data | Functional | Charts and metrics rendered from extremism analysis |
