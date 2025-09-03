from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


class UserRole(str, Enum):
    """User role enumeration"""
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    role: UserRole = Field(default=UserRole.STUDENT, description="User role")


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="Password must be at least 8 characters with uppercase, lowercase, and digit"
    )
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name contains only letters and spaces"""
        if not re.match(r'^[a-zA-Z\s]+$', v.strip()):
            raise ValueError('Name must contain only letters and spaces')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate password confirmation matches"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)"""
    id: int = Field(..., description="User's unique identifier")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name if provided"""
        if v and not re.match(r'^[a-zA-Z\s]+$', v.strip()):
            raise ValueError('Name must contain only letters and spaces')
        return v.strip() if v else v


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="New password"
    )
    confirm_new_password: str = Field(..., description="New password confirmation")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password complexity"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        """Validate new password confirmation matches"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class TokenData(BaseModel):
    """Schema for token payload data"""
    email: Optional[str] = None
    user_id: Optional[int] = None


class UserList(BaseModel):
    """Schema for paginated user list response"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class ApiResponse(BaseModel):
    """Generic API response schema"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[dict] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(None, description="List of errors if any")