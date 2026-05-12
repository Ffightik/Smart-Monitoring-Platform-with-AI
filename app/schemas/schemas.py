from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ActivityLevel(str, Enum):
    low       = "low"
    medium    = "medium"
    high      = "high"
    sedentary = "sedentary"
    light     = "light"
    moderate  = "moderate"
    vigorous  = "vigorous"
    unknown   = "unknown"


class UploadResponse(BaseModel):
    user_id: str
    rows:    int
    days:    int
    message: str


class HealthStats(BaseModel):
    avg_hr:            Optional[float] = None
    min_hr:            Optional[float] = None
    max_hr:            Optional[float] = None
    avg_active_energy: Optional[float] = None
    total_energy:      Optional[float] = None
    avg_sleep_stage:   Optional[float] = None
    dominant_sleep:    Optional[str]   = None
    avg_bmi:           Optional[float] = None
    avg_weight:        Optional[float] = None
    workout_days:      Optional[int]   = None
    avg_blood_oxygen:  Optional[float] = None
    days_covered:      Optional[int]   = None


class AnalysisResponse(BaseModel):
    user_id: str
    stats:   HealthStats
    charts:  dict = Field(default_factory=dict)


class ModelConfidence(BaseModel):
    xgb:    float
    lstm:   float
    hybrid: float


class PredictResponse(BaseModel):
    user_id:    str
    current:    ActivityLevel
    next:       ActivityLevel
    hybrid:     ActivityLevel
    confidence: ModelConfidence
    message:    str


class ChatRequest(BaseModel):
    user_id:        str
    message:        str
    stats:          Optional[HealthStats]     = None
    prediction:     Optional[PredictResponse] = None
    inject_context: bool = False


class ChatResponse(BaseModel):
    user_id: str
    reply:   str


class ErrorResponse(BaseModel):
    detail: str