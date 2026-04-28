"""
Train and save a dedicated SGDClassifier pipeline for extremism threat detection.
Saves the model to data/models/sgd_threat_model.joblib.
"""

import os
import sys
import json
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_PATH = os.path.join(BACKEND_DIR, "data", "datasets", "extremisim.csv")
MODEL_DIR = os.path.join(BACKEND_DIR, "data", "models")
RANDOM_STATE = 42

os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    print(f"Loading dataset from {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, encoding="utf-8")
    df = df[df["Original_Message"].notna() & (df["Original_Message"].str.strip() != "")].copy()
    print(f"  {len(df)} rows loaded")

    text = df["Original_Message"].astype(str)
    labels = df["Extremism_Label"].map({"EXTREMIST": "high", "NON_EXTREMIST": "low"}).fillna("low")

    print(f"\nLabel distribution:")
    print(labels.value_counts().to_string())

    X_train, X_test, y_train, y_test = train_test_split(
        text, labels, test_size=0.2, random_state=RANDOM_STATE, stratify=labels
    )

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=30_000,
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
        )),
        ("clf", SGDClassifier(
            loss="modified_huber",
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])

    print("\nTraining SGDClassifier ...")
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_pred)
    test_f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"\nTest Set Evaluation:")
    print(classification_report(y_test, y_pred, target_names=sorted(labels.unique())))
    print(f"  Test Accuracy: {test_accuracy:.4f}")
    print(f"  Test F1 (wt):  {test_f1:.4f}")

    out_path = os.path.join(MODEL_DIR, "sgd_threat_model.joblib")
    joblib.dump(pipe, out_path)
    print(f"\nModel saved: {out_path}")

    summary = {
        "model": "SGDClassifier",
        "loss": "modified_huber",
        "test_accuracy": round(test_accuracy, 4),
        "test_f1_weighted": round(test_f1, 4),
        "classes": list(pipe.classes_),
    }
    summary_path = os.path.join(MODEL_DIR, "sgd_training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
