import pandas as pd
import numpy as np

FEATURES = [
    "HeartRate", "Active Energy", "Blood Oxygen",
    "Calories", "Distance", "Resting Energy",
    "Weight", "Height", "bmi",
    "sleep_stage", "workout_encoded", "gender_encoded",
    "is_workout", "is_sleeping",
    "energy_balance", "fatigue_index", "active_ratio"
]


def universal_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()


    df.columns = [str(c).replace(" ", "").lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]


    mapping = {
        "heartrate": ["hr", "pulse", "heartrate"],
        "activeenergy": ["activeenergy", "active_energy", "energy"],
        "steps": ["steps", "st"],
        "sleepanalysis": ["sleep", "sleepanalysis", "sleep_stage"],
        "workouttype": ["workout", "workouttype", "activity_type"]
    }

    for standard, variations in mapping.items():
        for var in variations:
            if var in df.columns and standard not in df.columns:
                df = df.rename(columns={var: standard})


    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:
            df[col] = df[col].fillna(df[col].median())

    sleep_map = {"awake": 0, "light": 1, "rem": 2, "deep": 3}
    df["sleep_stage"] = df.get("sleepanalysis", pd.Series()).astype(str).str.lower().map(sleep_map).fillna(-1)

    workout_map = {"walking": 1, "yoga": 2, "cycling": 3, "running": 4}
    df["workout_encoded"] = df.get("workouttype", pd.Series()).astype(str).str.lower().map(workout_map).fillna(0)

    df["gender_encoded"] = (df.get("gender", "").astype(str).str.lower() == "male").astype(int)
    df["is_workout"] = (df.get("workouttype", pd.Series()).notna() & (df.get("workouttype") != "None")).astype(int)
    df["is_sleeping"] = (df.get("sleepanalysis", pd.Series()).notna() & (df.get("sleepanalysis") != "None")).astype(int)

    weight = df.get("weight", 70.0)
    height = df.get("height", 175.0)
    df["bmi"] = weight / ((height / 100) ** 2 + 0.001)

    df["energy_balance"] = df.get("calories", 0) - df.get("activeenergy", 0)
    df["fatigue_index"] = df.get("heartrate", 70) / (df["sleep_stage"] + 2)
    df["active_ratio"] = df.get("activeenergy", 0) / (df.get("calories", 0) + 1)

    clean_features = [f.replace(" ", "").lower() for f in FEATURES]
    for i, col in enumerate(clean_features):
        if col not in df.columns:
            df[col] = 0.0  


    df = df.reindex(columns=clean_features)
    df.columns = FEATURES
    return df
