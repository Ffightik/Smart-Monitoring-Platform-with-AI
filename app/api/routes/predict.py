import numpy as np
from fastapi import APIRouter, HTTPException
from app.api.routes.upload import get_user_data
from app.models.hybrid_model import load_resources
from app.schemas.schemas import PredictResponse, ModelConfidence, ActivityLevel
from app.core.data_validator import MINIMUM_TRUST
from app.config import settings

router = APIRouter(prefix="/predict", tags=["Predict"])
LABELS = settings.ACTIVITY_LABELS


@router.post("/{user_id}", response_model=PredictResponse)
async def predict(user_id: str):
    data = get_user_data(user_id)
    if not data:
        raise HTTPException(status_code=404,
            detail=f"No data found for user '{user_id}'. Upload a file first.")

    # ── Trust score gate ───────────────────────────────────────────────────────
    validation = data.get("validation", {})
    trust_score = validation.get("trust_score", 1.0)
    model_allowed = validation.get("model_allowed", True)
    block_reason  = validation.get("block_reason")

    if not model_allowed:
        raise HTTPException(status_code=422, detail=(
            f"⛔ Model prediction blocked.\n\n"
            f"Trust score: {trust_score:.0%} (minimum required: {MINIMUM_TRUST:.0%})\n\n"
            f"Reason: {block_reason}"
        ))

    features = data["features"]
    SEQ_LEN  = settings.SEQUENCE_LENGTH
    FEAT_COLS = [
        "HeartRate","Active Energy","Blood Oxygen","Calories","Distance",
        "Resting Energy","Weight","Height","bmi","sleep_stage",
        "workout_encoded","gender_encoded","is_workout","is_sleeping",
        "energy_balance","fatigue_index","active_ratio",
    ]

    try:
        xgb_model, lstm_model, scaler = load_resources()

        for col in FEAT_COLS:
            if col not in features.columns:
                features[col] = 0.0

        X = features[FEAT_COLS].fillna(0.0).values
        X_scaled = scaler.transform(X)

        xgb_proba = xgb_model.predict_proba(X_scaled[[-1]])[0]

        if len(X_scaled) < SEQ_LEN:
            pad = np.zeros((SEQ_LEN - len(X_scaled), X_scaled.shape[1]))
            seq = np.vstack([pad, X_scaled])
        else:
            seq = X_scaled[-SEQ_LEN:]
        lstm_proba = lstm_model.predict(seq[np.newaxis, ...], verbose=0)[0]

        n = min(len(xgb_proba), len(lstm_proba))
        hybrid_proba = 0.7 * xgb_proba[:n] + 0.3 * lstm_proba[:n]

        def to_label(proba):
            idx = int(np.argmax(proba))
            return LABELS[idx] if idx < len(LABELS) else "unknown"

        # ── Dampen confidence if trust is low ─────────────────────────────────
        # Low trust → cap confidence display so user isn't misled
        confidence_cap = 0.5 + (trust_score * 0.5)  # trust=0.45 → cap=0.725

        def capped(p): return round(float(min(np.max(p), confidence_cap)), 3)

        result = PredictResponse(
            user_id=user_id,
            current=ActivityLevel(to_label(xgb_proba)),
            next=ActivityLevel(to_label(lstm_proba)),
            hybrid=ActivityLevel(to_label(hybrid_proba)),
            confidence=ModelConfidence(
                xgb=capped(xgb_proba),
                lstm=capped(lstm_proba),
                hybrid=capped(hybrid_proba),
            ),
            message=(
                f"Predicted '{to_label(hybrid_proba)}' "
                f"[trust {trust_score:.0%}]"
                + (" ⚠️ low data quality" if trust_score < 0.65 else "")
            ),
        )

        # Cache
        from app.api.routes.upload import _user_store
        if user_id in _user_store:
            _user_store[user_id]["predict"] = result.model_dump()

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")