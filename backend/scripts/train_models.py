"""
Train ML models for threat detection using the Global Terrorism Database.

Produces two models:
1. Threat Level Classifier  — predicts low / medium / high / critical
2. Attack Type Classifier   — predicts attack category

Both use TF-IDF vectorisation + SGDClassifier (linear SVM).
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_PATH = os.path.join(BACKEND_DIR, "data", "datasets", "gtd.csv")
MODEL_DIR = os.path.join(BACKEND_DIR, "data", "models")

os.makedirs(MODEL_DIR, exist_ok=True)


def load_data() -> pd.DataFrame:
    print(f"Loading dataset from {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, encoding="latin-1", low_memory=False)
    print(f"  Loaded {len(df)} rows")

    # Keep rows that have a summary (our text feature)
    df = df[df["summary"].notna() & (df["summary"].str.strip() != "")].copy()
    print(f"  {len(df)} rows with non-empty summary")
    return df


def derive_threat_level(df: pd.DataFrame) -> pd.Series:
    """Map total casualties → threat level label."""
    severity = df["nkill"].fillna(0) + df["nwound"].fillna(0)
    conditions = [
        severity == 0,
        severity <= 5,
        severity <= 20,
        severity > 20,
    ]
    labels = ["low", "medium", "high", "critical"]
    return pd.Series(np.select(conditions, labels, default="low"), index=df.index)


def simplify_attack_type(series: pd.Series) -> pd.Series:
    """Merge rare / overlapping attack types into broader categories."""
    mapping = {
        "Bombing/Explosion": "Bombing/Explosion",
        "Armed Assault": "Armed Assault",
        "Assassination": "Assassination",
        "Hostage Taking (Kidnapping)": "Hostage Taking",
        "Hostage Taking (Barricade Incident)": "Hostage Taking",
        "Facility/Infrastructure Attack": "Infrastructure Attack",
        "Unarmed Assault": "Unarmed Assault",
        "Hijacking": "Hijacking",
        "Unknown": "Unknown",
    }
    return series.map(mapping).fillna("Other")


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=30_000,
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
        )),
        ("clf", SGDClassifier(
            loss="modified_huber",   # gives probability estimates
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def train_and_save(X_text, y, model_name: str):
    print(f"\n{'='*60}")
    print(f"Training: {model_name}")
    print(f"  Classes: {sorted(y.unique())}")
    print(f"  Distribution:\n{y.value_counts().to_string()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=42, stratify=y,
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    print(f"\nTest set classification report:")
    print(classification_report(y_test, y_pred))

    accuracy = (y_pred == y_test).mean()
    print(f"  Accuracy: {accuracy:.4f}")

    out_path = os.path.join(MODEL_DIR, f"{model_name}.joblib")
    joblib.dump(pipe, out_path)
    print(f"  Model saved → {out_path}")

    return pipe, accuracy


def main():
    df = load_data()

    text = df["summary"].astype(str)

    # ── Model 1: Threat Level ─────────────────────────────────────────
    threat_labels = derive_threat_level(df)
    train_and_save(text, threat_labels, "threat_level_model")

    # ── Model 2: Attack Type ──────────────────────────────────────────
    attack_labels = simplify_attack_type(df["attacktype1_txt"])
    train_and_save(text, attack_labels, "attack_type_model")

    print("\n✅ All models trained and saved to:", MODEL_DIR)


if __name__ == "__main__":
    main()
