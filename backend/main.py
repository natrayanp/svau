from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

# Import routes
from routes.auth import auth_routes, permission_routes, role_routes
from routes.system import db_analytics_routes

#from models import HealthCheckResponse, ErrorResponse
from utils.database.database import DatabaseManager  # Import the actual class

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
'''
# Health check endpoint
@app.get("/", response_model=HealthCheckResponse, tags=["Health"])
async def root():
    return HealthCheckResponse(
        status="healthy",
        database="PostgreSQL"
    )

# Health check with database connection test
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    try:
        # Use DatabaseManager directly - no dependency injection needed here
        db = DatabaseManager()
        is_healthy = db.health_check()
        
        return HealthCheckResponse(
            status="healthy" if is_healthy else "unhealthy",
            database="connected" if is_healthy else "disconnected"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            database="connection failed"
        )
'''

# Mount all routes
app.include_router(auth_routes.router)
#app.include_router(user_routes.router)  
app.include_router(permission_routes.router)
app.include_router(role_routes.router)
#app.include_router(db_analytics_routes)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)