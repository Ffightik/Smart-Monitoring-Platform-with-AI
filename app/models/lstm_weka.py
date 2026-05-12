"""
lstm_weka.py
------------
Trains LSTM + XGB hybrid directly on the Weka Apple Watch dataset.
Labels: Lying / Sitting / Self Pace walk / Running (3/5/7 METs)
Mapped to: sedentary / light / moderate / vigorous

Run from project root:
    python app/models/lstm_weka.py
"""

import os, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import layers, models, callbacks, optimizers

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_PATH   = "app/data/data_for_weka_aw.csv"
LSTM_PATH   = "app/models/lstm_model.keras"
XGB_PATH    = "app/models/xgb_model.json"
SCALER_PATH = "app/models/scaler.joblib"

SEQ_LEN = 10   # shorter sequences — dataset has ~600 rows per class

# Activity → numeric label mapping
# 0 = sedentary, 1 = light, 2 = moderate, 3 = vigorous
ACTIVITY_MAP = {
    "Lying":           0,
    "Sitting":         0,
    "Self Pace walk":  1,
    "Running 3 METs":  2,
    "Running 5 METs":  2,
    "Running 7 METs":  3,
}
LABELS = ["sedentary", "light", "moderate", "vigorous"]

# Features available in this dataset
FEATURES = [
    "Applewatch.Steps_LE",
    "Applewatch.Heart_LE",
    "Applewatch.Calories_LE",
    "Applewatch.Distance_LE",
    "EntropyApplewatchHeartPerDay_LE",
    "EntropyApplewatchStepsPerDay_LE",
    "RestingApplewatchHeartrate_LE",
    "CorrelationApplewatchHeartrateSteps_LE",
    "NormalizedApplewatchHeartrate_LE",
    "ApplewatchIntensity_LE",
    "SDNormalizedApplewatchHR_LE",
    "ApplewatchStepsXDistance_LE",
    "age",
    "gender",
    "height",
    "weight",
    "bmi",
]
TARGET = "label"


# ── PREPROCESSING ─────────────────────────────────────────────────────────────

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Map activity labels
    df[TARGET] = df["activity_trimmed"].map(ACTIVITY_MAP)
    unmapped = df[TARGET].isna().sum()
    if unmapped > 0:
        print(f"⚠️  {unmapped} rows with unmapped activities — dropping")
    df = df.dropna(subset=[TARGET])
    df[TARGET] = df[TARGET].astype(int)

    # Derived features
    df["bmi"] = df["weight"] / ((df["height"] / 100) ** 2 + 0.001)

    # Ensure all features exist
    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    df[FEATURES] = df[FEATURES].fillna(df[FEATURES].median())

    return df


def create_sequences(X: np.ndarray, y: np.ndarray):
    Xs, ys = [], []
    for i in range(len(X) - SEQ_LEN):
        Xs.append(X[i:i + SEQ_LEN])
        ys.append(y[i + SEQ_LEN])
    return np.array(Xs), np.array(ys, dtype=np.int64)


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
    m.compile(
        optimizer=optimizers.Adam(0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return m


# ── MAIN ──────────────────────────────────────────────────────────────────────

def train():
    print("📂 Loading Weka Apple Watch dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    df = preprocess(df)

    print(f"\n   Label distribution:")
    counts = df[TARGET].value_counts().sort_index()
    for cls, cnt in counts.items():
        print(f"     {LABELS[cls]:<12}: {cnt:,} ({cnt/len(df)*100:.1f}%)")

    n_classes = len(df[TARGET].unique())

    # ── Scale ─────────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[FEATURES].values)
    y_all    = df[TARGET].values
    joblib.dump(scaler, SCALER_PATH)
    print(f"\n✅ Scaler saved → {SCALER_PATH}")

    # ── Sequences ─────────────────────────────────────────────────────────────
    X_seq, y_seq = create_sequences(X_scaled, y_all)
    print(f"\n📊 Sequences: {len(y_seq):,}  |  Shape: {X_seq.shape}")

    unique_classes = np.unique(y_seq)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_seq, y_seq, test_size=0.2,
        stratify=y_seq, random_state=42
    )
    print(f"   Train: {len(y_tr):,}  |  Test: {len(y_te):,}")

    weights = compute_class_weight("balanced", classes=unique_classes, y=y_tr)
    print(f"   Class weights: {dict(enumerate(weights.round(3)))}")

    # ── Train LSTM ────────────────────────────────────────────────────────────
    print("\n🚀 Training LSTM...")
    lstm = build_lstm((SEQ_LEN, len(FEATURES)), n_classes)
    lstm.fit(
        X_tr, y_tr,
        epochs=60,
        batch_size=32,
        validation_data=(X_te, y_te),
        class_weight=dict(enumerate(weights)),
        callbacks=[callbacks.EarlyStopping(
            patience=10, restore_best_weights=True, monitor="val_accuracy"
        )],
        verbose=1,
    )
    lstm.save(LSTM_PATH)
    print(f"✅ LSTM saved → {LSTM_PATH}")

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
    xgb_model.fit(X_flat_tr, y_tr, eval_set=[(X_flat_te, y_te)], verbose=False)
    xgb_model.save_model(XGB_PATH)
    print(f"✅ XGB saved → {XGB_PATH}")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    lstm_proba   = lstm.predict(X_te, verbose=0)
    xgb_proba    = xgb_model.predict_proba(X_flat_te)
    hybrid_proba = 0.7 * xgb_proba + 0.3 * lstm_proba

    present = sorted(np.unique(y_te))
    plabels = [LABELS[i] for i in present]

    print("\n=== EVALUATION ===")
    for name, pred in [
        ("LSTM",   np.argmax(lstm_proba,   axis=1)),
        ("XGB",    np.argmax(xgb_proba,    axis=1)),
        ("Hybrid", np.argmax(hybrid_proba, axis=1)),
    ]:
        acc = accuracy_score(y_te, pred)
        f1  = f1_score(y_te, pred, average="macro", zero_division=0)
        print(f"\n{name}  Acc: {acc:.4f}  F1: {f1:.4f}")
        print(classification_report(
            y_te, pred, labels=present,
            target_names=plabels, zero_division=0
        ))

    # Save label mapping for the API
    import json
    mapping = {
        "labels": LABELS,
        "activity_map": ACTIVITY_MAP,
        "features": FEATURES,
        "seq_len": SEQ_LEN,
        "n_classes": n_classes,
    }
    meta_path = "app/models/model_meta.json"
    with open(meta_path, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"\n✅ Model metadata saved → {meta_path}")
    print("\n✅ Training complete!")


if __name__ == "__main__":
    train()