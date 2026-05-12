"""
app/models/models_evaluation.py
--------------------------------
Универсальный evaluation — работает с ЛЮБЫМ датасетом.
Использует UniversalPipeline для автоматического маппинга колонок.

Запуск:
    python -m app.models.models_evaluation
    python -m app.models.models_evaluation --data data/unclean_smartwatch_health_data.csv
    python -m app.models.models_evaluation --data data/data_for_weka_aw.csv
"""

import os, sys, warnings, argparse
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_curve, auc, f1_score, accuracy_score
)
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import layers, models, callbacks, optimizers

from app.core.universal_data_pipeline import UniversalPipeline, MODEL_FEATURES

# ── CONFIG ────────────────────────────────────────────────────────────────────
DEFAULT_DATA = "data/data_for_weka_aw.csv"
LSTM_PATH    = "app/models/lstm_model.keras"
XGB_PATH     = "app/models/xgb_model.json"
SCALER_PATH  = "app/models/scaler.joblib"
OUT_PATH     = "app/models/evaluation_report.png"
SEQ_LEN      = 10

# Label names — indexed by numeric class value
# Pipeline maps everything to 0/1/2/3
LABEL_NAMES = {
    0: "sedentary / low",
    1: "light / medium",
    2: "moderate / high",
    3: "vigorous",
}

# ── THEME ─────────────────────────────────────────────────────────────────────
DARK_BG = "#0F1117"
CARD_BG = "#1A1D27"
TEXT    = "#E8EAF0"
GRID_C  = "#2A2D3A"
COLORS  = ["#4FC3F7", "#81C784", "#FFB74D", "#F06292"]
HEAT_CMAP = LinearSegmentedColormap.from_list(
    "eval", ["#0F1117", "#1A237E", "#4FC3F7", "#81C784"], N=256
)
plt.rcParams.update({
    "figure.facecolor": DARK_BG, "axes.facecolor": CARD_BG,
    "axes.edgecolor": GRID_C,    "axes.labelcolor": TEXT,
    "axes.titlecolor": TEXT,     "xtick.color": TEXT,
    "ytick.color": TEXT,         "text.color": TEXT,
    "grid.color": GRID_C,        "grid.linestyle": "--",
    "grid.alpha": 0.5,           "font.family": "DejaVu Sans",
    "font.size": 10,             "axes.titlesize": 11,
    "axes.titleweight": "bold",  "legend.facecolor": CARD_BG,
    "legend.edgecolor": GRID_C,
})


# ── SEQUENCES ─────────────────────────────────────────────────────────────────

def create_sequences(X: np.ndarray, y: np.ndarray):
    Xs, ys = [], []
    for i in range(len(X) - SEQ_LEN):
        Xs.append(X[i:i + SEQ_LEN])
        ys.append(y[i + SEQ_LEN])
    return np.array(Xs), np.array(ys, dtype=np.int64)


# ── MODEL ─────────────────────────────────────────────────────────────────────

def build_lstm(input_shape, n_classes):
    m = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Bidirectional(layers.LSTM(64, return_sequences=True)),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Bidirectional(layers.LSTM(32)),
        layers.BatchNormalization(),
        layers.Dense(32, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(n_classes, activation="softmax"),
    ])
    m.compile(optimizer="adam",
              loss="sparse_categorical_crossentropy",
              metrics=["accuracy"])
    return m


# ── PLOT HELPERS ──────────────────────────────────────────────────────────────

def plot_history(ax_loss, ax_acc, history):
    ep = range(1, len(history["loss"]) + 1)
    ax_loss.plot(ep, history["loss"],     color=COLORS[0], lw=2, label="Train")
    ax_loss.plot(ep, history["val_loss"], color=COLORS[2], lw=2, ls="--", label="Val")
    ax_loss.set_title("Training Loss")
    ax_loss.set_xlabel("Epoch")
    ax_loss.legend(); ax_loss.grid(True)

    ax_acc.plot(ep, history["accuracy"],     color=COLORS[1], lw=2, label="Train")
    ax_acc.plot(ep, history["val_accuracy"], color=COLORS[2], lw=2, ls="--", label="Val")
    ax_acc.set_title("Training Accuracy")
    ax_acc.set_xlabel("Epoch")
    ax_acc.set_ylim(0, 1.05)
    ax_acc.legend(); ax_acc.grid(True)


