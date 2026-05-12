"""
app/core/data_validator.py
--------------------------
Multi-layer health data validation system.

Layers:
  1. Type validation      — columns have correct dtypes
  2. Range validation     — physiological bounds check
  3. Semantic validation  — time series, variability, user identity
  4. Trust Score          — 0.0–1.0 composite confidence metric

If trust_score < MINIMUM_TRUST → model prediction is BLOCKED.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

# ── Thresholds ────────────────────────────────────────────────────────────────
MINIMUM_TRUST        = 0.45   # below this → no prediction
MIN_ROWS_FOR_MODEL   = 24     # at least 24 hourly records
MIN_UNIQUE_HOURS     = 6      # at least 6 distinct hours
MIN_VARIABILITY_COLS = 2      # at least 2 columns must have std > 0

# ── Physiological ranges ──────────────────────────────────────────────────────
RANGES = {
    # Column name patterns → (min, max, unit)
    "HeartRate":         (28,  220, "bpm"),
    "Heart Rate":        (28,  220, "bpm"),
    "RestingHeartRate":  (28,  120, "bpm"),
    "HRV":               (0,   200, "ms"),
    "BloodOxygen":       (70,  100, "%"),
    "Blood Oxygen":      (70,  100, "%"),
    "Steps":             (0,   80_000, "steps"),
    "Step Count":        (0,   80_000, "steps"),
    "Sleep Analysis":    (-1,  3,   "stage"),
    "sleep_stage":       (-1,  3,   "stage"),
    "Weight":            (20,  300, "kg"),
    "Height":            (100, 250, "cm"),
    "bmi":               (10,  60,  ""),
    "ActiveEnergy":      (0,   5000, "kcal"),
    "Active Energy":     (0,   5000, "kcal"),
    "Distance":          (0,   200,  "km"),
    "Calories":          (0,   10000,"kcal"),
    "RespiratoryRate":   (4,   60,  "/min"),
    "BodyTemperature":   (34,  42,  "°C"),
}

# ── Result dataclasses ────────────────────────────────────────────────────────
@dataclass
class ValidationIssue:
    level:   str    # "error" | "warning" | "info"
    layer:   str    # "type" | "range" | "semantic" | "identity"
    column:  str
    message: str
    pct_affected: float = 0.0   # % of rows affected


@dataclass
class ValidationResult:
    passed:       bool
    trust_score:  float                        # 0.0 – 1.0
    trust_label:  str                          # "high" | "medium" | "low" | "rejected"
    issues:       list[ValidationIssue] = field(default_factory=list)
    stats:        dict                  = field(default_factory=dict)
    block_reason: Optional[str]         = None  # set if model is blocked

    @property
    def errors(self):   return [i for i in self.issues if i.level == "error"]
    @property
    def warnings(self): return [i for i in self.issues if i.level == "warning"]
    @property
    def model_allowed(self) -> bool:
        return self.passed and self.trust_score >= MINIMUM_TRUST


# ── Validator ─────────────────────────────────────────────────────────────────
class HealthDataValidator:
    """
    Run all validation layers on a processed health DataFrame.
    Call validate(df) → ValidationResult.
    """

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        issues: list[ValidationIssue] = []
        score_components: dict[str, float] = {}

        # ── Layer 1: Type validation ──────────────────────────────────────────
        type_score = self._validate_types(df, issues)
        score_components["types"] = type_score

        # ── Layer 2: Range validation ─────────────────────────────────────────
        range_score = self._validate_ranges(df, issues)
        score_components["ranges"] = range_score

        # ── Layer 3: Semantic validation ──────────────────────────────────────
        sem_score = self._validate_semantics(df, issues)
        score_components["semantics"] = sem_score

        # ── Layer 4: Identity / non-health check ──────────────────────────────
        id_score = self._validate_identity(df, issues)
        score_components["identity"] = id_score

        # ── Composite Trust Score ─────────────────────────────────────────────
        # Weighted average — semantics matters most for ML reliability
        weights = {"types": 0.20, "ranges": 0.30, "semantics": 0.35, "identity": 0.15}
        trust = sum(score_components[k] * weights[k] for k in weights)
        trust = round(float(np.clip(trust, 0.0, 1.0)), 3)

        # ── Determine label ───────────────────────────────────────────────────
        if trust >= 0.80:
            label = "high"
        elif trust >= 0.60:
            label = "medium"
        elif trust >= MINIMUM_TRUST:
            label = "low"
        else:
            label = "rejected"

        # ── Block model if needed ─────────────────────────────────────────────
        errors = [i for i in issues if i.level == "error"]
        block_reason = None

        if trust < MINIMUM_TRUST:
            block_reason = (
                f"Trust score {trust:.0%} is below the minimum {MINIMUM_TRUST:.0%} required "
                f"for reliable predictions. Please upload a longer or cleaner health export."
            )
        elif len(errors) >= 3:
            block_reason = (
                f"{len(errors)} critical data errors found. "
                f"Predictions would be unreliable."
            )

        # ── Stats summary ─────────────────────────────────────────────────────
        stats = {
            "rows":              len(df),
            "columns":           list(df.columns),
            "score_breakdown":   {k: round(v, 3) for k, v in score_components.items()},
            "error_count":       len(errors),
            "warning_count":     len([i for i in issues if i.level == "warning"]),
        }

        return ValidationResult(
            passed       = block_reason is None,
            trust_score  = trust,
            trust_label  = label,
            issues       = issues,
            stats        = stats,
            block_reason = block_reason,
        )

    # ── Layer 1: Types ────────────────────────────────────────────────────────
    def _validate_types(self, df: pd.DataFrame, issues: list) -> float:
        numeric_cols = [
            c for c in df.columns
            if c not in ("datetime", "date", "timestamp", "WorkoutType", "Sleep Analysis", "Gender")
        ]
        score = 1.0
        for col in numeric_cols:
            if col not in df.columns:
                continue
            n_bad = pd.to_numeric(df[col], errors="coerce").isna().sum() - df[col].isna().sum()
            if n_bad > 0:
                pct = n_bad / len(df)
                issues.append(ValidationIssue(
                    level="error" if pct > 0.1 else "warning",
                    layer="type",
                    column=col,
                    message=f"{n_bad} non-numeric values in '{col}' (expected numbers)",
                    pct_affected=round(pct * 100, 1),
                ))
                score -= 0.15 * min(pct * 5, 1.0)

        # Check datetime if present
        if "datetime" in df.columns:
            try:
                pd.to_datetime(df["datetime"])
            except Exception:
                issues.append(ValidationIssue(
                    level="error", layer="type", column="datetime",
                    message="datetime column contains unparseable values",
                ))
                score -= 0.2

        return max(0.0, score)

    # ── Layer 2: Ranges ───────────────────────────────────────────────────────
    def _validate_ranges(self, df: pd.DataFrame, issues: list) -> float:
        score = 1.0
        checked = 0

        for col, (lo, hi, unit) in RANGES.items():
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) == 0:
                continue
            checked += 1

            # Outliers outside physiological range
            out_of_range = series[(series < lo) | (series > hi)]
            pct = len(out_of_range) / len(series)

            if pct > 0.30:
                issues.append(ValidationIssue(
                    level="error", layer="range", column=col,
                    message=(
                        f"{pct:.0%} of '{col}' values outside physiological range "
                        f"[{lo}–{hi} {unit}]. "
                        f"Observed: min={series.min():.1f}, max={series.max():.1f}"
                    ),
                    pct_affected=round(pct * 100, 1),
                ))
                score -= 0.25
            elif pct > 0.05:
                issues.append(ValidationIssue(
                    level="warning", layer="range", column=col,
                    message=(
                        f"{pct:.0%} of '{col}' values outside normal range "
                        f"[{lo}–{hi} {unit}]. Possible sensor errors."
                    ),
                    pct_affected=round(pct * 100, 1),
                ))
                score -= 0.08

            # All-same-value (sensor stuck)
            if series.nunique() == 1:
                issues.append(ValidationIssue(
                    level="warning", layer="range", column=col,
                    message=f"'{col}' has only one unique value ({series.iloc[0]}). Sensor may be stuck.",
                    pct_affected=100.0,
                ))
                score -= 0.10

        if checked == 0:
            issues.append(ValidationIssue(
                level="error", layer="range", column="—",
                message="No recognisable health metric columns found for range validation.",
            ))
            score = 0.0

        return max(0.0, score)

    # ── Layer 3: Semantics ────────────────────────────────────────────────────
    def _validate_semantics(self, df: pd.DataFrame, issues: list) -> float:
        score = 1.0
        n = len(df)

        # 3a. Minimum rows
        if n < MIN_ROWS_FOR_MODEL:
            issues.append(ValidationIssue(
                level="error", layer="semantic", column="—",
                message=(
                    f"Only {n} rows found. Minimum {MIN_ROWS_FOR_MODEL} required for reliable predictions. "
                    f"This may be aggregated data (one row per patient) rather than a time series."
                ),
            ))
            score -= 0.50

        # 3b. Time series presence
        if "datetime" in df.columns:
            try:
                dt = pd.to_datetime(df["datetime"])
                n_unique_days  = dt.dt.date.nunique()
                n_unique_hours = dt.dt.hour.nunique()
                span_days      = (dt.max() - dt.min()).days

                if n_unique_hours < MIN_UNIQUE_HOURS:
                    issues.append(ValidationIssue(
                        level="error", layer="semantic", column="datetime",
                        message=(
                            f"Only {n_unique_hours} distinct hours in data. "
                            f"A health export should span many hours across multiple days."
                        ),
                    ))
                    score -= 0.30

                if span_days < 1:
                    issues.append(ValidationIssue(
                        level="warning", layer="semantic", column="datetime",
                        message=f"Data spans less than 1 day ({span_days} days). Short window reduces prediction quality.",
                    ))
                    score -= 0.15
                elif span_days >= 7:
                    score = min(1.0, score + 0.05)  # bonus for long history

            except Exception:
                pass
        else:
            # No datetime — check if rows look like a time series
            if n < 48:
                issues.append(ValidationIssue(
                    level="warning", layer="semantic", column="—",
                    message="No datetime column found and fewer than 48 rows. Cannot confirm time-series structure.",
                ))
                score -= 0.10

        # 3c. Variability check — data should not be all-constant
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 0:
            stds = numeric_df.std(ddof=0)
            varying = (stds > 0.01).sum()
            if varying < MIN_VARIABILITY_COLS:
                issues.append(ValidationIssue(
                    level="error", layer="semantic", column="—",
                    message=(
                        f"Only {varying} columns have any variability. "
                        f"Real health data fluctuates over time — this looks like static/aggregated data."
                    ),
                ))
                score -= 0.40
            elif varying < 4:
                issues.append(ValidationIssue(
                    level="warning", layer="semantic", column="—",
                    message=f"Only {varying} columns show variability. Limited signal for ML prediction.",
                ))
                score -= 0.10

        # 3d. HeartRate specific sanity check
        hr_col = next((c for c in ["HeartRate","Heart Rate"] if c in df.columns), None)
        if hr_col:
            hr = pd.to_numeric(df[hr_col], errors="coerce").dropna()
            if len(hr) > 5:
                # Real HR should vary — sleeping vs active
                if hr.std() < 2.0:
                    issues.append(ValidationIssue(
                        level="warning", layer="semantic", column=hr_col,
                        message=(
                            f"Heart rate standard deviation is only {hr.std():.1f} bpm. "
                            f"Real HR varies significantly between rest and activity (expect >5 bpm std)."
                        ),
                    ))
                    score -= 0.12

                # Check for physiologically impossible transitions
                diffs = hr.diff().abs().dropna()
                extreme_jumps = (diffs > 60).sum()
                if extreme_jumps > len(hr) * 0.05:
                    issues.append(ValidationIssue(
                        level="warning", layer="semantic", column=hr_col,
                        message=(
                            f"{extreme_jumps} HR transitions >60 bpm in consecutive readings. "
                            f"Possible sensor noise or data quality issues."
                        ),
                    ))
                    score -= 0.08

        return max(0.0, score)

    # ── Layer 4: Identity / non-health check ──────────────────────────────────
    def _validate_identity(self, df: pd.DataFrame, issues: list) -> float:
        score = 1.0
        cols_lower = [c.lower().replace(" ","").replace("_","") for c in df.columns]

        # Research dataset identifiers
        RESEARCH_COLS = [
            "patientid","patient","pat","subjectid","caseid","sampleid",
            "osmonth","osstatus","survival","deceased","tcga","biopsy",
            "curvature","fiber","collagen","pixel","ctfire",
            "genomic","mutation","mrna","expression","histology",
        ]
        found = [kw for kw in RESEARCH_COLS if any(kw in c for c in cols_lower)]
        if found:
            issues.append(ValidationIssue(
                level="error", layer="identity", column=", ".join(found[:3]),
                message=(
                    f"Detected research/clinical dataset identifiers: {', '.join(found[:3])}. "
                    f"This appears to be a research dataset, not a personal health export. "
                    f"Please upload your own Apple Watch or smartwatch data."
                ),
            ))
            score = 0.0

        # Multi-user data (patient IDs suggest multiple people)
        id_like = [c for c in df.columns if any(kw in c.lower() for kw in ["id","user","patient","subject"])]
        for col in id_like:
            if col in df.columns:
                n_unique = df[col].nunique()
                if n_unique > 5:
                    issues.append(ValidationIssue(
                        level="error", layer="identity", column=col,
                        message=(
                            f"'{col}' has {n_unique} unique values — this looks like data from "
                            f"{n_unique} different people, not a single user's health export."
                        ),
                    ))
                    score -= 0.50
                    break

        # Minimum health keywords
        HEALTH_KW = [
            "heartrate","heart","bpm","steps","calories","energy","oxygen",
            "sleep","weight","height","distance","workout","activity","hrv",
        ]
        has_health = any(kw in c for c in cols_lower for kw in HEALTH_KW)
        if not has_health and score > 0:
            issues.append(ValidationIssue(
                level="error", layer="identity", column="—",
                message="No health-related columns detected. This does not appear to be a health dataset.",
            ))
            score = 0.0

        return max(0.0, score)


# ── Public helper ─────────────────────────────────────────────────────────────
def validate_health_data(df: pd.DataFrame) -> ValidationResult:
    """Convenience function — validate a DataFrame and return ValidationResult."""
    return HealthDataValidator().validate(df)


def trust_score_summary(result: ValidationResult) -> dict:
    """Return a dict ready to serialize to JSON for the frontend."""
    return {
        "trust_score":    result.trust_score,
        "trust_label":    result.trust_label,
        "model_allowed":  result.model_allowed,
        "block_reason":   result.block_reason,
        "error_count":    len(result.errors),
        "warning_count":  len(result.warnings),
        "issues": [
            {
                "level":        i.level,
                "layer":        i.layer,
                "column":       i.column,
                "message":      i.message,
                "pct_affected": i.pct_affected,
            }
            for i in result.issues
        ],
    }