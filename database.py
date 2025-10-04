"""
Database models and configuration for User Authentication
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

# SQLite database (change to PostgreSQL for production)
DATABASE_URL = "sqlite:///./network_monitor.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    REGIONAL_MANAGER = "regional_manager"
    TECHNICIAN = "technician"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER)
    region = Column(String(50), nullable=True)  # For regional managers
    branches = Column(String(500), nullable=True)  # Comma-separated branch names
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

def init_db():
    """Initialize database and create default admin user"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
