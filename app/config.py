import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH, override=True)


class Settings:
    APP_HOST: str  = os.getenv("APP_HOST",  "0.0.0.0")
    APP_PORT: int  = int(os.getenv("APP_PORT", 8000))
    APP_ENV: str   = os.getenv("APP_ENV",   "development")
    DEBUG: bool    = APP_ENV == "development"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # JWT secret — auto-generated if not set, but set it in .env for persistence
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "hp-dev-secret-change-me-in-production-32chars"
    )

    BASE_DIR: Path    = Path(__file__).resolve().parent.parent
    DATA_DIR: Path    = BASE_DIR / "data"
    MODELS_DIR: Path  = BASE_DIR / "app" / "models"

    MODEL_LSTM_PATH: str = str(MODELS_DIR / "lstm_model.keras")
    MODEL_XGB_PATH: str  = str(MODELS_DIR / "xgb_model.json")
    SCALER_PATH: str     = str(MODELS_DIR / "scaler.joblib")

    SEQUENCE_LENGTH: int  = 30
    ACTIVITY_LABELS: list = ["low", "medium", "high"]

    def validate(self) -> None:
        if not self.OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY not set — /chat will not work")


settings = Settings()
