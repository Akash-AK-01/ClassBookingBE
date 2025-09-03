from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, time
from enum import Enum


class ClassStatus(str, Enum):
    """Class status enumeration"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ClassCategory(str, Enum):
    """Class category enumeration"""
    FITNESS = "FITNESS"
    YOGA = "YOGA"
    DANCE = "DANCE"
    MARTIAL_ARTS = "MARTIAL_ARTS"
    SPORTS = "SPORTS"
    WELLNESS = "WELLNESS"
    OTHER = "OTHER"


class ClassBase(BaseModel):
    """Base class schema"""
    name: str = Field(..., min_length=2, max_length=100, description="Class name")
    description: Optional[str] = Field(None, max_length=1000, description="Class description")
    category: ClassCategory = Field(..., description="Class category")
    duration_minutes: int = Field(..., ge=15, le=480, description="Class duration in minutes")
    max_capacity: int = Field(..., ge=1, le=100, description="Maximum number of participants")
    price: float = Field(..., ge=0, description="Class price")
    instructor_name: str = Field(..., min_length=2, max_length=100, description="Instructor name")


class ClassCreate(ClassBase):
    """Schema for creating a new class"""
    pass


class ClassUpdate(BaseModel):
    """Schema for updating a class"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[ClassCategory] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    max_capacity: Optional[int] = Field(None, ge=1, le=100)
    price: Optional[float] = Field(None, ge=0)
    instructor_name: Optional[str] = Field(None, min_length=2, max_length=100)
    status: Optional[ClassStatus] = None


class ClassResponse(ClassBase):
    """Schema for class response"""
    id: int = Field(..., description="Class unique identifier")
    status: ClassStatus = Field(..., description="Class status")
    created_at: datetime = Field(..., description="Class creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    total_sessions: int = Field(0, description="Total number of sessions for this class")
    active_sessions: int = Field(0, description="Number of active sessions")
    
    class Config:
        from_attributes = True


class ClassWithStats(ClassResponse):
    """Class response with booking statistics"""
    total_bookings: int = Field(0, description="Total bookings across all sessions")
    average_attendance: float = Field(0.0, description="Average attendance rate")
    revenue: float = Field(0.0, description="Total revenue generated")


class ClassList(BaseModel):
    """Schema for paginated class list"""
    classes: List[ClassWithStats] = Field(..., description="List of classes")
    total: int = Field(..., description="Total number of classes")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class ClassSchedule(BaseModel):
    """Schema for class schedule information"""
    class_id: int = Field(..., description="Class ID")
    class_name: str = Field(..., description="Class name")
    upcoming_sessions: List[dict] = Field(..., description="List of upcoming sessions")
    next_available_slot: Optional[datetime] = Field(None, description="Next available booking slot")