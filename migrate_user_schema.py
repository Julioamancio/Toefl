#!/usr/bin/env python3
"""
Database Migration Script for User Schema
Adds missing columns to the users table on Render.com deployment
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not found")
        sys.exit(1)
    return database_url

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except Exception as e:
        logger.error(f"Error checking column {column_name} in table {table_name}: {e}")
        return False

def migrate_user_schema():
    """Migrate the users table to add missing columns"""
    database_url = get_database_url()
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        logger.info("Starting user schema migration...")
        
        # Check if users table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'users' not in tables:
            logger.error("Users table does not exist!")
            return False
        
        # List of columns that should exist in the users table
        required_columns = [
            ('is_teacher', 'BOOLEAN DEFAULT FALSE'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('last_login', 'TIMESTAMP NULL')
        ]
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                for column_name, column_definition in required_columns:
                    if not check_column_exists(engine, 'users', column_name):
                        logger.info(f"Adding column {column_name} to users table...")
                        
                        # Add the column
                        sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"
                        conn.execute(text(sql))
                        
                        logger.info(f"Successfully added column {column_name}")
                    else:
                        logger.info(f"Column {column_name} already exists, skipping...")
                
                # Commit transaction
                trans.commit()
                logger.info("User schema migration completed successfully!")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"Error during migration, rolling back: {e}")
                return False
                
    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def verify_schema():
    """Verify that all required columns exist after migration"""
    database_url = get_database_url()
    
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        
        required_columns = ['id', 'username', 'email', 'password_hash', 'is_admin', 'is_teacher', 'is_active', 'created_at', 'last_login']
        existing_columns = [col['name'] for col in columns]
        
        logger.info("Current users table schema:")
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return False
        else:
            logger.info("All required columns are present!")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying schema: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== User Schema Migration Script ===")
    
    # First verify current schema
    logger.info("Checking current schema...")
    verify_schema()
    
    # Run migration
    success = migrate_user_schema()
    
    if success:
        logger.info("Migration completed successfully!")
        # Verify final schema
        logger.info("Verifying final schema...")
        verify_schema()
    else:
        logger.error("Migration failed!")
        sys.exit(1)