"""
Database models and configuration for User Authentication
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

# SQLite database (change to PostgreSQL for production)
# Use data directory for Docker volume persistence
import os
data_dir = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(data_dir, exist_ok=True)
DATABASE_URL = f"sqlite:///{data_dir}/ward_ops.db"

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
    organization_id = Column(Integer, nullable=True)  # For multi-tenant support
    is_superuser = Column(Boolean, default=False)  # For admin users
    region = Column(String(50), nullable=True)  # For regional managers
    branches = Column(String(500), nullable=True)  # Comma-separated branch names
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class PingResult(Base):
    """Independent ping check results"""
    __tablename__ = "ping_results"

    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(50), index=True, nullable=False)
    device_name = Column(String(255))
    packets_sent = Column(Integer, default=5)
    packets_received = Column(Integer, default=0)
    packet_loss_percent = Column(Integer, default=100)
    min_rtt_ms = Column(Integer, nullable=True)
    avg_rtt_ms = Column(Integer, nullable=True)
    max_rtt_ms = Column(Integer, nullable=True)
    is_reachable = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class TracerouteResult(Base):
    """Network path traceroute results"""
    __tablename__ = "traceroute_results"

    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(50), index=True, nullable=False)
    device_name = Column(String(255))
    hop_number = Column(Integer, nullable=False)
    hop_ip = Column(String(50))
    hop_hostname = Column(String(255))
    latency_ms = Column(Integer, nullable=True)
    packet_loss = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

def init_db():
    """Initialize database and create all tables"""
    # Import all models to ensure they're registered with Base
    try:
        from models import Organization, SystemConfig, SetupWizardState
    except ImportError:
        pass  # Models might not exist in older versions

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Run SQL migrations for georgian_cities and other custom tables
    import sqlite3
    import os

    migrations_dir = "migrations"
    if os.path.exists(migrations_dir):
        db_path = str(engine.url).replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        for sql_file in sql_files:
            sql_path = os.path.join(migrations_dir, sql_file)
            with open(sql_path, 'r') as f:
                sql_script = f.read()
            try:
                cursor.executescript(sql_script)
                conn.commit()
            except Exception:
                pass  # Migration may already be applied

        conn.close()

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
