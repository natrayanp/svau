from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

# SlowAPI (Rate Limiting)
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

# Import routes
from routes.auth import auth_routes, permission_routes, role_routes
from routes.system import db_analytics_routes

# Custom middleware
from utils.api.api_response_middleware import GlobalResponseMiddleware

# App initialization helpers (JWT manager, cleanup scheduler)
from utils.auth.auth_startup import initialize_app

# Models
#from models.health_models import HealthCheckResponse
from models.api_models import ErrorResponse

# Database Manager
from utils.database.database import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flashcard API",
    version="1.0.0",
    description="A RESTful API for managing flashcards and study sessions",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


# ---------------------------------------------------------
# ✅ SLOWAPI RATE LIMITING (Correct placement)
# ---------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )

# ---------------------------------------------------------
# ✅ ENVIRONMENT-BASED CORS CONFIGURATION
# ---------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "development":
    allow_origins = [
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
else:
    allow_origins = [
        "https://yourflashcardapp.com",
        "https://www.yourflashcardapp.com",
    ]

# ---------------------------------------------------------
# ✅ CUSTOM HTTP EXCEPTION HANDLER
# ---------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=str(exc.detail),
            error={
                "code": str(exc.status_code),
                "message": str(exc.detail),
                "details": {"exception_type": type(exc).__name__}
            }
        ).model_dump()
    )

# ---------------------------------------------------------
# ✅ GLOBAL RESPONSE WRAPPER
# ---------------------------------------------------------
app.add_middleware(GlobalResponseMiddleware)

# ---------------------------------------------------------
# ✅ ROUTES
# ---------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(permission_routes.router)
app.include_router(role_routes.router)
# app.include_router(db_analytics_routes)

# ---------------------------------------------------------
# ✅ CORS MIDDLEWARE (after SlowAPI + GlobalResponse)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# ---------------------------------------------------------
# ✅ INITIALIZE APP HELPERS (JWT manager, cleanup scheduler)
# ---------------------------------------------------------
initialize_app()

# ---------------------------------------------------------
# ✅ LOCAL DEVELOPMENT ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
