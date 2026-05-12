from dotenv import load_dotenv
load_dotenv()

import uvicorn
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_level="info",
    )