def plot_cm(ax, y_true, y_pred, title, present, label_names):
    cm     = confusion_matrix(y_true, y_pred, labels=present)
    cm_pct = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9) * 100
    lbls   = [label_names.get(i, str(i)) for i in present]
    sns.heatmap(cm_pct, annot=True, fmt=".1f", cmap=HEAT_CMAP,
                xticklabels=lbls, yticklabels=lbls, ax=ax,
                cbar=False, annot_kws={"size": 9, "weight": "bold"})
    ax.set_title(f"{title}\nConfusion Matrix (%)")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)


def plot_f1(ax, reports, present, label_names):
    x, width = np.arange(len(present)), 0.25
    for idx, (name, rep) in enumerate(reports.items()):
        lbl_keys = [label_names.get(i, str(i)) for i in present]
        f1s  = [rep.get(lbl, {}).get("f1-score", 0) for lbl in lbl_keys]
        bars = ax.bar(x + idx * width, f1s, width, label=name,
                      color=COLORS[idx], alpha=0.85, edgecolor=DARK_BG)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.01,
                    f"{h:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x + width)
    ax.set_xticklabels([label_names.get(i, str(i)) for i in present],
                       fontsize=8)
    ax.set_ylim(0, 1.2)
    ax.set_title("F1-Score per Class")
    ax.set_ylabel("F1"); ax.legend(); ax.grid(True, axis="y")


def plot_roc(ax, y_bin, probas, present):
    ls_map = {"LSTM": "-", "XGB": "--", "Hybrid": "-."}
    for name, proba in probas.items():
        for idx, i in enumerate(present):
            if i >= proba.shape[1]: continue
            fpr, tpr, _ = roc_curve(y_bin[:, i], proba[:, i])
            ra = auc(fpr, tpr)
            ax.plot(fpr, tpr, color=COLORS[idx % len(COLORS)],
                    lw=1.5, linestyle=ls_map.get(name, "-"),
                    alpha=0.85, label=f"{name}·c{i} {ra:.2f}")
    ax.plot([0,1],[0,1], "w--", lw=0.6, alpha=0.3)
    ax.set_title("ROC Curves")
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
    ax.legend(fontsize=7, loc="lower right"); ax.grid(True)


def plot_confidence(ax, probas):
    for (name, proba), color in zip(probas.items(), COLORS):
        conf = np.max(proba, axis=1)
        ax.hist(conf, bins=25, color=color, alpha=0.65,
                label=f"{name} μ={conf.mean():.2f}",
                edgecolor=DARK_BG, linewidth=0.3)
    ax.axvline(0.5, color="#EF5350", ls="--", lw=1.2, label="50%")
    ax.set_title("Confidence Distribution")
    ax.set_xlabel("Max probability"); ax.set_ylabel("Count")
    ax.legend(fontsize=8); ax.grid(True)


def plot_feature_importance(ax, xgb_model):
    imp   = xgb_model.feature_importances_
    order = np.argsort(imp)
    short = [f.replace(" ", "").replace("Energy", "E")
               .replace("encoded", "enc")
               .replace("balance", "bal") for f in MODEL_FEATURES]
    ax.barh([short[i] for i in order], imp[order],
            color=COLORS[0], alpha=0.8, edgecolor=DARK_BG)
    ax.set_title("XGB Feature Importance")
    ax.set_xlabel("Gain"); ax.grid(True, axis="x")


def plot_label_dist(ax, labels, label_names):
    counts = labels[labels >= 0].value_counts().sort_index()
    lbls   = [label_names.get(i, str(i)) for i in counts.index]
    bars   = ax.barh(lbls, counts.values,
                     color=COLORS[:len(counts)], alpha=0.85, edgecolor=DARK_BG)
    for bar, val in zip(bars, counts.values):
        ax.text(val + counts.max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9)
    ax.set_title("Dataset Label Distribution")
    ax.set_xlabel("Count"); ax.grid(True, axis="x")


