import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import layers, models, callbacks, optimizers

# ── CONFIG ────────────────────────────────────────────────────────────────────
SEQUENCE_LENGTH    = 30
MODEL_PATH         = "app/models/lstm_model.keras"
SCALER_PATH        = "app/models/scaler.joblib"
TARGET_COLUMN      = "Activity Level"
TARGET_COLUMN_CLEAN = "activity_level"

EXTRA_DATA_PATHS = [
    "data/model_stress_test_data.csv",
]

FEATURES = [
    "HeartRate", "Active Energy", "Blood Oxygen",
    "Calories", "Distance", "Resting Energy",
    "Weight", "Height", "bmi",
    "sleep_stage", "workout_encoded", "gender_encoded",
    "is_workout", "is_sleeping",
    "energy_balance", "fatigue_index", "active_ratio"
]
FEATURES_CLEAN = [f.replace(" ", "").lower() for f in FEATURES]
LABELS_NAME = ["low", "medium", "high"]


def categorize(steps) -> int:
    if pd.isna(steps): return np.nan
    s = int(steps)
    if s == 0:      return 0
    elif s < 500:   return 1
    else:           return 2


def create_labels(df: pd.DataFrame) -> pd.DataFrame:
    steps_col = next((c for c in df.columns if "step" in c.lower()), None)
    if steps_col:
        df[TARGET_COLUMN] = df[steps_col].apply(categorize)
    else:
        df[TARGET_COLUMN] = 0
    return df


def load_data() -> pd.DataFrame:
    primary = "app/data/synthetic_health_data.csv"
    if not os.path.exists(primary):
        primary = "data/health_data.csv"
    if not os.path.exists(primary):
        raise FileNotFoundError(f"Primary data file not found at {primary}")

    print(f" Loading primary data from: {primary}")
    frames = [pd.read_csv(primary)]

    for path in EXTRA_DATA_PATHS:
        if os.path.exists(path):
            extra = pd.read_csv(path)
            print(f" Loading extra data from: {path} ({len(extra):,} rows)")
            frames.append(extra)
        else:
            print(f"️  Extra dataset not found (skipping): {path}")

    df = pd.concat(frames, ignore_index=True)
    print(f"   Combined rows: {len(df):,}")
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace(" ", "").lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    original_target_clean = TARGET_COLUMN.replace(" ", "").lower()

    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].fillna(df[col].median())

    sleep_map = {"awake": 0, "light": 1, "rem": 2, "deep": 3}
    s_col = next((c for c in df.columns if "sleep" in c), None)
    if s_col:
        df["sleep_stage"] = df[s_col].astype(str).str.lower().map(sleep_map).fillna(-1)
        df["is_sleeping"] = (df[s_col].notna() & (df[s_col].astype(str).str.lower() != "none")).astype(int)
    else:
        df["sleep_stage"] = -1; df["is_sleeping"] = 0

    workout_map = {"walking": 1, "yoga": 2, "cycling": 3, "running": 4}
    w_col = next((c for c in df.columns if "workout" in c), None)
    if w_col:
        df["workout_encoded"] = df[w_col].astype(str).str.lower().map(workout_map).fillna(0)
        df["is_workout"] = (df[w_col].notna() & (df[w_col].astype(str).str.lower() != "none")).astype(int)
    else:
        df["workout_encoded"] = 0; df["is_workout"] = 0

    df["gender_encoded"] = (
        df.get("gender", pd.Series([""] * len(df))).astype(str).str.lower() == "male"
    ).astype(int)

    hr  = df.get("heartrate",     pd.Series([70.0]  * len(df), index=df.index))
    cal = df.get("calories",      pd.Series([0.0]   * len(df), index=df.index))
    ae  = df.get("activeenergy",  pd.Series([0.0]   * len(df), index=df.index))
    w   = df.get("weight",        pd.Series([70.0]  * len(df), index=df.index))
    h   = df.get("height",        pd.Series([170.0] * len(df), index=df.index))
    re  = df.get("restingenergy", pd.Series([0.0]   * len(df), index=df.index))

    if cal.sum() == 0 and re.sum() > 0:
        cal = re + ae

    df["energy_balance"] = cal - ae
    df["fatigue_index"]  = hr / (df["sleep_stage"] + 2)
    df["active_ratio"]   = ae / (cal + 1.0)
    df["bmi"]            = w / ((h / 100) ** 2 + 0.001)

    for col in FEATURES_CLEAN:
        if col not in df.columns: df[col] = 0.0

    df = df.reindex(columns=FEATURES_CLEAN + [original_target_clean])
    df.columns = FEATURES + [TARGET_COLUMN]
    df[FEATURES] = df[FEATURES].fillna(0.0)

    before = len(df)
    df = df.dropna(subset=[TARGET_COLUMN])
    after = len(df)
    print(f"   Rows after dropna: {after:,} (dropped {before - after})")

    if after == 0:
        raise ValueError("DataFrame is empty after preprocessing!")

    print(f"   Label distribution:")
    counts = df[TARGET_COLUMN].value_counts().sort_index()
    for cls, cnt in counts.items():
        print(f"     {LABELS_NAME[int(cls)]:<8}: {cnt:,} ({cnt / after * 100:.1f}%)")

    return df


