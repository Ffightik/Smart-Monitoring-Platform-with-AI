"""
app/core/universal_data_pipeline.py
------------------------------------
Универсальный пайплайн — принимает ЛЮБОЙ датасет,
возвращает стандартный DataFrame с фиксированными 17 фичами.

Использование:
    from app.core.universal_data_pipeline import UniversalPipeline
    pipeline = UniversalPipeline()
    df, report = pipeline.process("data/any_file.csv")
"""

import re
import numpy as np
import pandas as pd
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL SLOTS — это то что модель всегда ожидает
# ══════════════════════════════════════════════════════════════════════════════

CANONICAL_SLOTS = {
    "heart_rate":     ["heartrate", "heart_rate", "hr", "bpm", "pulse",
                       "heart rate", "heart rate (bpm)", "applewatch.heart_le",
                       "herzfrequenz", "пульс", "частота сердечных сокращений"],

    "steps":          ["steps", "step_count", "stepcount", "step count",
                       "applewatch.steps_le", "шаги", "количество шагов",
                       "daily_steps", "totalsteps"],

    "active_energy":  ["active_energy", "activeenergy", "active energy",
                       "calories_burned", "active calories",
                       "applewatch.calories_le", "активные калории"],

    "calories":       ["calories", "totalcalories", "total_calories",
                       "cal", "kcal", "калории"],

    "distance":       ["distance", "dist", "applewatch.distance_le",
                       "distance_km", "расстояние"],

    "resting_energy": ["resting_energy", "restingenergy", "resting energy",
                       "basal_energy", "bmr", "restingapplewatchheartrate_le"],

    "blood_oxygen":   ["blood_oxygen", "bloodoxygen", "spo2", "oxygen",
                       "blood oxygen level (%)", "blood oxygen",
                       "кислород", "насыщение кислородом"],

    "heart_rate_variability": ["hrv", "heart_rate_variability",
                               "sdnn", "rmssd"],

    "weight":         ["weight", "body_mass", "bodymass", "вес", "масса"],
    "height":         ["height", "рост"],
    "age":            ["age", "возраст"],
    "gender":         ["gender", "sex", "пол"],

    "sleep":          ["sleep", "sleep_analysis", "sleepanalysis",
                       "sleep_stage", "sleep duration", "sleep duration (hours)",
                       "сон"],

    "workout":        ["workout", "workout_type", "workouttype",
                       "activity_type", "exercise"],

    "activity_label": ["activity_level", "activity", "activity_trimmed",
                       "label", "class", "target", "тип активности"],

    "stress":         ["stress", "stress_level", "стресс"],

    "intensity":      ["applewatchintensity_le", "intensity",
                       "correlationapplewatchheartratesteps_le",
                       "normalizedapplewatchheartrate_le"],
}

# Финальные 17 фичей которые ожидает модель
MODEL_FEATURES = [
    "HeartRate", "Active Energy", "Blood Oxygen",
    "Calories", "Distance", "Resting Energy",
    "Weight", "Height", "bmi",
    "sleep_stage", "workout_encoded", "gender_encoded",
    "is_workout", "is_sleeping",
    "energy_balance", "fatigue_index", "active_ratio",
]

SLEEP_MAP   = {"awake": 0, "light": 1, "rem": 2, "deep": 3,
               "none": -1, "nan": -1}
WORKOUT_MAP = {"walking": 1, "yoga": 2, "cycling": 3, "running": 4,
               "self pace walk": 1, "lying": 0, "sitting": 0}

ACTIVITY_LABEL_MAP = {
    # sedentary
    "lying": 0, "sitting": 0, "sedentary": 0, "seddentary": 0,
    # light
    "light": 1, "self pace walk": 1, "walking": 1, "active": 1, "actve": 1,
    # moderate
    "moderate": 2, "running 3 mets": 2, "running 5 mets": 2,
    # vigorous
    "vigorous": 3, "running 7 mets": 3, "highly active": 3, "highly_active": 3,
    # synthetic
    "low": 0, "medium": 1, "high": 2,
}


