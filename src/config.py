import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:1988@localhost:5432/class_booking")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security settings
    MIN_PASSWORD_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    
    # Database settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

