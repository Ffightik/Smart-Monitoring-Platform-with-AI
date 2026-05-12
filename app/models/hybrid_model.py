import numpy as np
import pandas as pd
import xgboost as xgb
import joblib
import os
from tensorflow.keras.models import load_model
from sklearn.metrics import accuracy_score, f1_score, classification_report

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

XGB_PATH   = "app/models/xgb_model.json"
LSTM_PATH  = "app/models/lstm_model.keras"
SCALER_PATH = "app/models/scaler.joblib"

TARGET  = ["low", "medium", "high"]
SEQ_LEN = 30

FEATURES = [
    "HeartRate", "Active Energy", "Blood Oxygen",
    "Calories", "Distance", "Resting Energy",
    "Weight", "Height", "bmi",
    "sleep_stage", "workout_encoded", "gender_encoded",
    "is_workout", "is_sleeping",
    "energy_balance", "fatigue_index", "active_ratio"
]
FEATURES_CLEAN = [f.replace(" ", "").lower() for f in FEATURES]

_xgb_model  = None
_lstm_model = None
_scaler     = None


def load_resources():
    global _xgb_model, _lstm_model, _scaler
    if _xgb_model is None:
        _xgb_model = xgb.XGBClassifier()
        _xgb_model.load_model(XGB_PATH)
    if _lstm_model is None:
        _lstm_model = load_model(LSTM_PATH)
    if _scaler is None:
        if os.path.exists(SCALER_PATH):
            _scaler = joblib.load(SCALER_PATH)
        else:
            raise FileNotFoundError(
                f"❌ Scaler not found at {SCALER_PATH}. Train the LSTM first!"
            )
    return _xgb_model, _lstm_model, _scaler


# ── Preprocessing ─────────────────────────────────────────────────────────────

def robust_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace(" ", "").lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    # Fill numeric NaNs with median
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].fillna(df[col].median())

    # Sleep
    sleep_map = {"awake": 0, "light": 1, "rem": 2, "deep": 3}
    s_col = next((c for c in df.columns if "sleep" in c), None)
    if s_col:
        df["sleep_stage"] = (
            df[s_col].astype(str).str.lower().map(sleep_map).fillna(-1)
        )
        df["is_sleeping"] = (
            df[s_col].notna()
            & (df[s_col].astype(str).str.lower() != "none")
        ).astype(int)
    else:
        df["sleep_stage"] = -1
        df["is_sleeping"] = 0

    # Workout
    workout_map = {"walking": 1, "yoga": 2, "cycling": 3, "running": 4}
    w_col = next((c for c in df.columns if "workout" in c), None)
    if w_col:
        df["workout_encoded"] = (
            df[w_col].astype(str).str.lower().map(workout_map).fillna(0)
        )
        df["is_workout"] = (
            df[w_col].notna()
            & (df[w_col].astype(str).str.lower() != "none")
        ).astype(int)
    else:
        df["workout_encoded"] = 0
        df["is_workout"] = 0

    df["gender_encoded"] = (
        df.get("gender", pd.Series([""] * len(df)))
        .astype(str).str.lower() == "male"
    ).astype(int)

    # Derived metrics — guard against missing columns with .get(col, default)
    hr  = df.get("heartrate",    pd.Series([70.0]  * len(df), index=df.index))
    cal = df.get("calories",     pd.Series([0.0]   * len(df), index=df.index))
    ae  = df.get("activeenergy", pd.Series([0.0]   * len(df), index=df.index))
    w   = df.get("weight",       pd.Series([70.0]  * len(df), index=df.index))
    h   = df.get("height",       pd.Series([170.0] * len(df), index=df.index))

    # FIX: if Calories column is missing/all-zero but RestingEnergy exists,
    # approximate Calories as RestingEnergy + ActiveEnergy
    re = df.get("restingenergy", pd.Series([0.0] * len(df), index=df.index))
    if cal.sum() == 0 and re.sum() > 0:
        cal = re + ae

    df["energy_balance"] = cal - ae
    df["fatigue_index"]  = hr / (df["sleep_stage"] + 2)
    df["active_ratio"]   = ae / (cal + 1.0)
    df["bmi"]            = w / ((h / 100) ** 2 + 0.001)

    return df


def ensure_features(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).replace(" ", "").lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reindex(columns=FEATURES_CLEAN, fill_value=0.0)
    df.columns = FEATURES
    return df


# ── Single-row prediction (for API / real-time use) ───────────────────────────

