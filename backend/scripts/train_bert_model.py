"""
Fine-tune BERT / DistilBERT models for extremism threat detection.

Workflow:
  1. Load the extremism dataset (Original_Message, Extremism_Label)
  2. Encode labels as integers (EXTREMIST → 1, NON_EXTREMIST → 0)
  3. Fine-tune DistilBERT and (optionally) BERT-base on the training split
  4. Evaluate on held-out test set: accuracy, F1, precision, recall, ROC-AUC
  5. Generate confusion matrix and classification-report heatmap
  6. Save the best BERT model + tokenizer to data/models/bert_threat_model/

Requirements:
  pip install transformers torch datasets accelerate scikit-learn pandas matplotlib seaborn

Usage:
  python scripts/train_bert_model.py
  python scripts/train_bert_model.py --epochs 5 --batch-size 16 --model bert-base-uncased
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
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
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(BACKEND_DIR, "data", "models")
BERT_MODEL_DIR = os.path.join(MODEL_DIR, "bert_threat_model")
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

os.makedirs(BERT_MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42
LABEL_MAP = {"NON_EXTREMIST": 0, "EXTREMIST": 1}
LABEL_NAMES = ["low", "high"]  # matches existing threat-level scheme


# ── dataset class ────────────────────────────────────────────────────
class ExtremismDataset(Dataset):
    """PyTorch dataset for tokenised text + labels."""

    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": self.labels[idx],
        }


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


# ── training loop ────────────────────────────────────────────────────
def train_one_epoch(model, dataloader, optimizer, scheduler, device):
    model.train()
    total_loss = 0
    for batch in dataloader:
        optimizer.zero_grad()
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        total_loss += loss.item()

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

    return total_loss / len(dataloader)


# ── evaluation ───────────────────────────────────────────────────────
@torch.no_grad()
def evaluate(model, dataloader, device):
    model.eval()
    all_preds, all_labels, all_probs = [], [], []

    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)

        all_preds.extend(logits.argmax(dim=-1).cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        all_probs.extend(probs.cpu().numpy())

    return np.array(all_preds), np.array(all_labels), np.array(all_probs)


# ── visualization ────────────────────────────────────────────────────
def plot_training_loss(losses, model_name):
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(losses) + 1), losses, marker="o", linewidth=2)
    plt.xlabel("Epoch")
    plt.ylabel("Training Loss")
    plt.title(f"Training Loss -- {model_name}")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "16_bert_training_loss.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_confusion(y_true, y_pred, model_name):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABEL_NAMES)
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    ax.set_title(f"Confusion Matrix -- {model_name}")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "17_bert_confusion_matrix.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_classification_heatmap(y_true, y_pred, model_name):
    report = classification_report(y_true, y_pred, target_names=LABEL_NAMES, output_dict=True)
    report_df = pd.DataFrame(report).T
    keep = LABEL_NAMES + ["macro avg", "weighted avg"]
    report_df = report_df.loc[[r for r in keep if r in report_df.index]][
        ["precision", "recall", "f1-score"]
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(report_df.astype(float), annot=True, fmt=".3f", cmap="YlGn",
                vmin=0.5, vmax=1.0, ax=ax, linewidths=0.5)
    ax.set_title(f"Classification Report -- {model_name}")
    ax.set_ylabel("")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "18_bert_classification_heatmap.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_model_comparison(results: dict):
    """Bar chart comparing BERT variants (similar to traditional models chart)."""
    names = list(results.keys())
    accuracy = [results[n]["accuracy"] for n in names]
    f1 = [results[n]["f1_weighted"] for n in names]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, accuracy, width, label="Accuracy")
    bars2 = ax.bar(x + width / 2, f1, width, label="F1 (weighted)")

    ax.set_ylabel("Score")
    ax.set_title("BERT Model Comparison -- Test Set")
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
    path = os.path.join(OUTPUT_DIR, "19_bert_model_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── main training pipeline ───────────────────────────────────────────
def train_and_evaluate(model_name, texts_train, texts_test, y_train, y_test,
                       epochs, batch_size, lr, max_length, device):
    """Fine-tune one BERT variant and return test metrics."""
    print(f"\n{'='*70}")
    print(f"TRAINING: {model_name}")
    print(f"  epochs={epochs}  batch_size={batch_size}  lr={lr}  max_len={max_length}")
    print(f"  device={device}")
    print("=" * 70)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2
    ).to(device)

    train_ds = ExtremismDataset(texts_train, y_train, tokenizer, max_length)
    test_ds = ExtremismDataset(texts_test, y_test, tokenizer, max_length)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps,
    )

    epoch_losses = []
    for epoch in range(1, epochs + 1):
        loss = train_one_epoch(model, train_loader, optimizer, scheduler, device)
        epoch_losses.append(loss)

        # Quick validation each epoch
        preds, labels, probs = evaluate(model, test_loader, device)
        acc = accuracy_score(labels, preds)
        f1 = f1_score(labels, preds, average="weighted")
        print(f"  Epoch {epoch}/{epochs} -- loss={loss:.4f}  val_acc={acc:.4f}  val_f1={f1:.4f}")

    # ── final evaluation ─────────────────────────────────────────────
    preds, labels, probs = evaluate(model, test_loader, device)

    acc = accuracy_score(labels, preds)
    f1_w = f1_score(labels, preds, average="weighted")
    prec = precision_score(labels, preds, average="weighted")
    rec = recall_score(labels, preds, average="weighted")

    try:
        roc_auc = roc_auc_score(labels, probs[:, 1])
    except Exception:
        roc_auc = None

    print(f"\n  Final Test Results ({model_name}):")
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    F1 (wt):   {f1_w:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    if roc_auc is not None:
        print(f"    ROC-AUC:   {roc_auc:.4f}")

    print(f"\n{classification_report(labels, preds, target_names=LABEL_NAMES)}")

    metrics = {
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1_w, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc else None,
        "epoch_losses": [round(l, 4) for l in epoch_losses],
    }

    return model, tokenizer, preds, labels, probs, metrics, epoch_losses


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune BERT for extremism detection")
    parser.add_argument("--model", type=str, default=None,
                        help="Single HuggingFace model name to fine-tune "
                             "(default: compare distilbert + bert-base)")
    parser.add_argument("--epochs", type=int, default=4,
                        help="Number of training epochs (default: 4)")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Batch size (default: 16)")
    parser.add_argument("--lr", type=float, default=2e-5,
                        help="Learning rate (default: 2e-5)")
    parser.add_argument("--max-length", type=int, default=128,
                        help="Max token length (default: 128)")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── device selection ─────────────────────────────────────────────
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    print(f"Using device: {device}")

    # ── load data ────────────────────────────────────────────────────
    texts, labels = load_data()

    texts_train, texts_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_STATE, stratify=labels,
    )
    print(f"  Train: {len(texts_train)}  Test: {len(texts_test)}")

    # ── models to compare ────────────────────────────────────────────
    if args.model:
        model_names = [args.model]
    else:
        model_names = [
            "distilbert-base-uncased",
            "bert-base-uncased",
        ]

    all_results = {}
    best_f1 = -1
    best_model_info = None

    for model_name in model_names:
        model, tokenizer, preds, labels_arr, probs, metrics, losses = train_and_evaluate(
            model_name=model_name,
            texts_train=texts_train,
            texts_test=texts_test,
            y_train=y_train,
            y_test=y_test,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            max_length=args.max_length,
            device=device,
        )
        all_results[model_name] = metrics

        if metrics["f1_weighted"] > best_f1:
            best_f1 = metrics["f1_weighted"]
            best_model_info = (model, tokenizer, preds, labels_arr, probs, metrics, losses, model_name)

    # ── save best model ──────────────────────────────────────────────
    model, tokenizer, preds, labels_arr, probs, metrics, losses, best_name = best_model_info

    print(f"\n{'='*70}")
    print(f"BEST BERT MODEL: {best_name}  (F1={best_f1:.4f})")
    print("=" * 70)

    # Save model and tokenizer
    model.save_pretrained(BERT_MODEL_DIR)
    tokenizer.save_pretrained(BERT_MODEL_DIR)
    print(f"Model saved to: {BERT_MODEL_DIR}")

    # Save label mapping
    label_config = {
        "label_map": LABEL_MAP,
        "id2label": {0: "low", 1: "high"},
        "label2id": {"low": 0, "high": 1},
    }
    with open(os.path.join(BERT_MODEL_DIR, "label_config.json"), "w") as f:
        json.dump(label_config, f, indent=2)

    # ── visualizations ───────────────────────────────────────────────
    plot_training_loss(losses, best_name)
    plot_confusion(labels_arr, preds, best_name)
    plot_classification_heatmap(labels_arr, preds, best_name)

    if len(all_results) > 1:
        plot_model_comparison(all_results)

    # ── save training summary ────────────────────────────────────────
    summary = {
        "best_model": best_name,
        "models_compared": list(all_results.keys()),
        "results": all_results,
        "hyperparameters": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "max_length": args.max_length,
        },
        "device": device,
        "dataset_size": len(texts),
        "train_size": len(texts_train),
        "test_size": len(texts_test),
    }
    summary_path = os.path.join(MODEL_DIR, "bert_training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved: {summary_path}")

    print(f"\nDone. Best BERT model ({best_name}) saved to {BERT_MODEL_DIR}")


if __name__ == "__main__":
    main()