def plot_summary(ax, reports, y_true, preds, present, label_names):
    ax.axis("off")
    lbl_cols = [label_names.get(i, f"class {i}") for i in present]
    cols = ["Model", "Accuracy", "F1 macro"] + lbl_cols
    rows = []
    for name, (rep, pred) in zip(reports.keys(),
                                  zip(reports.values(), preds.values())):
        f1s = [f"{rep.get(label_names.get(i,''), {}).get('f1-score', 0):.3f}"
               for i in present]
        rows.append([
            name,
            f"{accuracy_score(y_true, pred):.4f}",
            f"{f1_score(y_true, pred, average='macro', zero_division=0):.4f}",
            *f1s,
        ])
    tbl = ax.table(cellText=rows, colLabels=cols,
                   loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10); tbl.scale(1, 2.2)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_facecolor(CARD_BG if r > 0 else "#1F2535")
        cell.set_edgecolor(GRID_C)
        cell.set_text_props(color=TEXT,
                            fontweight="bold" if r == 0 else "normal")
    ax.set_title("Evaluation Summary", fontsize=13,
                 fontweight="bold", pad=16)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DEFAULT_DATA,
                        help="Path to any CSV dataset")
    parser.add_argument("--out",  default=OUT_PATH,
                        help="Output PNG path")
    args = parser.parse_args()

    # ── Load via UniversalPipeline ────────────────────────────────────────────
    print(f"📂 Loading: {args.data}")
    pipeline = UniversalPipeline()
    features, labels, report = pipeline.process(args.data, verbose=True)
    print("\n" + report.summary())

    if labels is None:
        print("❌ No label column found. Cannot evaluate.")
        return

    # Remove rows with label = -1 (unmapped/null)
    valid    = labels >= 0
    features = features[valid].reset_index(drop=True)
    labels   = labels[valid].reset_index(drop=True)

    if len(features) < SEQ_LEN + 10:
        print(f"❌ Not enough valid rows ({len(features)}) after filtering.")
        return

    present_orig = sorted(labels.unique())
    n_classes    = len(present_orig)

    # Remap labels to sequential 0,1,2,... (required by sparse_categorical_crossentropy)
    remap     = {orig: new for new, orig in enumerate(present_orig)}
    remap_inv = {new: orig for orig, new in remap.items()}
    labels    = labels.map(remap)
    present   = list(range(n_classes))
    label_names = {new: LABEL_NAMES.get(orig, f"class {orig}")
                   for new, orig in remap_inv.items()}

    if present_orig != present:
        print(f"   Label remap : {remap}  (non-sequential -> remapped)")

    print(f"\n📊 Valid rows  : {len(features):,}")
    print(f"   Classes     : {[label_names[i] for i in present]}")

    # ── Scale ─────────────────────────────────────────────────────────────────
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(features[MODEL_FEATURES].values)
    y_all    = labels.values

    # ── Sequences ─────────────────────────────────────────────────────────────
    X_seq, y_seq = create_sequences(X_scaled, y_all)
    print(f"   Sequences   : {len(y_seq):,}")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_seq, y_seq, test_size=0.2,
        stratify=y_seq, random_state=42
    )
    weights = compute_class_weight("balanced",
                                   classes=np.unique(y_tr), y=y_tr)

    # ── Train LSTM ────────────────────────────────────────────────────────────
    print("\n🚀 Training LSTM...")
    lstm = build_lstm((SEQ_LEN, len(MODEL_FEATURES)), n_classes)
    hist = lstm.fit(
        X_tr, y_tr, epochs=60, batch_size=32,
        validation_data=(X_te, y_te),
        class_weight=dict(enumerate(weights)),
        callbacks=[callbacks.EarlyStopping(
            patience=10, restore_best_weights=True,
            monitor="val_accuracy"
        )],
        verbose=1,
    )
    history = hist.history

    # ── Train XGB ─────────────────────────────────────────────────────────────
    print("\n🚀 Training XGB...")
    X_flat_tr = X_tr[:, -1, :]
    X_flat_te = X_te[:, -1, :]
    xgb_model = xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="mlogloss",
        random_state=42, verbosity=0,
    )
    xgb_model.fit(X_flat_tr, y_tr,
                  eval_set=[(X_flat_te, y_te)], verbose=False)

    # ── Predictions ───────────────────────────────────────────────────────────
    lstm_proba   = lstm.predict(X_te, verbose=0)
    xgb_proba    = xgb_model.predict_proba(X_flat_te)

    # Align probability arrays to same number of classes
    n_out = max(lstm_proba.shape[1], xgb_proba.shape[1])
    def pad(p, n):
        if p.shape[1] < n:
            pad = np.zeros((p.shape[0], n - p.shape[1]))
            return np.hstack([p, pad])
        return p
    lstm_proba = pad(lstm_proba, n_out)
    xgb_proba  = pad(xgb_proba,  n_out)

    hybrid_proba = 0.7 * xgb_proba + 0.3 * lstm_proba
    lstm_pred    = np.argmax(lstm_proba,   axis=1)
    xgb_pred     = np.argmax(xgb_proba,    axis=1)
    hybrid_pred  = np.argmax(hybrid_proba, axis=1)

    plabels = [label_names[i] for i in present]
    reports = {
        "LSTM":   classification_report(y_te, lstm_pred,   target_names=plabels,
                                         labels=present, output_dict=True, zero_division=0),
        "XGB":    classification_report(y_te, xgb_pred,    target_names=plabels,
                                         labels=present, output_dict=True, zero_division=0),
        "Hybrid": classification_report(y_te, hybrid_pred, target_names=plabels,
                                         labels=present, output_dict=True, zero_division=0),
    }
    probas = {"LSTM": lstm_proba, "XGB": xgb_proba, "Hybrid": hybrid_proba}
    preds  = {"LSTM": lstm_pred,  "XGB": xgb_pred,  "Hybrid": hybrid_pred}
    y_bin  = label_binarize(y_te, classes=list(range(n_out)))

    print("\n=== RESULTS ===")
    for name, pred in preds.items():
        acc = accuracy_score(y_te, pred)
        f1  = f1_score(y_te, pred, average="macro", zero_division=0)
        print(f"{name:8s}  Acc: {acc:.4f}  F1: {f1:.4f}")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    dataset_name = os.path.basename(args.data)
    print(f"\n🎨 Building dashboard for {dataset_name}...")

    fig = plt.figure(figsize=(24, 30), facecolor=DARK_BG)
    fig.suptitle(f"HealthPlatform — Model Evaluation\n{dataset_name}",
                 fontsize=16, fontweight="bold", color=TEXT, y=0.995)

    gs = gridspec.GridSpec(5, 4, figure=fig,
                           hspace=0.55, wspace=0.4,
                           left=0.06, right=0.97,
                           top=0.96, bottom=0.04)

    # Row 0: loss + accuracy + label dist
    plot_history(fig.add_subplot(gs[0, :2]),
                 fig.add_subplot(gs[0, 2]), history)
    plot_label_dist(fig.add_subplot(gs[0, 3]), labels, label_names)

    # Row 1: confusion matrices + F1 bars
    plot_cm(fig.add_subplot(gs[1, 0]), y_te, lstm_pred,   "LSTM",   present, label_names)
    plot_cm(fig.add_subplot(gs[1, 1]), y_te, xgb_pred,    "XGB",    present, label_names)
    plot_cm(fig.add_subplot(gs[1, 2]), y_te, hybrid_pred, "Hybrid", present, label_names)
    plot_f1(fig.add_subplot(gs[1, 3]), reports, present, label_names)

    # Row 2: ROC + feature importance
    plot_roc(fig.add_subplot(gs[2, :2]), y_bin, probas, present)
    plot_feature_importance(fig.add_subplot(gs[2, 2:]), xgb_model)

    # Row 3: probability distributions + confidence
    for idx, (name, proba) in enumerate(probas.items()):
        ax = fig.add_subplot(gs[3, idx])
        for i, (cls, col) in enumerate(zip(present, COLORS)):
            if i < proba.shape[1]:
                ax.hist(proba[:, i], bins=25, color=col, alpha=0.6,
                        label=label_names.get(cls, str(cls)),
                        edgecolor=DARK_BG, linewidth=0.3)
        ax.set_title(f"{name} — Class Probabilities")
        ax.set_xlabel("Probability"); ax.set_ylabel("Count")
        ax.legend(fontsize=7); ax.grid(True)
    plot_confidence(fig.add_subplot(gs[3, 3]), probas)

    # Row 4: summary table
    plot_summary(fig.add_subplot(gs[4, :]),
                 reports, y_te, preds, present, label_names)

    out_path = args.out
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    print(f"✅ Report saved → {out_path}")
    plt.show()


if __name__ == "__main__":
    main()

