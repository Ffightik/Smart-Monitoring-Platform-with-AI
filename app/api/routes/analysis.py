from fastapi import APIRouter, HTTPException
from app.api.routes.upload import get_user_data
from app.schemas.schemas import AnalysisResponse, HealthStats

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/{user_id}", response_model=AnalysisResponse)
async def get_analysis(user_id: str):
    data = get_user_data(user_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for user '{user_id}'.")

    raw_stats  = data.get("stats", {})
    raw_charts = data.get("raw_charts", {})

    print(f"[analysis] raw_charts keys: {list(raw_charts.keys())}")

    stats = HealthStats(
        avg_hr            = raw_stats.get("avg_hr"),
        min_hr            = raw_stats.get("min_hr"),
        max_hr            = raw_stats.get("max_hr"),
        avg_active_energy = raw_stats.get("avg_active_energy"),
        total_energy      = raw_stats.get("total_energy"),
        avg_sleep_stage   = raw_stats.get("avg_sleep_stage"),
        dominant_sleep    = raw_stats.get("dominant_sleep"),
        avg_bmi           = raw_stats.get("avg_bmi"),
        avg_weight        = raw_stats.get("avg_weight"),
        workout_days      = raw_stats.get("workout_days"),
        avg_blood_oxygen  = raw_stats.get("avg_blood_oxygen"),
        days_covered      = raw_stats.get("days_covered"),
    )

    return AnalysisResponse(user_id=user_id, stats=stats, charts=raw_charts)