from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from ..database.models import Session as SessionModel, Class, Booking, User
from ..schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, SessionWithDetails,
    SessionList, SessionBookingInfo, SessionAttendance, SessionStatus
)
from ..config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """Service layer for session management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, session_data: SessionCreate, created_by: int) -> SessionModel:
        """Create a new session"""
        logger.info(f"Creating new session for class {session_data.class_id}")
        
        # Verify class exists
        class_obj = self.db.query(Class).filter(Class.id == session_data.class_id).first()
        if not class_obj:
            raise ValueError("Class not found")
        
        # Check for scheduling conflicts
        conflicts = self.check_scheduling_conflicts(
            session_data.start_time, 
            session_data.end_time,
            session_data.location
        )
        if conflicts:
            raise ValueError("Session conflicts with existing sessions")
        
        # Create session
        db_session = SessionModel(
            class_id=session_data.class_id,
            start_time=session_data.start_time,
            end_time=session_data.end_time,
            location=session_data.location,
            special_notes=session_data.special_notes,
            status=SessionStatus.SCHEDULED,
            created_by=created_by
        )
        
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        
        logger.info(f"Session created successfully with ID: {db_session.id}")
        return db_session
    
    def get_session(self, session_id: int) -> Optional[SessionModel]:
        """Get session by ID"""
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    def get_sessions_with_details(
        self, 
        skip: int = 0, 
        limit: int = 100,
        class_id: Optional[int] = None,
        status: Optional[SessionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> SessionList:
        """Get sessions with class details and pagination"""
        
        query = self.db.query(SessionModel).join(Class)
        
        # Apply filters
        if class_id:
            query = query.filter(SessionModel.class_id == class_id)
        if status:
            query = query.filter(SessionModel.status == status)
        if start_date:
            query = query.filter(SessionModel.start_time >= start_date)
        if end_date:
            query = query.filter(SessionModel.start_time <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        sessions = query.order_by(SessionModel.start_time).offset(skip).limit(limit).all()
        
        # Build response with details
        session_details = []
        for session in sessions:
            current_bookings = self.get_session_booking_count(session.id)
            available_spots = session.class_obj.max_capacity - current_bookings
            
            session_detail = SessionWithDetails(
                id=session.id,
                class_id=session.class_id,
                start_time=session.start_time,
                end_time=session.end_time,
                location=session.location,
                special_notes=session.special_notes,
                status=session.status,
                current_bookings=current_bookings,
                max_capacity=session.class_obj.max_capacity,
                available_spots=available_spots,
                created_at=session.created_at,
                updated_at=session.updated_at,
                class_name=session.class_obj.name,
                class_category=session.class_obj.category,
                instructor_name=session.class_obj.instructor_name,
                price=session.class_obj.price,
                duration_minutes=session.class_obj.duration_minutes
            )
            session_details.append(session_detail)
        
        return SessionList(
            sessions=session_details,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0
        )
    
    def update_session(self, session_id: int, session_data: SessionUpdate) -> Optional[SessionModel]:
        """Update session"""
        logger.info(f"Updating session {session_id}")
        
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Check for conflicts if time is being changed
        if session_data.start_time or session_data.end_time:
            start_time = session_data.start_time or session.start_time
            end_time = session_data.end_time or session.end_time
            
            conflicts = self.check_scheduling_conflicts(
                start_time, end_time, session_data.location or session.location, session_id
            )
            if conflicts:
                raise ValueError("Updated session conflicts with existing sessions")
        
        # Update fields
        update_data = session_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(session, field, value)
        
        session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Session {session_id} updated successfully")
        return session
    
    def cancel_session(self, session_id: int, reason: Optional[str] = None) -> bool:
        """Cancel a session and handle bookings"""
        logger.info(f"Cancelling session {session_id}")
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Update session status
        session.status = SessionStatus.CANCELLED
        session.special_notes = f"{session.special_notes or ''}\nCancelled: {reason or 'No reason provided'}"
        session.updated_at = datetime.utcnow()
        
        # Cancel all bookings for this session
        bookings = self.db.query(Booking).filter(
            Booking.session_id == session_id,
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).all()
        
        for booking in bookings:
            booking.status = "CANCELLED"
            booking.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Session {session_id} cancelled, {len(bookings)} bookings cancelled")
        return True
    
    def get_upcoming_sessions(self, limit: int = 10) -> List[SessionBookingInfo]:
        """Get upcoming bookable sessions"""
        now = datetime.utcnow()
        
        sessions = self.db.query(SessionModel).join(Class).filter(
            SessionModel.start_time > now,
            SessionModel.status == SessionStatus.SCHEDULED
        ).order_by(SessionModel.start_time).limit(limit).all()
        
        session_info = []
        for session in sessions:
            current_bookings = self.get_session_booking_count(session.id)
            available_spots = session.class_obj.max_capacity - current_bookings
            
            # Calculate booking deadline (e.g., 2 hours before session)
            booking_deadline = session.start_time - timedelta(hours=2)
            is_bookable = now < booking_deadline and available_spots > 0
            
            info = SessionBookingInfo(
                session_id=session.id,
                session_title=f"{session.class_obj.name} - {session.start_time.strftime('%Y-%m-%d %H:%M')}",
                start_time=session.start_time,
                available_spots=available_spots,
                is_bookable=is_bookable,
                booking_deadline=booking_deadline
            )
            session_info.append(info)
        
        return session_info
    
    def get_session_attendance(self, session_id: int) -> Optional[SessionAttendance]:
        """Get attendance statistics for a session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        bookings = self.db.query(Booking).filter(Booking.session_id == session_id).all()
        
        total_bookings = len(bookings)
        attended = len([b for b in bookings if b.status == "COMPLETED"])
        no_shows = len([b for b in bookings if b.status == "NO_SHOW"])
        
        attendance_rate = (attended / total_bookings * 100) if total_bookings > 0 else 0
        
        return SessionAttendance(
            session_id=session_id,
            total_bookings=total_bookings,
            attended=attended,
            no_shows=no_shows,
            attendance_rate=attendance_rate
        )
    
    def check_scheduling_conflicts(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        location: Optional[str] = None,
        exclude_session_id: Optional[int] = None
    ) -> List[SessionModel]:
        """Check for scheduling conflicts"""
        
        query = self.db.query(SessionModel).filter(
            SessionModel.status.in_([SessionStatus.SCHEDULED, SessionStatus.ONGOING]),
            or_(
                and_(SessionModel.start_time <= start_time, SessionModel.end_time > start_time),
                and_(SessionModel.start_time < end_time, SessionModel.end_time >= end_time),
                and_(SessionModel.start_time >= start_time, SessionModel.end_time <= end_time)
            )
        )
        
        if location:
            query = query.filter(SessionModel.location == location)
        
        if exclude_session_id:
            query = query.filter(SessionModel.id != exclude_session_id)
        
        return query.all()
    
    def get_session_booking_count(self, session_id: int) -> int:
        """Get current booking count for a session"""
        return self.db.query(Booking).filter(
            Booking.session_id == session_id,
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).count()
    
    def get_sessions_by_class(self, class_id: int, include_past: bool = False) -> List[SessionModel]:
        """Get all sessions for a specific class"""
        query = self.db.query(SessionModel).filter(SessionModel.class_id == class_id)
        
        if not include_past:
            query = query.filter(SessionModel.start_time > datetime.utcnow())
        
        return query.order_by(SessionModel.start_time).all()
    
    def mark_session_completed(self, session_id: int) -> bool:
        """Mark a session as completed"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.COMPLETED
        session.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Session {session_id} marked as completed")
        return True