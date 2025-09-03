from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from ..database.models import User, Booking, Session as SessionModel
from ..schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserList, PasswordChange, UserRole
)
from ..auth import get_password_hash, verify_password, AuthenticationError
from ..config import settings

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        logger.info(f"Creating new user with email: {user_data.email}")
        
        # Check if user already exists
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            password_hash=hashed_password,
            role=user_data.role.upper(),
            is_active=True
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"User created successfully with ID: {db_user.id}")
        return db_user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> UserList:
        """Get users with pagination and filters"""
        
        query = self.db.query(User)
        
        # Apply filters
        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            query = query.filter(
                User.name.ilike(f"%{search}%") | 
                User.email.ilike(f"%{search}%")
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        user_responses = [
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login
            ) for user in users
        ]
        
        return UserList(
            users=user_responses,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0
        )
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        logger.info(f"Updating user {user_id}")
        
        user = self.get_user(user_id)
        if not user:
            return None
        
        # Check if email is being changed and if it's already taken
        if user_data.email and user_data.email != user.email:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise ValueError("Email already in use by another user")
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User {user_id} updated successfully")
        return user
    
    def change_password(self, user_id: int, password_data: PasswordChange) -> bool:
        """Change user password"""
        logger.info(f"Changing password for user {user_id}")
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Verify current password
        if not verify_password(password_data.current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        
        # Hash new password
        new_password_hash = get_password_hash(password_data.new_password)
        
        # Update password
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Password changed successfully for user {user_id}")
        return True
    
    def activate_user(self, user_id: int) -> bool:
        """Activate a user account"""
        logger.info(f"Activating user {user_id}")
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User {user_id} activated successfully")
        return True
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account"""
        logger.info(f"Deactivating user {user_id}")
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Cancel all future bookings for this user
        future_bookings = self.db.query(Booking).join(SessionModel).filter(
            Booking.user_id == user_id,
            SessionModel.start_time > datetime.utcnow(),
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).all()
        
        for booking in future_bookings:
            booking.status = "CANCELLED"
            booking.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"User {user_id} deactivated, {len(future_bookings)} bookings cancelled")
        return True
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        # Get booking statistics
        total_bookings = self.db.query(Booking).filter(Booking.user_id == user_id).count()
        
        completed_bookings = self.db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.status == "COMPLETED"
        ).count()
        
        cancelled_bookings = self.db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.status == "CANCELLED"
        ).count()
        
        upcoming_bookings = self.db.query(Booking).join(SessionModel).filter(
            Booking.user_id == user_id,
            SessionModel.start_time > datetime.utcnow(),
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).count()
        
        return {
            "user_id": user_id,
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "upcoming_bookings": upcoming_bookings,
            "completion_rate": (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0,
            "member_since": user.created_at,
            "last_activity": user.last_login
        }
    
    def get_admin_users(self) -> List[User]:
        """Get all admin users"""
        return self.db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.is_active == True
        ).all()
    
    def promote_to_admin(self, user_id: int) -> bool:
        """Promote user to admin role"""
        logger.info(f"Promoting user {user_id} to admin")
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.role = UserRole.ADMIN
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User {user_id} promoted to admin successfully")
        return True
    
    def demote_from_admin(self, user_id: int) -> bool:
        """Demote admin user to student role"""
        logger.info(f"Demoting user {user_id} from admin")
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.role = UserRole.STUDENT
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User {user_id} demoted from admin successfully")
        return True
    
    def search_users(self, query: str, limit: int = 10) -> List[UserResponse]:
        """Search users by name or email"""
        users = self.db.query(User).filter(
            User.name.ilike(f"%{query}%") | User.email.ilike(f"%{query}%"),
            User.is_active == True
        ).limit(limit).all()
        
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login
            ) for user in users
        ]
    
    def get_recent_users(self, limit: int = 10) -> List[UserResponse]:
        """Get recently registered users"""
        users = self.db.query(User).order_by(
            User.created_at.desc()
        ).limit(limit).all()
        
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login
            ) for user in users
        ]
