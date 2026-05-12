import os
import io
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.parser import HealthParser
from app.core.universal_data_pipeline import UniversalPipeline
from app.core.data_validator import validate_health_data, trust_score_summary
from app.schemas.schemas import UploadResponse

router   = APIRouter(prefix="/upload", tags=["Upload"])
_user_store: dict = {}
parser   = HealthParser()
pipeline = UniversalPipeline()

RAW_CHART_COLS = {
    "Steps":        "steps",   "Step Count":   "steps",
    "HeartRate":    "heart_rate", "Heart Rate": "heart_rate",
    "Active Energy":"active_energy", "ActiveEnergy":"active_energy",
    "Distance":     "distance", "HRV": "hrv",
}

# ── Quick CSV pre-check (before full parse) ───────────────────────────────────
def _quick_csv_check(raw: bytes) -> None:
    """Fast structural check — rejects obvious non-health files immediately."""
    import pandas as pd
    try:
        df = pd.read_csv(io.BytesIO(raw), nrows=10)
    except Exception:
        raise HTTPException(status_code=422, detail="Cannot read CSV. Check the file format.")

    cols_norm = [c.lower().replace(" ","").replace("_","") for c in df.columns]

    # Hard reject: research dataset markers
    BAD = ["curvature","fiberkey","collagen","boundarypoint","epiregion",
           "ctfire","omnitest","osmonth","osstatus","genomic","mrna",
           "fiber","alignment","angularvariance","pixelcount"]
    found_bad = [kw for kw in BAD if any(kw in c for c in cols_norm)]
    if found_bad:
        sample = ", ".join(df.columns[:5].tolist())
        raise HTTPException(status_code=422, detail=(
            f"❌ This is not a personal health export.\n\n"
            f"Detected non-health columns: {sample}…\n\n"
            f"Please upload:\n"
            f"• Apple Health export.xml (iPhone → Health → Export)\n"
            f"• Smartwatch CSV with HeartRate, Steps, Calories, Sleep columns"
        ))

    # Min rows
    full = pd.read_csv(io.BytesIO(raw))
    if len(full) < 10:
        raise HTTPException(status_code=422, detail=(
            f"❌ Only {len(full)} rows — too few for analysis.\n\n"
            f"A health export should have hundreds of rows (one per hour or measurement).\n"
            f"This looks like aggregated research data."
        ))

    # Research IDs
    RESEARCH_IDS = ["patient_id","patientid","subject_id","os_months","os_status","tcga"]
    found_ids = [kw for kw in RESEARCH_IDS if any(kw in c for c in cols_norm)]
    if found_ids:
        raise HTTPException(status_code=422, detail=(
            f"❌ Clinical research dataset detected.\n\n"
            f"Found research identifiers: {', '.join(found_ids[:3])}\n\n"
            f"Please upload your own personal health export."
        ))


