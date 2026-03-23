# Dataset Research & Selection Report

## 1. Datasets Identified and Evaluated

### Dataset 1: Global Terrorism Database (GTD)
- **Source**: START (National Consortium for the Study of Terrorism and Responses to Terrorism), University of Maryland — available on Kaggle (`START-UMD/gtd`)
- **Size**: 181,691 records × 135 features (155 MB CSV)
- **Coverage**: 1970–2017, 205 countries, 3,537 terrorist groups
- **Quality**: High — curated by academic researchers; no duplicate records; 29 columns with zero missing values; well-documented codebook
- **License**: Open-access for academic/research use under START's terms of use
- **Relevance**: ★★★★★ — The most comprehensive open-source terrorism incident database worldwide. Directly aligned with our project's terrorism detection and monitoring objectives.

### Dataset 2: RAND Database of Worldwide Terrorism Incidents (RDWTI)
- **Source**: RAND Corporation
- **Size**: ~40,000 records (1968–2009)
- **Coverage**: Global incidents, fewer features than GTD
- **Quality**: Good — well-curated but discontinued after 2009
- **License**: Publicly available but with restrictions on redistribution
- **Relevance**: ★★★☆☆ — Useful but smaller, older, and no longer maintained. Fewer features limit analysis depth.

### Dataset 3: Armed Conflict Location & Event Data (ACLED)
- **Source**: ACLED Project (acleddata.com)
- **Size**: ~1.2 million events (1997–present)
- **Coverage**: Global political violence and protests
- **Quality**: Very high — continuously updated, rigorously coded
- **License**: Requires registration; free for academic use; usage terms restrict commercial distribution
- **Relevance**: ★★★★☆ — Broader than terrorism (includes riots, protests, battles). Very comprehensive but scope extends beyond pure terrorism.

### Dataset 4: Kaggle Terrorism & Radicalization Dataset
- **Source**: Various Kaggle contributors (e.g., `muhammetvarl/global-terrorism`)
- **Size**: Varies — typically derived from GTD with subsets or enrichments
- **Coverage**: Usually GTD-derivative with additional cleaning
- **Quality**: Variable — depends on contributor; often pre-cleaned
- **License**: Typically CC-BY or public domain
- **Relevance**: ★★★☆☆ — Useful for quick prototyping but derivative; better to use the primary source.

### Dataset 5: NSL-KDD / CIC-IDS Cyber Intrusion Detection Datasets
- **Source**: University of New Brunswick (UNB)
- **Size**: NSL-KDD: ~150K records; CICIDS2017: ~2.8M records
- **Coverage**: Network traffic data with attack labels
- **Quality**: High — standard benchmark in cybersecurity ML research
- **License**: Open for academic use
- **Relevance**: ★★☆☆☆ — Focused on network intrusion detection, not terrorism event analysis. Relevant if expanding to cyber-terrorism but not a primary fit for text/document mining.

---

## 2. Dataset Evaluation Matrix

| Criterion         | GTD  | RDWTI | ACLED | Kaggle Derivatives | NSL-KDD |
|-------------------|------|-------|-------|-------------------|---------|
| **Size**          | ★★★★★ | ★★★   | ★★★★★  | ★★★               | ★★★★    |
| **Quality**       | ★★★★★ | ★★★★  | ★★★★★  | ★★★               | ★★★★    |
| **Relevance**     | ★★★★★ | ★★★   | ★★★★   | ★★★               | ★★      |
| **Licensing**     | ★★★★  | ★★★   | ★★★    | ★★★★★              | ★★★★    |
| **Recency**       | ★★★★  | ★★    | ★★★★★  | ★★★               | ★★★     |
| **Documentation** | ★★★★★ | ★★★   | ★★★★   | ★★                | ★★★★    |
| **TOTAL**         | **29** | **18** | **26** | **18**            | **21**  |

---

## 3. Final Selection: Global Terrorism Database (GTD)

### Decision Rationale

The **Global Terrorism Database (GTD)** is selected as the primary dataset for this project based on the following justification:

1. **Direct Domain Alignment**: GTD is the world's most comprehensive open-access database on terrorist events, directly matching our project's core objective of terrorism detection and monitoring.

2. **Scale and Richness**: With 181,691 incidents across 135 features spanning 47 years (1970–2017), it provides sufficient volume for meaningful statistical analysis and machine learning model training.

3. **Feature Diversity**: The dataset includes temporal data (year, month, day), geographic data (country, region, lat/long), categorical data (attack type, target type, weapon type, group name), text data (summaries, motives), and numeric data (casualties, perpetrators).

4. **Academic Credibility**: Maintained by START at the University of Maryland — a DHS Center of Excellence — it is the gold standard in terrorism research and is cited in thousands of peer-reviewed publications.

5. **Text Mining Potential**: The `summary` and `motive` free-text fields (available for 63.6% and 27.8% of records respectively) enable NLP-based analysis that aligns with our document analysis pipeline.

6. **Ground Truth Labels**: Built-in classification fields (`attacktype1_txt`, `targtype1_txt`, `weaptype1_txt`, `success`, `suicide`) provide supervised learning labels without requiring manual annotation.

### Limitations Acknowledged
- Data stops at 2017 (no recent events)
- 1993 data is entirely missing (not collected that year)
- 45.6% of perpetrators are "Unknown" — limits group attribution analysis
- 62 of 135 columns have >90% missing values (secondary/tertiary targets, weapons, claims)

---

## 4. Project Scope, Objectives, and Success Criteria

### Project Scope
Build a web-based data mining system for terrorism detection and monitoring that:
- Analyzes the Global Terrorism Database to extract patterns, trends, and threat indicators
- Provides document upload and automated text analysis for threat detection
- Offers real-time monitoring and alerting capabilities
- Visualizes terrorism data through an interactive dashboard

### Objectives
1. **Data Understanding**: Complete exploratory data analysis of the GTD to establish baseline domain knowledge
2. **Pattern Detection**: Identify temporal, geographic, and categorical patterns in terrorism data
3. **Threat Classification**: Build ML models to classify threat levels from text and categorical features
4. **Monitoring System**: Implement real-time content monitoring with automated threat scoring
5. **Visualization**: Create interactive dashboards for terrorism trend analysis and alert management

### Success Criteria
| Criteria | Target | Measurement |
|----------|--------|-------------|
| Dataset loaded and profiled | Complete | All 135 columns documented, quality assessed |
| EDA completed with visualizations | ≥12 charts | Covering temporal, geographic, categorical, and correlation analysis |
| Data quality issues documented | Complete | Missing values, outliers, and anomalies catalogued |
| Feature relationships analyzed | Complete | Correlation matrix and cross-tabulations produced |
| Baseline domain insights documented | Complete | Written report with key findings and recommendations |
| Text analysis pipeline functional | Working | Can process uploaded documents and return threat scores |
| Dashboard displays real data | Functional | Charts and metrics rendered from GTD analysis |
