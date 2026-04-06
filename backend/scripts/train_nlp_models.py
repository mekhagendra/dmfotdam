"""
Train NLP-based models for extremism threat detection.

Adds transformer-based embeddings + classical classifiers as a middle ground
between pure TF-IDF and full BERT fine-tuning.

Models trained:
  1. Sentence-BERT embeddings + Logistic Regression
  2. Sentence-BERT embeddings + XGBoost (if available)
  3. spaCy text categorizer (CNN-based)

Requirements:
  pip install sentence-transformers spacy xgboost scikit-learn pandas matplotlib seaborn
  python -m spacy download en_core_web_sm

Usage:
  python scripts/train_nlp_models.py
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_PATH = os.path.join(BACKEND_DIR, "data", "datasets", "extremisim.csv")
MODEL_DIR = os.path.join(BACKEND_DIR, "data", "models")
OUTPUT_DIR = os.path.join(BACKEND_DIR, "data", "datasets", "eda_output")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42
LABEL_MAP = {"NON_EXTREMIST": "low", "EXTREMIST": "high"}


# ── data loading ─────────────────────────────────────────────────────
def load_data():
    print(f"Loading dataset from {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, encoding="utf-8")
    df = df[df["Original_Message"].notna() & (df["Original_Message"].str.strip() != "")].copy()
    print(f"  {len(df)} rows with non-empty text")

    texts = df["Original_Message"].astype(str).tolist()
    labels = df["Extremism_Label"].map(LABEL_MAP).tolist()
    print(f"  Label distribution: {pd.Series(labels).value_counts().to_dict()}")
    return texts, labels


# ═══════════════════════════════════════════════════════════════════════
#  Model 1 & 2: Sentence-BERT embeddings + classical classifiers
# ═══════════════════════════════════════════════════════════════════════
def train_sbert_models(texts_train, texts_test, y_train, y_test):
    """Encode texts with Sentence-BERT, then train LR + XGBoost."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [SKIP] sentence-transformers not installed. "
              "Install with: pip install sentence-transformers")
        return {}

    print("\n" + "=" * 70)
    print("SENTENCE-BERT EMBEDDING MODELS")
    print("=" * 70)

    # Use a lightweight sentence-transformer model
    sbert_model_name = "all-MiniLM-L6-v2"
    print(f"  Loading Sentence-BERT model: {sbert_model_name}")
    sbert = SentenceTransformer(sbert_model_name)

    print("  Encoding training texts ...")
    X_train = sbert.encode(texts_train, show_progress_bar=True, batch_size=32)
    print("  Encoding test texts ...")
    X_test = sbert.encode(texts_test, show_progress_bar=True, batch_size=32)

    results = {}

    # ── Logistic Regression on SBERT embeddings ──────────────────────
    print("\n--- SBERT + Logistic Regression ---")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)
    lr.fit(X_train, y_train)

    y_pred = lr.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_w = f1_score(y_test, y_pred, average="weighted")
    prec = precision_score(y_test, y_pred, average="weighted")
    rec = recall_score(y_test, y_pred, average="weighted")

    print(f"  Accuracy:  {acc:.4f}")
    print(f"  F1 (wt):   {f1_w:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['low', 'high'])}")

    results["SBERT + LogReg"] = {
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1_w, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
    }

    # Save SBERT+LR model
    import joblib
    sbert_lr_path = os.path.join(MODEL_DIR, "sbert_logreg_model.joblib")
    joblib.dump({"sbert_model": sbert_model_name, "classifier": lr}, sbert_lr_path)
    print(f"  Model saved: {sbert_lr_path}")

    # ── XGBoost on SBERT embeddings ──────────────────────────────────
    try:
        from xgboost import XGBClassifier

        print("\n--- SBERT + XGBoost ---")
        # Encode labels to integers for XGBoost
        label_enc = {"low": 0, "high": 1}
        y_train_int = [label_enc[l] for l in y_train]
        y_test_int = [label_enc[l] for l in y_test]

        xgb = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            use_label_encoder=False,
            eval_metric="logloss",
        )
        xgb.fit(X_train, y_train_int)

        y_pred_int = xgb.predict(X_test)
        y_pred_xgb = ["high" if p == 1 else "low" for p in y_pred_int]

        acc = accuracy_score(y_test, y_pred_xgb)
        f1_w = f1_score(y_test, y_pred_xgb, average="weighted")
        prec = precision_score(y_test, y_pred_xgb, average="weighted")
        rec = recall_score(y_test, y_pred_xgb, average="weighted")

        print(f"  Accuracy:  {acc:.4f}")
        print(f"  F1 (wt):   {f1_w:.4f}")
        print(f"  Precision: {prec:.4f}")
        print(f"  Recall:    {rec:.4f}")
        print(f"\n{classification_report(y_test, y_pred_xgb, target_names=['low', 'high'])}")

        results["SBERT + XGBoost"] = {
            "accuracy": round(acc, 4),
            "f1_weighted": round(f1_w, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
        }

        xgb_path = os.path.join(MODEL_DIR, "sbert_xgboost_model.joblib")
        joblib.dump({"sbert_model": sbert_model_name, "classifier": xgb, "label_enc": label_enc}, xgb_path)
        print(f"  Model saved: {xgb_path}")

    except ImportError:
        print("  [SKIP] xgboost not installed. Install with: pip install xgboost")

    return results


# ═══════════════════════════════════════════════════════════════════════
#  Model 3: spaCy Text Categorizer
# ═══════════════════════════════════════════════════════════════════════
def train_spacy_model(texts_train, texts_test, y_train, y_test, epochs=10):
    """Train a spaCy text categorizer (CNN-based)."""
    try:
        import spacy
        from spacy.training import Example
    except ImportError:
        print("  [SKIP] spaCy not installed. Install with: pip install spacy")
        return {}

    print("\n" + "=" * 70)
    print("SPACY TEXT CATEGORIZER (CNN)")
    print("=" * 70)

    nlp = spacy.blank("en")

    # Add text categorizer component
    textcat = nlp.add_pipe("textcat", last=True)
    textcat.add_label("EXTREMIST")
    textcat.add_label("NON_EXTREMIST")

    # Prepare training data
    train_examples = []
    for text, label in zip(texts_train, y_train):
        cats = {"EXTREMIST": 1.0 if label == "high" else 0.0,
                "NON_EXTREMIST": 1.0 if label == "low" else 0.0}
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, {"cats": cats})
        train_examples.append(example)

    # Train
    nlp.initialize(lambda: train_examples)
    optimizer = nlp.create_optimizer()

    for epoch in range(1, epochs + 1):
        losses = {}
        # Shuffle training data each epoch
        import random
        random.seed(RANDOM_STATE + epoch)
        random.shuffle(train_examples)

        batches = [train_examples[i:i + 8] for i in range(0, len(train_examples), 8)]
        for batch in batches:
            nlp.update(batch, sgd=optimizer, losses=losses)

        print(f"  Epoch {epoch}/{epochs} -- loss={losses.get('textcat', 0):.4f}")

    # Evaluate
    y_pred = []
    for text in texts_test:
        doc = nlp(text)
        pred = "high" if doc.cats["EXTREMIST"] > doc.cats["NON_EXTREMIST"] else "low"
        y_pred.append(pred)

    acc = accuracy_score(y_test, y_pred)
    f1_w = f1_score(y_test, y_pred, average="weighted")
    prec = precision_score(y_test, y_pred, average="weighted")
    rec = recall_score(y_test, y_pred, average="weighted")

    print(f"\n  Test Results:")
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    F1 (wt):   {f1_w:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['low', 'high'])}")

    # Save spaCy model
    spacy_path = os.path.join(MODEL_DIR, "spacy_textcat_model")
    nlp.to_disk(spacy_path)
    print(f"  Model saved: {spacy_path}")

    return {
        "spaCy TextCat (CNN)": {
            "accuracy": round(acc, 4),
            "f1_weighted": round(f1_w, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
        }
    }


# ── visualization ────────────────────────────────────────────────────
def plot_nlp_model_comparison(results: dict):
    if len(results) < 1:
        return

    names = list(results.keys())
    accuracy = [results[n]["accuracy"] for n in names]
    f1 = [results[n]["f1_weighted"] for n in names]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, accuracy, width, label="Accuracy")
    bars2 = ax.bar(x + width / 2, f1, width, label="F1 (weighted)")

    ax.set_ylabel("Score")
    ax.set_title("NLP Model Comparison -- Test Set")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, ha="right")
    ax.legend()
    ax.set_ylim(0.5, 1.0)
    ax.grid(axis="y", alpha=0.3)

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "20_nlp_model_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── main ─────────────────────────────────────────────────────────────
def main():
    texts, labels = load_data()

    texts_train, texts_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_STATE, stratify=labels,
    )
    print(f"  Train: {len(texts_train)}  Test: {len(texts_test)}")

    all_results = {}

    # ── Sentence-BERT models ─────────────────────────────────────────
    sbert_results = train_sbert_models(texts_train, texts_test, y_train, y_test)
    all_results.update(sbert_results)

    # ── spaCy model ──────────────────────────────────────────────────
    spacy_results = train_spacy_model(texts_train, texts_test, y_train, y_test, epochs=10)
    all_results.update(spacy_results)

    # ── Load existing TF-IDF results for comparison ──────────────────
    tfidf_summary_path = os.path.join(MODEL_DIR, "training_summary.json")
    if os.path.exists(tfidf_summary_path):
        with open(tfidf_summary_path) as f:
            tfidf_summary = json.load(f)
        all_results["TF-IDF + " + tfidf_summary["best_model"]] = {
            "accuracy": tfidf_summary["test_accuracy"],
            "f1_weighted": tfidf_summary["test_f1_weighted"],
            "precision": None,
            "recall": None,
        }

    # ── Comparison chart ─────────────────────────────────────────────
    plot_nlp_model_comparison(all_results)

    # ── Save summary ─────────────────────────────────────────────────
    summary = {
        "models_compared": list(all_results.keys()),
        "results": all_results,
        "dataset_size": len(texts),
        "train_size": len(texts_train),
        "test_size": len(texts_test),
    }
    summary_path = os.path.join(MODEL_DIR, "nlp_training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved: {summary_path}")

    # ── Print final comparison ───────────────────────────────────────
    print(f"\n{'='*70}")
    print("ALL NLP MODELS -- FINAL COMPARISON")
    print("=" * 70)
    for name, metrics in sorted(all_results.items(), key=lambda x: x[1].get("f1_weighted", 0), reverse=True):
        print(f"  {name:30s}  acc={metrics['accuracy']:.4f}  f1={metrics['f1_weighted']:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