def get_user_data(user_id: str) -> dict | None:
    return _user_store.get(user_id)


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in (".xml", ".csv"):
        raise HTTPException(status_code=400,
            detail=f"❌ Unsupported file type '{ext}'. Use .xml or .csv")

    raw_bytes = await file.read()

    # ── Format-specific pre-checks ────────────────────────────────────────────
    if ext == ".csv":
        _quick_csv_check(raw_bytes)
    else:
        head = raw_bytes[:3000].decode("utf-8", errors="ignore")
        if not any(kw in head for kw in ["HealthData","HKRecord","ClinicalDocument"]):
            raise HTTPException(status_code=422, detail=(
                "❌ This XML is not an Apple Health export.\n\n"
                "Export from: iPhone → Health app → profile picture → Export All Health Data"
            ))

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        # ── Parse ─────────────────────────────────────────────────────────────
        if ext == ".xml":
            df_raw = parser.parse(tmp_path, days=120)
            if df_raw.empty:
                raise HTTPException(status_code=422, detail=(
                    "⚠️ No records found in last 120 days. Try a wider export."))
            df_raw = parser.to_pipeline_format(df_raw)
        else:
            import pandas as pd
            df_raw = pd.read_csv(io.BytesIO(raw_bytes))

        # ── Deep validation ───────────────────────────────────────────────────
        val_result = validate_health_data(df_raw)
        trust_info = trust_score_summary(val_result)

        # Hard block on critical validation failure
        if not val_result.model_allowed and val_result.trust_score < 0.20:
            errors_text = "\n".join(
                f"• {i.message}" for i in val_result.errors[:3]
            )
            raise HTTPException(status_code=422, detail=(
                f"❌ Data quality too low for analysis.\n\n"
                f"Trust score: {val_result.trust_score:.0%}\n\n"
                f"Issues found:\n{errors_text}\n\n"
                f"Please upload a proper health export file."
            ))

        # ── Save raw charts BEFORE pipeline ───────────────────────────────────
        raw_charts = {}
        for col, key in RAW_CHART_COLS.items():
            if col in df_raw.columns and key not in raw_charts:
                series = df_raw[col].fillna(0)
                if (series > 0).any():
                    raw_charts[key] = [round(float(v), 2) for v in series.tail(72).tolist()]

        # ── Pipeline ──────────────────────────────────────────────────────────
        features, labels, report = pipeline.process(df_raw, verbose=False)

        # Also grab chart cols from features
        for col, key in RAW_CHART_COLS.items():
            if col in features.columns and key not in raw_charts:
                series = features[col].fillna(0)
                if (series > 0).any():
                    raw_charts[key] = [round(float(v), 2) for v in series.tail(72).tolist()]

        stats = _compute_stats(features, df_raw)

        user_id = str(uuid.uuid4())[:8]
        _user_store[user_id] = {
            "features":   features,
            "labels":     labels,
            "stats":      stats,
            "raw_charts": raw_charts,
            "filename":   filename,
            "validation": trust_info,   # ← stored for predict.py to check
        }

        rows = len(features)
        days = max(1, rows // 24)

        # Build message with trust score info
        if val_result.trust_label == "high":
            trust_msg = f"✅ Data quality: excellent ({val_result.trust_score:.0%})"
        elif val_result.trust_label == "medium":
            trust_msg = f"⚠️ Data quality: medium ({val_result.trust_score:.0%}) — {len(val_result.warnings)} warnings"
        elif val_result.trust_label == "low":
            trust_msg = f"⚠️ Data quality: low ({val_result.trust_score:.0%}) — predictions may be less accurate"
        else:
            trust_msg = f"⛔ Data quality: insufficient ({val_result.trust_score:.0%}) — predictions blocked"

        return UploadResponse(
            user_id=user_id, rows=rows, days=days,
            message=f"Processed {rows:,} records. {trust_msg}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        os.unlink(tmp_path)


def _compute_stats(features, df_raw=None) -> dict:
    import numpy as np
    stats = {}
    for col, (avg_key, min_key, max_key) in {
        "HeartRate":     ("avg_hr",           "min_hr",  "max_hr"),
        "Active Energy": ("avg_active_energy", None,      "total_energy"),
        "Blood Oxygen":  ("avg_blood_oxygen",  None,      None),
    }.items():
        if col in features.columns:
            s = features[col].dropna(); s = s[s > 0]
            if len(s):
                stats[avg_key] = round(float(s.mean()), 1)
                if min_key: stats[min_key] = round(float(s.min()), 1)
                if max_key:
                    val = float(s.sum()) if col == "Active Energy" else float(s.max())
                    stats[max_key] = round(val, 1)

    for col, key in [("Weight","avg_weight"),("Height","height"),("bmi","avg_bmi")]:
        if col in features.columns:
            s = features[col].dropna(); s = s[s > 0]
            if len(s): stats[key] = round(float(s.median()), 1)

    if "sleep_stage" in features.columns:
        sl = features["sleep_stage"].dropna(); sl = sl[sl >= 0]
        if len(sl):
            stats["avg_sleep_stage"] = round(float(sl.mean()), 2)
            stats["dominant_sleep"]  = {0:"Awake",1:"Light",2:"REM",3:"Deep"}.get(int(sl.mode()[0]),"Unknown")

    if "is_workout" in features.columns:
        stats["workout_days"] = int((features["is_workout"] > 0).sum())

    if df_raw is not None:
        for col in ["Steps","Step Count","StepCount"]:
            if col in df_raw.columns:
                s = df_raw[col].dropna(); s = s[s > 0]
                if len(s):
                    stats["avg_steps"] = round(float(s.mean()), 1)
                    stats["max_steps"] = round(float(s.max()), 1)
                break

    stats["days_covered"] = max(1, len(features) // 24)
    return stats
