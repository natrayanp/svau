from fastapi import FastAPI, HTTPException, Depends, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
import os
from dotenv import load_dotenv

# UPDATED IMPORTS - Add role_routes
from routes.auth import auth_routes, user_routes, permission_routes, role_routes

from models import (
    Flashcard, FlashcardCreate, FlashcardUpdate, Deck, DeckCreate, DeckUpdate,
    StudySessionCreate, StudySessionResponse, HealthCheckResponse,
    SuccessResponse, ErrorResponse, Difficulty
)
from backend.utils.database import Database

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

# Environment-based CORS configuration
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# Database dependency
def get_db():
    db = Database()
    try:
        yield db
    finally:
        pass

# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_type=type(exc).__name__
        ).model_dump()
    )

# Health check endpoints
@app.get("/", response_model=HealthCheckResponse, tags=["Health"])
async def root():
    return HealthCheckResponse(
        status="healthy",
        database="PostgreSQL"
    )

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(db: Database = Depends(get_db)):
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return HealthCheckResponse(
            status="healthy",
            database="connected"
        )
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

# UPDATED: Mount all auth routes including the new role_routes
app.include_router(auth_routes.router)
app.include_router(user_routes.router)  
app.include_router(permission_routes.router)
app.include_router(role_routes.router)  # NEW: Add role management routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)