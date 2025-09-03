from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration"""
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class SessionBase(BaseModel):
    """Base session schema"""
    class_id: int = Field(..., description="ID of the class this session belongs to")
    start_time: datetime = Field(..., description="Session start date and time")
    end_time: datetime = Field(..., description="Session end date and time")
    location: Optional[str] = Field(None, max_length=200, description="Session location")
    special_notes: Optional[str] = Field(None, max_length=500, description="Special notes for this session")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate end time is after start time"""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class SessionCreate(SessionBase):
    """Schema for creating a new session"""
    pass


class SessionUpdate(BaseModel):
    """Schema for updating a session"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    special_notes: Optional[str] = Field(None, max_length=500)
    status: Optional[SessionStatus] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate end time is after start time if both provided"""
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class SessionResponse(SessionBase):
    """Schema for session response"""
    id: int = Field(..., description="Session unique identifier")
    status: SessionStatus = Field(..., description="Session status")
    current_bookings: int = Field(0, description="Current number of bookings")
    max_capacity: int = Field(..., description="Maximum capacity from class")
    available_spots: int = Field(..., description="Available booking spots")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SessionWithDetails(SessionResponse):
    """Session response with class details"""
    class_name: str = Field(..., description="Name of the class")
    class_category: str = Field(..., description="Class category")
    instructor_name: str = Field(..., description="Instructor name")
    price: float = Field(..., description="Session price")
    duration_minutes: int = Field(..., description="Session duration in minutes")


class SessionList(BaseModel):
    """Schema for paginated session list"""
    sessions: List[SessionWithDetails] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class SessionBookingInfo(BaseModel):
    """Schema for session booking information"""
    session_id: int = Field(..., description="Session ID")
    session_title: str = Field(..., description="Session title")
    start_time: datetime = Field(..., description="Session start time")
    available_spots: int = Field(..., description="Available spots")
    is_bookable: bool = Field(..., description="Whether session can be booked")
    booking_deadline: Optional[datetime] = Field(None, description="Last time to book")


class SessionAttendance(BaseModel):
    """Schema for session attendance tracking"""
    session_id: int = Field(..., description="Session ID")
    total_bookings: int = Field(..., description="Total bookings")
    attended: int = Field(..., description="Number who attended")
    no_shows: int = Field(..., description="Number of no-shows")
    attendance_rate: float = Field(..., description="Attendance rate as percentage")