def predict(df: pd.DataFrame) -> dict:
    """Predict activity level for the latest row in df (uses full history for LSTM)."""
    xgb_model, lstm_model, scaler = load_resources()

    df_proc = robust_preprocess(df.copy())
    df_proc = ensure_features(df_proc)

    # XGB: classify current (last) row
    last_row = df_proc[FEATURES].iloc[[-1]].values   # numpy array → no feature-name warning
    xgb_proba = xgb_model.predict_proba(last_row)[0]

    # LSTM: predict next state from sequence
    data_scaled = scaler.transform(df_proc[FEATURES].values)
    if len(data_scaled) < SEQ_LEN:
        pad = np.zeros((SEQ_LEN - len(data_scaled), len(FEATURES)))
        data_scaled = np.vstack([pad, data_scaled])
    seq = data_scaled[-SEQ_LEN:][np.newaxis, ...]     # shape (1, SEQ_LEN, n_features)

    lstm_proba = lstm_model.predict(seq, verbose=0)[0]

    hybrid_proba = 0.7 * xgb_proba + 0.3 * lstm_proba

    return {
        "current":    TARGET[int(np.argmax(xgb_proba))],
        "next":       TARGET[int(np.argmax(lstm_proba))],
        "hybrid":     TARGET[int(np.argmax(hybrid_proba))],
        "confidence": {
            "xgb":    float(np.max(xgb_proba)),
            "lstm":   float(np.max(lstm_proba)),
            "hybrid": float(np.max(hybrid_proba)),
        },
    }


# ── Batch evaluation (vectorised — no per-row model calls) ───────────────────

def evaluate(df: pd.DataFrame):
    """
    Evaluate the hybrid model on a labelled test CSV.

    FIX: instead of calling predict() in a loop (which re-runs the TF graph
    thousands of times and is ~100x slower), we:
      1. Preprocess the whole DataFrame once
      2. Run XGB on all rows in one batch
      3. Build all LSTM sequences and run them in one model.predict() call
      4. Combine and score
    """
    xgb_model, lstm_model, scaler = load_resources()

    # ── Find target column ───────────────────────────────────────────────────
    target_col = next(
        (c for c in df.columns if "target" in c.lower() or "anomaly" in c.lower()),
        None
    )
    if target_col is None:
        print("❌ Evaluation aborted: Target column not found.")
        return

    y_raw = df[target_col].values
    unique_labels = np.unique(y_raw)
    n_classes = len(TARGET)

    # Warn if the label space doesn't match the model's output classes
    if not all(l in range(n_classes) for l in unique_labels):
        print(
            f"⚠️  WARNING: Target column '{target_col}' contains values {unique_labels.tolist()}, "
            f"but the model predicts activity classes 0/1/2 ({TARGET}). "
            f"Evaluation results may be misleading."
        )
    if len(unique_labels) == 1:
        print(
            f"⚠️  WARNING: Only one class ({unique_labels[0]}) present in '{target_col}'. "
            f"Accuracy will be trivially 1.0 — this test set cannot meaningfully evaluate the model."
        )

    # ── Preprocess entire DataFrame once ─────────────────────────────────────
    print("🔄 Preprocessing...")
    df_proc = robust_preprocess(df.copy())
    df_proc = ensure_features(df_proc)
    scaled  = scaler.transform(df_proc[FEATURES].values)   # (N, n_feat)

    n = len(scaled)
    eval_start = SEQ_LEN   # first index where we have a full sequence

    print(f"📊 Evaluating on {n - eval_start} samples...")

    # ── XGB: batch predict on all rows from eval_start onward ────────────────
    xgb_proba_all = xgb_model.predict_proba(
        df_proc[FEATURES].iloc[eval_start:].values
    )                                                       # (M, 3)

    # ── LSTM: build all sequences, predict in one batch ──────────────────────
    seqs = np.stack([
        scaled[i - SEQ_LEN: i]
        for i in range(eval_start, n)
    ])                                                      # (M, SEQ_LEN, n_feat)

    print("🤖 Running LSTM batch inference...")
    lstm_proba_all = lstm_model.predict(seqs, batch_size=256, verbose=1)  # (M, 3)

    # ── Hybrid ───────────────────────────────────────────────────────────────
    hybrid_proba_all = 0.7 * xgb_proba_all + 0.3 * lstm_proba_all

    y_true    = y_raw[eval_start:].astype(int)
    y_hybrid  = np.argmax(hybrid_proba_all, axis=1).astype(int)
    y_xgb     = np.argmax(xgb_proba_all,   axis=1).astype(int)
    y_lstm    = np.argmax(lstm_proba_all,   axis=1).astype(int)

    present_classes = sorted(np.unique(np.concatenate([y_true, y_hybrid])))
    label_names     = [TARGET[i] for i in present_classes]

    print("\n=== FINAL HYBRID EVALUATION ===")
    print(f"Accuracy : {accuracy_score(y_true, y_hybrid):.4f}")
    print(f"F1 Score : {f1_score(y_true, y_hybrid, average='weighted', labels=present_classes, zero_division=0):.4f}")
    print("\nClassification report (hybrid):")
    print(classification_report(
        y_true, y_hybrid,
        labels=present_classes,
        target_names=label_names,
        zero_division=0
    ))
    print(f"XGB-only  accuracy: {accuracy_score(y_true, y_xgb):.4f}")
    print(f"LSTM-only accuracy: {accuracy_score(y_true, y_lstm):.4f}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_path = "data/hybrid_model_test_data.csv"
    if os.path.exists(test_path):
        test_df = pd.read_csv(test_path)
        evaluate(test_df)
    else:
        print(f"❌ File {test_path} not found.")