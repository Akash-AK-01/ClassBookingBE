from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """Audit log action types"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    BOOKING_CREATED = "BOOKING_CREATED"
    BOOKING_CANCELLED = "BOOKING_CANCELLED"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_UPDATED = "SESSION_UPDATED"
    CLASS_CREATED = "CLASS_CREATED"
    CLASS_UPDATED = "CLASS_UPDATED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    ACCOUNT_ACTIVATED = "ACCOUNT_ACTIVATED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"


class EntityType(str, Enum):
    """Entity types for audit logging"""
    USER = "USER"
    CLASS = "CLASS"
    SESSION = "SESSION"
    BOOKING = "BOOKING"
    SYSTEM = "SYSTEM"


class AuditLogBase(BaseModel):
    """Base audit log schema"""
    action: ActionType = Field(..., description="Type of action performed")
    entity_type: EntityType = Field(..., description="Type of entity affected")
    entity_id: Optional[int] = Field(None, description="ID of the affected entity")
    details: Optional[dict] = Field(None, description="Additional details about the action")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User agent string")


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log entries"""
    user_id: Optional[int] = Field(None, description="ID of the user who performed the action")


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response"""
    id: int = Field(..., description="Audit log entry ID")
    user_id: Optional[int] = Field(None, description="ID of the user who performed the action")
    user_email: Optional[str] = Field(None, description="Email of the user who performed the action")
    timestamp: datetime = Field(..., description="When the action was performed")
    
    class Config:
        from_attributes = True


class AuditLogList(BaseModel):
    """Schema for paginated audit log list"""
    logs: List[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of log entries")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs"""
    user_id: Optional[int] = None
    action: Optional[ActionType] = None
    entity_type: Optional[EntityType] = None
    entity_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None


class SystemStats(BaseModel):
    """Schema for system statistics"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    total_classes: int = Field(..., description="Total number of classes")
    active_classes: int = Field(..., description="Number of active classes")
    total_sessions: int = Field(..., description="Total number of sessions")
    upcoming_sessions: int = Field(..., description="Number of upcoming sessions")
    total_bookings: int = Field(..., description="Total number of bookings")
    recent_activity: List[AuditLogResponse] = Field(..., description="Recent system activity")