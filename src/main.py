from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database.base import get_db, engine, Base
from .database.models import User
from .schemas import UserCreate, UserLogin, Token, UserResponse
from .auth import authenticate_user, create_access_token, get_password_hash
from datetime import timedelta
from .config import settings, logger
import logging

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Class Booking API", 
    version="1.0.0",
    description="A comprehensive class booking system with user management"
)

# Set up logging for this module
app_logger = logging.getLogger(__name__)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    app_logger.info(f"Registration attempt for email: {user.email}")
    
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        app_logger.warning(f"Registration failed - email already exists: {user.email}")
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
   
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hashed_password,
        role=user.role.upper()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    app_logger.info(f"User registered successfully: {user.email} with role {user.role}")
    return db_user

@app.post("/api/v1/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    app_logger.info(f"Login attempt for email: {user_credentials.email}")
    
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        app_logger.warning(f"Failed login attempt for email: {user_credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    app_logger.info(f"User logged in successfully: {user_credentials.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# @
# @get students 
# @get admin data

@app.get("/")
async def root():
    app_logger.info("Root endpoint accessed")
    return {"message": "Class Booking API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify database connectivity"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        app_logger.info("Health check passed - database connection OK")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": timedelta()
        }
    except Exception as e:
        app_logger.error(f"Health check failed - database error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user(db: Session = Depends(get_db)):
    # For now, return a dummy response - you can implement JWT validation later
    return {"id": 1, "email": "test@example.com", "name": "Test User", "role": "ADMIN", "is_active": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)



