"""Initial migration - Create users table

Revision ID: 001
Revises: 
Create Date: 2025-09-03 08:08:40.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

# Set up logging for migrations
migration_logger = logging.getLogger(__name__)

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create users table"""
    migration_logger.info("Starting migration 001 - Creating users table")
    
    # Create users table with enhanced schema
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='STUDENT'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    
    migration_logger.info("Migration 001 completed successfully")


def downgrade():
    """Drop users table"""
    migration_logger.info("Starting downgrade 001 - Dropping users table")
    
    # Drop indexes first
    op.drop_index(op.f('ix_users_is_active'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    
    # Drop table
    op.drop_table('users')
    
    migration_logger.info("Downgrade 001 completed successfully")
