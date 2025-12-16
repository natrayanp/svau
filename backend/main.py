from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

# Rate Limiting
from slowapi.middleware import SlowAPIMiddleware
from utils.appwide.rate_limiter import limiter

# Routes
from routes.auth import auth_routes, permission_routes, role_routes

# Middleware
from utils.api.api_response_middleware import GlobalResponseMiddleware

# App initialization helpers
from utils.auth.auth_startup import initialize_app

# Models
from models.api_models import ErrorResponse

# Async DB Manager
from utils.database.database import get_db_manager


# ---------------------------------------------------------
# ✅ ENVIRONMENT SETUP
# ---------------------------------------------------------
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flashcard API",
    version="1.0.0",
    description="A RESTful API for managing flashcards and study sessions",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# ---------------------------------------------------------
# ✅ RATE LIMITING (SlowAPI)
# ---------------------------------------------------------
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# ---------------------------------------------------------
# ✅ CORS CONFIGURATION
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


# ---------------------------------------------------------
# ✅ GLOBAL RESPONSE WRAPPER
# ---------------------------------------------------------
app.add_middleware(GlobalResponseMiddleware)


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
                "details": {"exception_type": type(exc).__name__},
            },
        ).model_dump(),
    )


# ---------------------------------------------------------
# ✅ ROUTES
# ---------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(permission_routes.router)
#app.include_router(role_routes.router)
# app.include_router(db_analytics_routes)


# ---------------------------------------------------------
# ✅ STARTUP: Initialize Async DB + JWT Manager
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting Flashcard API...")

    # Initialize async DB pools
    db = get_db_manager()
    await db.connect()
    logger.info("✅ Database connected")

    # Initialize JWT manager, cleanup scheduler, etc.
    initialize_app()
    logger.info("✅ App helpers initialized")


# ---------------------------------------------------------
# ✅ SHUTDOWN: Close DB Pools
# ---------------------------------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down Flashcard API...")

    db = get_db_manager()
    await db.close()

    logger.info("✅ Database pools closed")


# ---------------------------------------------------------
# ✅ LOCAL DEVELOPMENT ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
