import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight

import xgboost as xgb

# -----------------------------
# CONFIG
# -----------------------------
TARGET_COLUMN = "Activity Level"
MODEL_PATH = "app/models/xgb_model.json"


# -----------------------------
# LOAD DATA
# -----------------------------
def load_data():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(BASE_DIR, "data", "health_data.csv")
    print(f"📂 Loading from: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


# -----------------------------
# CREATE LABELS
# ✅ Пороги подобраны под реальные данные (max Steps = 6996, median = 305)
# low:    Steps <= 100  (покой/сон — нули и минимальная активность)
# medium: Steps 101–400 (умеренная активность)
# high:   Steps > 400   (активные тренировки)
# -----------------------------
def create_labels(df):
    def categorize(steps):
        if pd.isna(steps) or steps <= 100:
            return 0  # low
        elif steps <= 400:
            return 1  # medium
        else:
            return 2  # high

    df[TARGET_COLUMN] = df["Steps"].apply(categorize)
    return df


# -----------------------------
# CLEAN + FEATURE ENGINEERING
# -----------------------------
def preprocess(df):
    df = df.copy()

    # ✅ Числовые признаки
    num_cols = ["HeartRate", "Active Energy", "Steps",
                "Blood Oxygen", "Calories", "Distance",
                "Resting Energy", "Weight", "Height"]

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    # ✅ Кодируем Sleep Analysis (был текстовый)
    sleep_map = {"Awake": 0, "Light": 1, "REM": 2, "Deep": 3}
    df["sleep_stage"] = df["Sleep Analysis"].map(sleep_map).fillna(-1)

    # ✅ Кодируем Workout Type
    workout_map = {"Walking": 1, "Yoga": 2, "Cycling": 3, "Running": 4}
    df["workout_encoded"] = df["Workout Type"].map(workout_map).fillna(0)

    # ✅ Кодируем Gender
    df["gender_encoded"] = (df["Gender"] == "Male").astype(int)

    # ✅ Флаг: идёт тренировка или нет
    df["is_workout"] = (df["Workout Type"].notna()).astype(int)

    # ✅ Флаг: человек спит
    df["is_sleeping"] = (df["Sleep Analysis"].notna()).astype(int)

    # ✅ Производные признаки
    df["energy_balance"] = df["Calories"] - df["Active Energy"]
    df["fatigue_index"] = df["HeartRate"] / (df["sleep_stage"] + 2)
    df["active_ratio"] = df["Active Energy"] / (df["Calories"] + 1)
    df["bmi"] = df["Weight"] / ((df["Height"] / 100) ** 2 + 0.001)

    # ✅ Duration всегда 60 — бесполезен, убираем
    return df


# -----------------------------
# PLOT TRAINING CURVES
# -----------------------------
def plot_training(model):
    results = model.evals_result()
    epochs = len(results['validation_0']['mlogloss'])

    plt.figure(figsize=(10, 5))
    plt.plot(range(epochs), results['validation_0']['mlogloss'], label='Train Loss')
    plt.plot(range(epochs), results['validation_1']['mlogloss'], label='Validation Loss')

    best_epoch = np.argmin(results['validation_1']['mlogloss'])
    plt.axvline(x=best_epoch, color='red', linestyle='--',
                label=f'Best epoch: {best_epoch}')

    plt.xlabel("Epoch")
    plt.ylabel("Log Loss")
    plt.title("XGBoost Training vs Validation Loss")
    plt.legend()
    plt.tight_layout()
    plt.show()


# -----------------------------
# TRAIN MODEL
# -----------------------------
def train_model():
    print("📥 Loading data...")
    df = load_data()

    print("🧹 Cleaning + Feature Engineering...")
    df = preprocess(df)

    print("🏷 Creating labels...")
    df = create_labels(df)

    # Распределение классов
    print("\n📊 Class distribution (0=low, 1=medium, 2=high):")
    counts = df[TARGET_COLUMN].value_counts().sort_index()
    labels_name = ["low", "medium", "high"]
    for label, count in counts.items():
        pct = count / len(df) * 100
        print(f"  {label} ({labels_name[label]}): {count:>6} ({pct:.1f}%)")

    FEATURES = [
        "HeartRate", "Active Energy", "Blood Oxygen",
        "Calories", "Distance", "Resting Energy",
        "Weight", "Height", "bmi",
        "sleep_stage", "workout_encoded", "gender_encoded",
        "is_workout", "is_sleeping",
        "energy_balance", "fatigue_index", "active_ratio"
    ]

    X = df[FEATURES]
    y = df[TARGET_COLUMN]

    print(f"\n🔍 Classes in y: {sorted(y.unique())}")
    assert y.nunique() == 3, "Должно быть ровно 3 класса!"

    print("🔀 Splitting...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

    print("🚀 Training XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        min_child_weight=3,
        num_class=3,
        objective="multi:softmax",
        eval_metric="mlogloss",
        early_stopping_rounds=30,
        random_state=42,
        n_jobs=-1
    )


    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        sample_weight=sample_weights,
        verbose=True
    )

    # EVALUATION
    print("\n📈 Evaluating...")
    y_pred = model.predict(X_test)

    print(f"\n✅ Accuracy:      {accuracy_score(y_test, y_pred):.4f}")
    print(f"✅ F1 (weighted): {f1_score(y_test, y_pred, average='weighted'):.4f}")
    print(f"✅ F1 (macro):    {f1_score(y_test, y_pred, average='macro'):.4f}")

    print("\n📊 Classification Report:")
    print(classification_report(y_test, y_pred,
                                target_names=labels_name,
                                zero_division=0))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("📉 Confusion Matrix:")
    print(cm)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1, 2])
    ax.set_yticks([0, 1, 2])
    ax.set_xticklabels(labels_name)
    ax.set_yticklabels(labels_name)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=12)
    plt.colorbar(im)
    plt.tight_layout()
    plt.show()

    plot_training(model)

    # Feature importance
    importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\n🔍 Feature Importances:")
    print(importances.to_string())

    model.save_model(MODEL_PATH)
    print("\n💾 Model saved (XGBoost)")
    return model


if __name__ == "__main__":
    train_model()