def create_sequences(df: pd.DataFrame):
    data = df[FEATURES + [TARGET_COLUMN]].values
    if len(data) < SEQUENCE_LENGTH:
        return np.array([]), np.array([])
    X, y = [], []
    for i in range(len(data) - SEQUENCE_LENGTH):
        X.append(data[i:i + SEQUENCE_LENGTH, :-1])
        y.append(data[i + SEQUENCE_LENGTH, -1])
    return np.array(X), np.array(y)


def create_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Masking(mask_value=0.0),
        layers.Bidirectional(layers.LSTM(64, return_sequences=True)),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Bidirectional(layers.LSTM(32)),
        layers.BatchNormalization(),
        layers.Dense(32, activation="relu"),
        layers.Dense(3,  activation="softmax"),
    ])
    model.compile(
        optimizer=optimizers.Adam(0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model():
    print(" Loading & Preprocessing...")
    df = load_data()
    df = create_labels(df)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df = preprocess(df)

    scaler = StandardScaler()
    df[FEATURES] = scaler.fit_transform(df[FEATURES])
    joblib.dump(scaler, SCALER_PATH)
    print(f" Scaler saved → {SCALER_PATH}")

    X, y = create_sequences(df)

    if X.size == 0:
        print(" Not enough data to create sequences!")
        return

    y = y.astype(np.int64)
    unique_classes = np.unique(y)
    print(f" Total sequences : {len(y):,}")
    print(f"   Classes present : {[LABELS_NAME[i] for i in unique_classes]}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        stratify=y if len(unique_classes) > 1 else None,
        random_state=42,
    )
    print(f"   Train: {X_train.shape[0]:,}  |  Test: {X_test.shape[0]:,}")

    weights = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
    print(f"   Class weights: {dict(enumerate(weights.round(3)))}")

    model = create_model((SEQUENCE_LENGTH, len(FEATURES)))

    print(" Training...")
    model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=32,
        validation_data=(X_test, y_test),
        class_weight=dict(enumerate(weights)),
        callbacks=[callbacks.EarlyStopping(patience=7, restore_best_weights=True)],
    )

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save(MODEL_PATH)
    print(f" Model saved → {MODEL_PATH}")

    y_pred  = np.argmax(model.predict(X_test, verbose=0), axis=1)
    present = np.unique(y_test)
    print(classification_report(
        y_test, y_pred,
        labels=present,
        target_names=[LABELS_NAME[i] for i in present],
        zero_division=0,
    ))


if __name__ == "__main__":
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    train_model()