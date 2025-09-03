from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from ..database.models import Booking, Session as SessionModel, Class, User
from ..schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingWithDetails,
    BookingList, BookingStats, BookingStatus
)
from ..config import settings

logger = logging.getLogger(__name__)


class BookingService:
    """Service layer for booking management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_booking(self, booking_data: BookingCreate, user_id: int) -> Booking:
        """Create a new booking"""
        logger.info(f"Creating booking for user {user_id}, session {booking_data.session_id}")
        
        # Verify session exists and is bookable
        session = self.db.query(SessionModel).filter(SessionModel.id == booking_data.session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        if session.status != "SCHEDULED":
            raise ValueError("Session is not available for booking")
        
        # Check if session is in the future
        if session.start_time <= datetime.utcnow():
            raise ValueError("Cannot book past sessions")
        
        # Check capacity
        current_bookings = self.get_session_booking_count(booking_data.session_id)
        if current_bookings >= session.class_obj.max_capacity:
            raise ValueError("Session is fully booked")
        
        # Check if user already has a booking for this session
        existing_booking = self.db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.session_id == booking_data.session_id,
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).first()
        
        if existing_booking:
            raise ValueError("User already has a booking for this session")
        
        # Check booking deadline (e.g., 2 hours before session)
        booking_deadline = session.start_time - timedelta(hours=2)
        if datetime.utcnow() > booking_deadline:
            raise ValueError("Booking deadline has passed")
        
        # Create booking
        db_booking = Booking(
            user_id=user_id,
            session_id=booking_data.session_id,
            notes=booking_data.notes,
            status=BookingStatus.PENDING,
            booking_date=datetime.utcnow()
        )
        
        self.db.add(db_booking)
        self.db.commit()
        self.db.refresh(db_booking)
        
        logger.info(f"Booking created successfully with ID: {db_booking.id}")
        return db_booking
    
    def get_booking(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID"""
        return self.db.query(Booking).filter(Booking.id == booking_id).first()
    
    def get_user_bookings(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[BookingStatus] = None,
        include_past: bool = True
    ) -> BookingList:
        """Get bookings for a specific user"""
        
        query = self.db.query(Booking).join(SessionModel).join(Class).filter(
            Booking.user_id == user_id
        )
        
        # Apply filters
        if status:
            query = query.filter(Booking.status == status)
        
        if not include_past:
            query = query.filter(SessionModel.start_time > datetime.utcnow())
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        bookings = query.order_by(SessionModel.start_time.desc()).offset(skip).limit(limit).all()
        
        # Build response with details
        booking_details = []
        for booking in bookings:
            booking_detail = BookingWithDetails(
                id=booking.id,
                session_id=booking.session_id,
                notes=booking.notes,
                user_id=booking.user_id,
                status=booking.status,
                booking_date=booking.booking_date,
                updated_at=booking.updated_at,
                admin_notes=booking.admin_notes,
                user_name=booking.user.name,
                user_email=booking.user.email,
                session_title=f"{booking.session.class_obj.name} - {booking.session.start_time.strftime('%Y-%m-%d %H:%M')}",
                session_date=booking.session.start_time,
                class_name=booking.session.class_obj.name
            )
            booking_details.append(booking_detail)
        
        return BookingList(
            bookings=booking_details,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0
        )
    
    def get_all_bookings(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[BookingStatus] = None,
        class_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BookingList:
        """Get all bookings with filters (admin function)"""
        
        query = self.db.query(Booking).join(SessionModel).join(Class).join(User)
        
        # Apply filters
        if status:
            query = query.filter(Booking.status == status)
        if class_id:
            query = query.filter(SessionModel.class_id == class_id)
        if start_date:
            query = query.filter(SessionModel.start_time >= start_date)
        if end_date:
            query = query.filter(SessionModel.start_time <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        bookings = query.order_by(Booking.booking_date.desc()).offset(skip).limit(limit).all()
        
        # Build response with details
        booking_details = []
        for booking in bookings:
            booking_detail = BookingWithDetails(
                id=booking.id,
                session_id=booking.session_id,
                notes=booking.notes,
                user_id=booking.user_id,
                status=booking.status,
                booking_date=booking.booking_date,
                updated_at=booking.updated_at,
                admin_notes=booking.admin_notes,
                user_name=booking.user.name,
                user_email=booking.user.email,
                session_title=f"{booking.session.class_obj.name} - {booking.session.start_time.strftime('%Y-%m-%d %H:%M')}",
                session_date=booking.session.start_time,
                class_name=booking.session.class_obj.name
            )
            booking_details.append(booking_detail)
        
        return BookingList(
            bookings=booking_details,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0
        )
    
    def update_booking(self, booking_id: int, booking_data: BookingUpdate, user_id: Optional[int] = None) -> Optional[Booking]:
        """Update booking (admin or user)"""
        logger.info(f"Updating booking {booking_id}")
        
        booking = self.get_booking(booking_id)
        if not booking:
            return None
        
        # If user_id provided, ensure user owns the booking (for user updates)
        if user_id and booking.user_id != user_id:
            raise ValueError("User can only update their own bookings")
        
        # Update fields
        update_data = booking_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        booking.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(booking)
        
        logger.info(f"Booking {booking_id} updated successfully")
        return booking
    
    def cancel_booking(self, booking_id: int, user_id: Optional[int] = None, reason: Optional[str] = None) -> bool:
        """Cancel a booking"""
        logger.info(f"Cancelling booking {booking_id}")
        
        booking = self.get_booking(booking_id)
        if not booking:
            return False
        
        # If user_id provided, ensure user owns the booking
        if user_id and booking.user_id != user_id:
            raise ValueError("User can only cancel their own bookings")
        
        # Check if cancellation is allowed (e.g., not too close to session time)
        session = booking.session
        cancellation_deadline = session.start_time - timedelta(hours=4)
        
        if datetime.utcnow() > cancellation_deadline and user_id:  # Admin can cancel anytime
            raise ValueError("Cancellation deadline has passed")
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.updated_at = datetime.utcnow()
        
        if reason:
            booking.admin_notes = f"{booking.admin_notes or ''}\nCancellation reason: {reason}"
        
        self.db.commit()
        
        logger.info(f"Booking {booking_id} cancelled successfully")
        return True
    
    def confirm_booking(self, booking_id: int) -> bool:
        """Confirm a pending booking (admin function)"""
        logger.info(f"Confirming booking {booking_id}")
        
        booking = self.get_booking(booking_id)
        if not booking:
            return False
        
        if booking.status != BookingStatus.PENDING:
            raise ValueError("Only pending bookings can be confirmed")
        
        booking.status = BookingStatus.CONFIRMED
        booking.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Booking {booking_id} confirmed successfully")
        return True
    
    def mark_attendance(self, booking_id: int, attended: bool) -> bool:
        """Mark attendance for a booking"""
        logger.info(f"Marking attendance for booking {booking_id}: {attended}")
        
        booking = self.get_booking(booking_id)
        if not booking:
            return False
        
        # Check if session has started or completed
        if booking.session.start_time > datetime.utcnow():
            raise ValueError("Cannot mark attendance for future sessions")
        
        booking.status = BookingStatus.COMPLETED if attended else BookingStatus.NO_SHOW
        booking.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Attendance marked for booking {booking_id}")
        return True
    
    def get_booking_stats(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> BookingStats:
        """Get booking statistics"""
        
        query = self.db.query(Booking)
        
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        
        bookings = query.all()
        
        total_bookings = len(bookings)
        confirmed_bookings = len([b for b in bookings if b.status == BookingStatus.CONFIRMED])
        cancelled_bookings = len([b for b in bookings if b.status == BookingStatus.CANCELLED])
        pending_bookings = len([b for b in bookings if b.status == BookingStatus.PENDING])
        completed_bookings = len([b for b in bookings if b.status == BookingStatus.COMPLETED])
        no_shows = len([b for b in bookings if b.status == BookingStatus.NO_SHOW])
        
        completion_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        no_show_rate = (no_shows / total_bookings * 100) if total_bookings > 0 else 0
        
        return BookingStats(
            total_bookings=total_bookings,
            confirmed_bookings=confirmed_bookings,
            cancelled_bookings=cancelled_bookings,
            pending_bookings=pending_bookings,
            completion_rate=completion_rate,
            no_show_rate=no_show_rate
        )
    
    def get_session_booking_count(self, session_id: int) -> int:
        """Get current booking count for a session"""
        return self.db.query(Booking).filter(
            Booking.session_id == session_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        ).count()
    
    def get_upcoming_user_bookings(self, user_id: int, limit: int = 5) -> List[BookingWithDetails]:
        """Get upcoming bookings for a user"""
        now = datetime.utcnow()
        
        bookings = self.db.query(Booking).join(SessionModel).join(Class).filter(
            Booking.user_id == user_id,
            SessionModel.start_time > now,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        ).order_by(SessionModel.start_time).limit(limit).all()
        
        booking_details = []
        for booking in bookings:
            booking_detail = BookingWithDetails(
                id=booking.id,
                session_id=booking.session_id,
                notes=booking.notes,
                user_id=booking.user_id,
                status=booking.status,
                booking_date=booking.booking_date,
                updated_at=booking.updated_at,
                admin_notes=booking.admin_notes,
                user_name=booking.user.name,
                user_email=booking.user.email,
                session_title=f"{booking.session.class_obj.name} - {booking.session.start_time.strftime('%Y-%m-%d %H:%M')}",
                session_date=booking.session.start_time,
                class_name=booking.session.class_obj.name
            )
            booking_details.append(booking_detail)
        
        return booking_details
    
    def check_booking_conflicts(self, user_id: int, session_id: int) -> bool:
        """Check if user has conflicting bookings"""
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return False
        
        # Check for overlapping sessions
        conflicting_bookings = self.db.query(Booking).join(SessionModel).filter(
            Booking.user_id == user_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            SessionModel.id != session_id,
            or_(
                and_(SessionModel.start_time <= session.start_time, SessionModel.end_time > session.start_time),
                and_(SessionModel.start_time < session.end_time, SessionModel.end_time >= session.end_time),
                and_(SessionModel.start_time >= session.start_time, SessionModel.end_time <= session.end_time)
            )
        ).first()
        
        return conflicting_bookings is not None