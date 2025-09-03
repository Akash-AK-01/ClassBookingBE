from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .database.models import User
from .config import settings
import logging
import re

# Set up logging for this module
auth_logger = logging.getLogger(__name__)

# Custom exceptions
class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass

class PasswordValidationError(Exception):
    """Raised when password doesn't meet requirements"""
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def validate_password(password: str) -> bool:
    """Validate password meets security requirements"""
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long")
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        raise PasswordValidationError("Password must contain at least one uppercase letter")
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        raise PasswordValidationError("Password must contain at least one lowercase letter")
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        raise PasswordValidationError("Password must contain at least one digit")
    
    return True

def get_password_hash(password: str) -> str:
    """Hash password after validation"""
    validate_password(password)
    auth_logger.info("Password validated and hashed successfully")
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user with enhanced logging and security checks"""
    auth_logger.info(f"Authentication attempt for user: {email}")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        auth_logger.warning(f"Authentication failed - user not found: {email}")
        return False
    
    if not user.is_active:
        auth_logger.warning(f"Authentication failed - user account disabled: {email}")
        return False
    
    if not verify_password(password, user.password_hash):
        auth_logger.warning(f"Authentication failed - invalid password for user: {email}")
        return False
    
    auth_logger.info(f"Authentication successful for user: {email}")
    return user

def get_current_user_from_token(token: str, db: Session):
    """Extract and validate user from JWT token with enhanced error handling"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            auth_logger.warning("Token validation failed - no email in payload")
            raise AuthenticationError("Invalid token payload")
            
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            auth_logger.warning(f"Token expired for user: {email}")
            raise AuthenticationError("Token expired")
            
    except JWTError as e:
        auth_logger.warning(f"JWT decode error: {str(e)}")
        raise AuthenticationError("Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        auth_logger.warning(f"Token validation failed - user not found: {email}")
        raise AuthenticationError("User not found")
        
    if not user.is_active:
        auth_logger.warning(f"Token validation failed - user account disabled: {email}")
        raise AuthenticationError("Account disabled")
    
    auth_logger.debug(f"Token validation successful for user: {email}")
    return user
