# ClassBookings Backend API

A FastAPI-based backend for class booking system with PostgreSQL database and Alembic migrations.

## Features

- **FastAPI** framework with automatic API documentation
- **PostgreSQL** database with SQLAlchemy ORM
- **Alembic** database migrations
- **JWT Authentication** with bcrypt password hashing
- **User Management** (Students and Admins)
- **CORS** configured for frontend integration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

#### PostgreSQL (Production/Interview)
```bash
# Create database
createdb classbookings

# Copy environment file and configure
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

#### SQLite (Local Development Alternative)
```bash
# Uncomment SQLite URL in .env file
# DATABASE_URL=sqlite:///./classbookings.db
```

### 3. Run Migrations

```bash
# Initialize Alembic (already done)
# alembic init migrations

# Run migrations to create tables
alembic upgrade head

# Create new migration (when models change)
alembic revision --autogenerate -m "Description of changes"
```

### 4. Start Server

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

## API Endpoints

- **POST** `/api/v1/auth/register` - User registration
- **POST** `/api/v1/auth/login` - User login
- **GET** `/docs` - Interactive API documentation
- **GET** `/redoc` - Alternative API documentation

## Database Schema

### Users Table
- `id` (Primary Key)
- `email` (Unique, Indexed)
- `name`
- `password_hash`
- `role` (STUDENT/ADMIN)
- `is_active`
- `created_at`
- `updated_at`

## Migration Commands Reference

```bash
# Check current migration status
alembic current

# Show migration history
alembic history

# Upgrade to latest migration
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Generate new migration from model changes
alembic revision --autogenerate -m "Add new table"

# Create empty migration file
alembic revision -m "Custom migration"
```

## Development

### Project Structure
```
ClassBookings_BE/
├── alembic.ini  # Configuration file for Alembic, a migration tool for SQLAlchemy
├── README.md  # Project documentation
├── requirements-dev.txt  # List of dependencies required for development
├── requirements.txt  # List of dependencies required for production
├── migrations/  # Directory for database migrations
│   ├── .gitkeep  # Empty file to keep the directory in Git
│   ├── 001_initial_migration.py  # Initial migration script
│   └── env.py  # Environment configuration for migrations
└── src/  # Source code directory
    ├── auth.py  # Authentication module
    ├── config.py  # Configuration module
    ├── main.py  # Main application entry point
    ├── schemas.py  # Schema definitions for API endpoints
    ├── api/  # API endpoints directory
    │   ├── dependencies.py  # Dependency injection module for API endpoints
    │   └── routes/  # API endpoint routes directory
    │       ├── admin.py  # Admin API endpoint routes
    │       ├── auth.py  # Authentication API endpoint routes
    │       ├── bookings.py  # Booking API endpoint routes
    │       ├── classes.py  # Class API endpoint routes
    │       └── sessions.py  # Session API endpoint routes
    ├── core/  # Core application logic directory
    │   ├── rules.py  # Business logic rules
    │   └── security.py  # Security-related logic
    ├── database/  # Database interaction directory
    │   ├── base.py  # Base database model
    │   └── models.py  # Database models
    ├── schemas/  # Schema definitions for database models
    │   ├── audit_log.py  # Audit log schema
    │   ├── booking.py  # Booking schema
    │   ├── class.py  # Class schema
    │   ├── session.py  # Session schema
    │   └── user.py  # User schema
    ├── services/  # Service layer directory
    │   ├── booking_service.py  # Booking service
    │   ├── session_service.py  # Session service
    │   └── user_service.py  # User service
    └── utils/  # Utility functions directory
        └── logger.py  # Logging utility

### Environment Variables
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/classbookings
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src
```
