"""
database.py - SQLAlchemy setup and models

Supports both SQLite (local dev) and PostgreSQL (production).
Set the DATABASE_URL environment variable to a PostgreSQL URL in production.
If DATABASE_URL is not set, falls back to local SQLite.
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Use DATABASE_URL env var in production (Render + Supabase), fallback to SQLite locally
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./coautomate.db")

# Supabase / Render provides 'postgres://' but SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs check_same_thread=False; PostgreSQL does not need it
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)         # Cell B5
    department = Column(String(255), nullable=False)        # Cell B6
    college = Column(String(255), nullable=False)           # Cell B7
    total_teaching_load = Column(String(50), nullable=False)# Cell I37
    term_school_year = Column(String(100), nullable=False)  # Cell J6
    signature_filename = Column(String(512), nullable=True) # e-signature file
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    period = Column(String(10), nullable=False)          # "1-15" or "16-31"
    month = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False)
    filename = Column(String(512), nullable=False)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