# ══════════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineReport:
    """Человекочитаемый отчёт о том что произошло с данными."""
    original_columns: list         = field(default_factory=list)
    mapped_slots:     dict         = field(default_factory=dict)   # slot → col
    missing_slots:    list         = field(default_factory=list)
    filled_with:      dict         = field(default_factory=dict)   # slot → strategy
    rows_dropped:     int          = 0
    outliers_fixed:   dict         = field(default_factory=dict)
    label_column:     Optional[str]= None
    label_map:        dict         = field(default_factory=dict)
    warnings:         list         = field(default_factory=list)

    def summary(self) -> str:
        lines = ["=== Pipeline Report ==="]
        lines.append(f"Original columns : {len(self.original_columns)}")
        lines.append(f"Mapped slots     : {len(self.mapped_slots)}")
        if self.missing_slots:
            lines.append(f"Missing (filled) : {self.missing_slots}")
        if self.outliers_fixed:
            lines.append(f"Outliers fixed   : {self.outliers_fixed}")
        if self.rows_dropped:
            lines.append(f"Rows dropped     : {self.rows_dropped}")
        if self.label_column:
            lines.append(f"Label column     : {self.label_column}")
        for w in self.warnings:
            lines.append(f"WARNING: {w}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — SCHEMA DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class SchemaDetector:
    """
    Определяет формат файла по наличию ключевых колонок.
    Возвращает название схемы и confidence score.
    """

    SCHEMAS = {
        "weka": ["activity_trimmed", "applewatch.heart_le", "applewatch.steps_le"],
        "smartwatch": ["activity level", "step count", "heart rate (bpm)"],
        "synthetic": ["heartrate", "steps", "sleep analysis"],
        "apple_health": ["heartrate", "active energy", "blood oxygen"],
        "generic": [],  # fallback
    }

    def detect(self, df: pd.DataFrame) -> tuple[str, float]:
        cols_lower = [c.lower().strip() for c in df.columns]

        scores = {}
        for schema, keywords in self.SCHEMAS.items():
            if not keywords:
                scores[schema] = 0.1
                continue
            hits = sum(1 for kw in keywords if kw in cols_lower)
            scores[schema] = hits / len(keywords)

        best = max(scores, key=scores.get)
        return best, scores[best]


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — COLUMN MAPPER
# ══════════════════════════════════════════════════════════════════════════════

class ColumnMapper:
    """
    Fuzzy-матчинг: находит в датафрейме колонку
    которая соответствует каждому canonical slot.
    """

    def _normalize(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def map(self, df: pd.DataFrame) -> dict[str, Optional[str]]:
        """
        Returns {slot: actual_column_name} or {slot: None} if not found.
        """
        df_cols = {col: self._normalize(col) for col in df.columns}
        mapping = {}

        for slot, aliases in CANONICAL_SLOTS.items():
            best_col, best_score = None, 0.0
            norm_aliases = [self._normalize(a) for a in aliases]

            for col, norm_col in df_cols.items():
                # Exact match first
                if norm_col in norm_aliases:
                    best_col, best_score = col, 1.0
                    break
                # Fuzzy match
                for alias in norm_aliases:
                    score = self._similarity(norm_col, alias)
                    if score > best_score and score >= 0.75:
                        best_col, best_score = col, score

            mapping[slot] = best_col

        return mapping


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — FEATURE ENGINEER
# ══════════════════════════════════════════════════════════════════════════════

class FeatureEngineer:
    """
    Строит стандартный вектор из 17 фичей.
    Заполняет пропуски умными дефолтами.
    Фиксит выбросы.
    """

    # Физиологические границы — за пределами → outlier
    BOUNDS = {
        "heart_rate":    (30, 220),
        "blood_oxygen":  (70, 100),
        "steps":         (0, 100_000),
        "weight":        (20, 300),
        "height":        (100, 250),
        "age":           (1, 120),
    }

    # Дефолты когда колонка полностью отсутствует
    DEFAULTS = {
        "heart_rate":    70.0,
        "steps":         0.0,
        "active_energy": 0.0,
        "calories":      0.0,
        "distance":      0.0,
        "resting_energy":0.0,
        "blood_oxygen":  98.0,
        "weight":        70.0,
        "height":        170.0,
        "age":           30.0,
        "gender":        0,
        "sleep":         "none",
        "workout":       "none",
        "stress":        0.0,
        "intensity":     0.0,
    }

    def _get(self, df, mapping, slot, default=None):
        col = mapping.get(slot)
        if col and col in df.columns:
            return df[col].copy()
        return pd.Series(
            [default if default is not None else self.DEFAULTS.get(slot, 0.0)] * len(df),
            index=df.index
        )

    def _fix_outliers(self, series, slot, report):
        if slot not in self.BOUNDS:
            return series
        lo, hi = self.BOUNDS[slot]
        mask = (series < lo) | (series > hi)
        n = mask.sum()
        if n > 0:
            series = series.copy()
            series[mask] = np.nan
            report.outliers_fixed[slot] = int(n)
        return series

    def engineer(
        self,
        df: pd.DataFrame,
        mapping: dict,
        report: PipelineReport,
    ) -> pd.DataFrame:

        out = pd.DataFrame(index=df.index)

        # ── Raw signals ───────────────────────────────────────────────────────
        hr  = self._get(df, mapping, "heart_rate",    70.0).astype(float)
        hr  = self._fix_outliers(hr,  "heart_rate",   report)

        cal = self._get(df, mapping, "calories",      0.0).astype(float)
        ae  = self._get(df, mapping, "active_energy", 0.0).astype(float)
        re  = self._get(df, mapping, "resting_energy",0.0).astype(float)
        bo  = self._get(df, mapping, "blood_oxygen",  98.0).astype(float)
        bo  = self._fix_outliers(bo, "blood_oxygen",  report)
        dist= self._get(df, mapping, "distance",      0.0).astype(float)
        w   = self._get(df, mapping, "weight",        70.0).astype(float)
        w   = self._fix_outliers(w,  "weight",        report)
        h   = self._get(df, mapping, "height",        170.0).astype(float)
        h   = self._fix_outliers(h,  "height",        report)

        # If Calories missing but Resting + Active exist → approximate
        if cal.sum() == 0 and (re + ae).sum() > 0:
            cal = re + ae
            report.filled_with["calories"] = "resting_energy + active_energy"

        # Fill numeric nulls with median
        for name, series in [("hr", hr), ("cal", cal), ("ae", ae),
                               ("bo", bo), ("w", w), ("h", h)]:
            series.fillna(series.median(), inplace=True)

        out["HeartRate"]       = hr
        out["Active Energy"]   = ae
        out["Blood Oxygen"]    = bo
        out["Calories"]        = cal
        out["Distance"]        = dist.fillna(0)
        out["Resting Energy"]  = re.fillna(0)
        out["Weight"]          = w
        out["Height"]          = h

        # ── Sleep ─────────────────────────────────────────────────────────────
        sleep_col = mapping.get("sleep")
        if sleep_col and sleep_col in df.columns:
            raw_sleep = df[sleep_col]
            numeric_sleep = pd.to_numeric(raw_sleep, errors="coerce")
            is_numeric = numeric_sleep.notna().mean() > 0.8

            if is_numeric:
                # Hours of sleep (e.g. "Sleep Duration (hours)")
                # 0 h        → -1 (not sleeping)
                # 0–4 h      →  0 (awake / poor)
                # 4–6 h      →  1 (light)
                # 6–8 h      →  2 (rem)
                # 8+ h       →  3 (deep / full rest)
                hours = numeric_sleep.fillna(0)
                stage = pd.cut(
                    hours,
                    bins=[-0.01, 0, 4, 6, 8, 99],
                    labels=[-1, 0, 1, 2, 3],
                ).astype(float)
                out["sleep_stage"] = stage.fillna(-1)
                out["is_sleeping"] = (hours > 0).astype(int)
                report.filled_with["sleep"] = "converted from hours to stage buckets"
            else:
                # Categorical stages: "light", "deep", "rem", "awake"
                raw_str = raw_sleep.astype(str).str.lower().str.strip()
                out["sleep_stage"] = raw_str.map(SLEEP_MAP).fillna(-1)
                out["is_sleeping"] = (
                    ~raw_str.isin(["none", "nan", ""])
                ).astype(int)
        else:
            # Infer from HR — low HR → likely sleeping
            night_hr_threshold = hr.quantile(0.25)
            out["sleep_stage"] = np.where(hr < night_hr_threshold, 1, -1)
            out["is_sleeping"] = (hr < night_hr_threshold).astype(int)
            report.filled_with["sleep"] = "inferred from low HR"
            report.missing_slots.append("sleep")

        # ── Workout ───────────────────────────────────────────────────────────
        workout_col = mapping.get("workout")
        if workout_col and workout_col in df.columns:
            raw_workout = df[workout_col].astype(str).str.lower().str.strip()
            out["workout_encoded"] = raw_workout.map(WORKOUT_MAP).fillna(0)
            out["is_workout"] = (
                ~raw_workout.isin(["none", "nan", ""])
            ).astype(int)
        else:
            # Infer from steps — high steps → likely workout
            step_col = mapping.get("steps")
            if step_col and step_col in df.columns:
                steps = df[step_col].astype(float).fillna(0)
                high_steps = steps > steps.quantile(0.75)
                out["workout_encoded"] = high_steps.astype(int)
                out["is_workout"]      = high_steps.astype(int)
                report.filled_with["workout"] = "inferred from high step count"
            else:
                out["workout_encoded"] = 0
                out["is_workout"]      = 0
            report.missing_slots.append("workout")

        # ── Gender ────────────────────────────────────────────────────────────
        gender_col = mapping.get("gender")
        if gender_col and gender_col in df.columns:
            g = df[gender_col].astype(str).str.lower().str.strip()
            out["gender_encoded"] = (
                g.isin(["male", "m", "1", "мужской"])
            ).astype(int)
        else:
            out["gender_encoded"] = 0  # neutral default
            report.missing_slots.append("gender")
            report.filled_with["gender"] = "default 0 (unknown)"

        # ── BMI ───────────────────────────────────────────────────────────────
        out["bmi"] = w / ((h / 100) ** 2 + 0.001)

        # ── Derived metrics ───────────────────────────────────────────────────
        out["energy_balance"] = out["Calories"] - out["Active Energy"]
        out["fatigue_index"]  = out["HeartRate"] / (out["sleep_stage"] + 2)
        out["active_ratio"]   = (
            out["Active Energy"] / (out["Calories"] + 1.0)
        )

        # ── Final order ───────────────────────────────────────────────────────
        out = out.reindex(columns=MODEL_FEATURES, fill_value=0.0)
        out = out.fillna(0.0)

        return out

    def extract_labels(
        self,
        df: pd.DataFrame,
        mapping: dict,
        report: PipelineReport,
    ) -> Optional[pd.Series]:
        """
        Пытается найти целевую переменную.
        Возвращает Series с int метками или None.
        """
        label_col = mapping.get("activity_label")
        if label_col is None or label_col not in df.columns:
            return None

        report.label_column = label_col
        raw = df[label_col].astype(str).str.lower().str.strip()

        # Try numeric first
        numeric = pd.to_numeric(raw, errors="coerce")
        if numeric.notna().mean() > 0.8:
            report.label_map = {"numeric": "direct"}
            return numeric.fillna(-1).astype(int)

        # Map text labels
        mapped = raw.map(ACTIVITY_LABEL_MAP)
        unmapped = mapped.isna().sum()
        if unmapped > 0:
            unique_unmapped = raw[mapped.isna()].unique()[:5].tolist()
            report.warnings.append(
                f"{unmapped} rows with unmapped labels: {unique_unmapped}"
            )
        report.label_map = ACTIVITY_LABEL_MAP
        return mapped.fillna(-1).astype(int)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class UniversalPipeline:
    """
    Единая точка входа для любого датасета.

    pipeline = UniversalPipeline()
    df_features, labels, report = pipeline.process("data/any.csv")
    """

    def __init__(self):
        self.detector  = SchemaDetector()
        self.mapper    = ColumnMapper()
        self.engineer  = FeatureEngineer()

    def process(
        self,
        source,            # str path OR pd.DataFrame
        verbose: bool = True,
    ) -> tuple[pd.DataFrame, Optional[pd.Series], PipelineReport]:

        report = PipelineReport()

        # ── Load ──────────────────────────────────────────────────────────────
        if isinstance(source, str):
            if source.endswith(".xml"):
                raise ValueError(
                    "XML files need the HealthParser first. "
                    "Use parser.parse_apple_health(path) → df, then pipeline.process(df)."
                )
            df = pd.read_csv(source)
        else:
            df = source.copy()

        report.original_columns = df.columns.tolist()

        # ── Layer 1: detect schema ────────────────────────────────────────────
        schema, confidence = self.detector.detect(df)
        if verbose:
            print(f"📋 Schema detected : {schema} (confidence {confidence:.0%})")
        if confidence < 0.4:
            report.warnings.append(
                f"Low schema confidence ({confidence:.0%}). "
                "Column mapping may be inaccurate."
            )

        # ── Layer 2: map columns ──────────────────────────────────────────────
        mapping = self.mapper.map(df)
        report.mapped_slots = {k: v for k, v in mapping.items() if v is not None}
        if verbose:
            print(f"🔗 Mapped slots    : {len(report.mapped_slots)} / {len(CANONICAL_SLOTS)}")
            for slot, col in report.mapped_slots.items():
                print(f"   {slot:<22} → {col}")

        # ── Layer 3: engineer features ────────────────────────────────────────
        features = self.engineer.engineer(df, mapping, report)
        labels   = self.engineer.extract_labels(df, mapping, report)

        if verbose:
            print(f"\n✅ Output shape    : {features.shape}")
            if labels is not None:
                valid = (labels >= 0).sum()
                print(f"✅ Labels found    : {valid:,} valid rows")
            if report.warnings:
                for w in report.warnings:
                    print(f"⚠️  {w}")

        return features, labels, report


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/unclean_smartwatch_health_data.csv"

    pipeline = UniversalPipeline()
    features, labels, report = pipeline.process(path)

    print("\n" + report.summary())
    print(f"\nFeature sample:\n{features.head(3).to_string()}")
    if labels is not None:
        print(f"\nLabel distribution:\n{labels.value_counts().sort_index()}")