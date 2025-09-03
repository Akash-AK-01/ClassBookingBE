from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BookingStatus(str, Enum):
    """Booking status enumeration"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class BookingBase(BaseModel):
    """Base booking schema"""
    session_id: int = Field(..., description="ID of the session being booked")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes for the booking")


class BookingCreate(BookingBase):
    """Schema for creating a new booking"""
    pass


class BookingUpdate(BaseModel):
    """Schema for updating a booking"""
    status: Optional[BookingStatus] = None
    notes: Optional[str] = Field(None, max_length=500)
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Admin-only notes")


class BookingResponse(BookingBase):
    """Schema for booking response"""
    id: int = Field(..., description="Booking unique identifier")
    user_id: int = Field(..., description="ID of the user who made the booking")
    status: BookingStatus = Field(..., description="Current booking status")
    booking_date: datetime = Field(..., description="When the booking was made")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    admin_notes: Optional[str] = Field(None, description="Admin-only notes")
    
    class Config:
        from_attributes = True


class BookingWithDetails(BookingResponse):
    """Booking response with session and user details"""
    user_name: str = Field(..., description="Name of the user who made the booking")
    user_email: str = Field(..., description="Email of the user who made the booking")
    session_title: str = Field(..., description="Title of the booked session")
    session_date: datetime = Field(..., description="Date and time of the session")
    class_name: str = Field(..., description="Name of the class")


class BookingList(BaseModel):
    """Schema for paginated booking list"""
    bookings: List[BookingWithDetails] = Field(..., description="List of bookings")
    total: int = Field(..., description="Total number of bookings")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class BookingStats(BaseModel):
    """Schema for booking statistics"""
    total_bookings: int = Field(..., description="Total number of bookings")
    confirmed_bookings: int = Field(..., description="Number of confirmed bookings")
    cancelled_bookings: int = Field(..., description="Number of cancelled bookings")
    pending_bookings: int = Field(..., description="Number of pending bookings")
    completion_rate: float = Field(..., description="Booking completion rate as percentage")
    no_show_rate: float = Field(..., description="No-show rate as percentage")