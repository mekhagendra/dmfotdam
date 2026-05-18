"""
Train ML models for extremism threat detection using the extremism dataset.

Workflow:
  1. Compare multiple classifiers via 5-fold stratified cross-validation
  2. Select the best model based on weighted F1-score
  3. Train final model on full training set and evaluate on held-out test set
  4. Generate confusion matrix and classification report
  5. Save the best model as threat_level_model.joblib

Classifiers compared:
  - SGDClassifier (linear SVM with modified Huber loss)
  - Logistic Regression (L2 regularized)
  - Random Forest (300 trees)
  - Support Vector Machine (linear kernel)
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    accuracy_score,
    roc_auc_score,
)

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(BACKEND_DIR, "data", "models")
OUTPUT_DIR = os.path.join(BACKEND_DIR, "data", "datasets", "eda_output")


def resolve_dataset_path() -> str:
    preferred = os.path.join(BACKEND_DIR, "data", "datasets", "training_dataset.csv")
    legacy = os.path.join(BACKEND_DIR, "data", "datasets", "extremisim.csv")
    if os.path.exists(preferred):
        return preferred
    if os.path.exists(legacy):
        return legacy
    raise FileNotFoundError(
        f"Dataset not found. Checked: {preferred} and {legacy}"
    )


DATASET_PATH = resolve_dataset_path()

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42


# ── data loading ─────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    print(f"Loading dataset from {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, encoding="utf-8")
    print(f"  Loaded {len(df)} rows")
    # normalise column names for new dataset schema (text/category)
    if "text" in df.columns and "Original_Message" not in df.columns:
        df = df.rename(columns={"text": "Original_Message"})
    if "category" in df.columns and "Extremism_Label" not in df.columns:
        df["Extremism_Label"] = df["category"].map(
            {"Extremist": "EXTREMIST", "NonExtremist": "NON_EXTREMIST"}
        ).fillna("NON_EXTREMIST")
    df = df[df["Original_Message"].notna() & (df["Original_Message"].str.strip() != "")].copy()
    print(f"  {len(df)} rows with non-empty Original_Message")
    return df


def derive_threat_level(df: pd.DataFrame) -> pd.Series:
    return df["Extremism_Label"].map({
        "EXTREMIST": "high",
        "NON_EXTREMIST": "low",
    }).fillna("low")


# ── TF-IDF vectorizer (shared across all pipelines) ─────────────────
def make_tfidf() -> TfidfVectorizer:
    return TfidfVectorizer(
        max_features=30_000,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.95,
        sublinear_tf=True,
        strip_accents="unicode",
    )


# ── candidate classifiers ───────────────────────────────────────────
def get_classifiers() -> dict:
    return {
        "SGD (Modified Huber)": SGDClassifier(
            loss="modified_huber",
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Linear SVC": CalibratedClassifierCV(
            LinearSVC(
                max_iter=2000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
            cv=3,
        ),
    }


# ── cross-validation comparison ─────────────────────────────────────
def compare_classifiers(X_text, y):
    print("\n" + "=" * 70)
    print("CLASSIFIER COMPARISON (5-fold Stratified Cross-Validation)")
    print("=" * 70)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    classifiers = get_classifiers()
    results = {}

    for name, clf in classifiers.items():
        print(f"\n--- {name} ---")
        pipe = Pipeline([("tfidf", make_tfidf()), ("clf", clf)])

        scores = cross_validate(
            pipe, X_text, y, cv=cv,
            scoring=["accuracy", "f1_weighted", "precision_weighted", "recall_weighted"],
            return_train_score=False,
            n_jobs=1,
        )

        result = {
            "accuracy_mean": scores["test_accuracy"].mean(),
            "accuracy_std": scores["test_accuracy"].std(),
            "f1_mean": scores["test_f1_weighted"].mean(),
            "f1_std": scores["test_f1_weighted"].std(),
            "precision_mean": scores["test_precision_weighted"].mean(),
            "recall_mean": scores["test_recall_weighted"].mean(),
        }
        results[name] = result

        print(f"  Accuracy:  {result['accuracy_mean']:.4f} (+/- {result['accuracy_std']:.4f})")
        print(f"  F1 (wt):   {result['f1_mean']:.4f} (+/- {result['f1_std']:.4f})")
        print(f"  Precision: {result['precision_mean']:.4f}")
        print(f"  Recall:    {result['recall_mean']:.4f}")

    return results


# ── visualization helpers ────────────────────────────────────────────
def plot_model_comparison(results: dict):
    names = list(results.keys())
    accuracy = [results[n]["accuracy_mean"] for n in names]
    f1 = [results[n]["f1_mean"] for n in names]
    acc_std = [results[n]["accuracy_std"] for n in names]
    f1_std = [results[n]["f1_std"] for n in names]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, accuracy, width, yerr=acc_std, label="Accuracy", capsize=4)
    bars2 = ax.bar(x + width / 2, f1, width, yerr=f1_std, label="F1 (weighted)", capsize=4)

    ax.set_ylabel("Score")
    ax.set_title("Model Comparison -- 5-Fold Cross-Validation")
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
    path = os.path.join(OUTPUT_DIR, "13_model_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_confusion_matrix(y_true, y_pred, labels, title="Confusion Matrix"):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    ax.set_title(title)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "14_confusion_matrix.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_classification_report_heatmap(y_true, y_pred, labels):
    report = classification_report(y_true, y_pred, target_names=labels, output_dict=True)
    report_df = pd.DataFrame(report).T
    # Keep only class rows and averages
    keep_rows = list(labels) + ["macro avg", "weighted avg"]
    report_df = report_df.loc[[r for r in keep_rows if r in report_df.index]]
    metrics = ["precision", "recall", "f1-score"]
    report_df = report_df[metrics]

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(report_df.astype(float), annot=True, fmt=".3f", cmap="YlGn",
                vmin=0.5, vmax=1.0, ax=ax, linewidths=0.5)
    ax.set_title("Classification Report Heatmap -- Best Model")
    ax.set_ylabel("")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "15_classification_report_heatmap.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── main training workflow ───────────────────────────────────────────
def main():
    df = load_data()
    text = df["Original_Message"].astype(str)
    threat_labels = derive_threat_level(df)

    print(f"\nLabel distribution:")
    print(threat_labels.value_counts().to_string())

    # ── Step 1: Compare classifiers with cross-validation ──────────
    results = compare_classifiers(text, threat_labels)
    plot_model_comparison(results)

    # ── Step 2: Select the best model by F1-score ──────────────────
    best_name = max(results, key=lambda n: results[n]["f1_mean"])
    print(f"\n{'='*70}")
    print(f"BEST MODEL: {best_name}")
    print(f"  CV F1 (weighted): {results[best_name]['f1_mean']:.4f}")
    print(f"  CV Accuracy:      {results[best_name]['accuracy_mean']:.4f}")
    print("=" * 70)

    # ── Step 3: Train final model on train split, evaluate on test ─
    X_train, X_test, y_train, y_test = train_test_split(
        text, threat_labels, test_size=0.2, random_state=RANDOM_STATE, stratify=threat_labels,
    )

    classifiers = get_classifiers()
    best_clf = classifiers[best_name]
    final_pipe = Pipeline([("tfidf", make_tfidf()), ("clf", best_clf)])
    final_pipe.fit(X_train, y_train)

    y_pred = final_pipe.predict(X_test)
    labels = sorted(threat_labels.unique())

    print(f"\nFinal Model Test Set Evaluation:")
    print(classification_report(y_test, y_pred, target_names=labels))

    test_accuracy = accuracy_score(y_test, y_pred)
    test_f1 = f1_score(y_test, y_pred, average="weighted")
    print(f"  Test Accuracy: {test_accuracy:.4f}")
    print(f"  Test F1 (wt):  {test_f1:.4f}")

    # ROC-AUC if model supports predict_proba
    try:
        y_proba = final_pipe.predict_proba(X_test)
        if y_proba.shape[1] == 2:
            # Use probability of "high" class
            high_idx = list(final_pipe.classes_).index("high")
            roc_auc = roc_auc_score((y_test == "high").astype(int), y_proba[:, high_idx])
            print(f"  ROC-AUC:       {roc_auc:.4f}")
    except Exception:
        print("  ROC-AUC: N/A (model does not support predict_proba)")

    # ── Step 4: Generate visualizations ────────────────────────────
    plot_confusion_matrix(y_test, y_pred, labels, title=f"Confusion Matrix -- {best_name}")
    plot_classification_report_heatmap(y_test, y_pred, labels)

    # ── Step 5: Save ALL individual models ─────────────────────────
    MODEL_FILE_MAP = {
        "SGD (Modified Huber)": "sgd_threat_model.joblib",
        "Logistic Regression": "logreg_threat_model.joblib",
        "Random Forest": "rf_threat_model.joblib",
        "Linear SVC": "linsvc_threat_model.joblib",
    }

    all_model_summaries = {}
    for clf_name, clf in classifiers.items():
        clf_pipe = Pipeline([("tfidf", make_tfidf()), ("clf", clf)])
        clf_pipe.fit(X_train, y_train)
        clf_pred = clf_pipe.predict(X_test)
        clf_f1 = f1_score(y_test, clf_pred, average="weighted")
        clf_acc = accuracy_score(y_test, clf_pred)
        file_name = MODEL_FILE_MAP.get(clf_name, clf_name.lower().replace(" ", "_") + "_threat_model.joblib")
        save_path = os.path.join(MODEL_DIR, file_name)
        joblib.dump(clf_pipe, save_path)
        all_model_summaries[clf_name] = {
            "file": file_name,
            "test_f1_weighted": round(clf_f1, 4),
            "test_accuracy": round(clf_acc, 4),
            "cv_f1_mean": round(results[clf_name]["f1_mean"], 4),
        }
        print(f"  Saved {clf_name} → {save_path}  (F1={clf_f1:.4f})")

    # Also save best model as the generic threat_level_model.joblib
    out_path = os.path.join(MODEL_DIR, "threat_level_model.joblib")
    joblib.dump(final_pipe, out_path)
    print(f"\nBest model ({best_name}) also saved as: {out_path}")

    # ── Step 6: Save comparison summary as JSON ────────────────────
    summary = {
        "best_model": best_name,
        "cv_results": {
            name: {k: round(v, 4) for k, v in res.items()}
            for name, res in results.items()
        },
        "all_models": all_model_summaries,
        "test_accuracy": round(test_accuracy, 4),
        "test_f1_weighted": round(test_f1, 4),
        "trained_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    summary_path = os.path.join(MODEL_DIR, "training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved: {summary_path}")

    print(f"\nDone. All models saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
