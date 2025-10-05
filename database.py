"""
Database models and configuration for User Authentication
Supports both SQLite (development) and PostgreSQL (production)
"""
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# ============================================
# Database Configuration
# ============================================

# Check if PostgreSQL should be used
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Default to SQLite for development
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    DATABASE_URL = f"sqlite:///{data_dir}/ward_ops.db"
    USE_POSTGRES = False

# Create engine with appropriate configuration
if USE_POSTGRES or DATABASE_URL.startswith("postgresql"):
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,  # Connection pool size
        max_overflow=40,  # Max connections beyond pool_size
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging
    )
else:
    # SQLite configuration
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)

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

    # User Preferences
    theme_preference = Column(String(10), default="auto")  # 'light', 'dark', or 'auto'
    language = Column(String(10), default="en")  # Language preference
    timezone = Column(String(50), default="UTC")  # Timezone preference
    notifications_enabled = Column(Boolean, default=True)  # Email notifications
    dashboard_layout = Column(String(1000), nullable=True)  # JSON for custom dashboard


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


class MTRResult(Base):
    """MTR (My TraceRoute) monitoring results - stores continuous monitoring data"""

    __tablename__ = "mtr_results"

    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(50), index=True, nullable=False)
    device_name = Column(String(255))
    hop_number = Column(Integer, nullable=False)
    hop_ip = Column(String(50))
    hop_hostname = Column(String(255))

    # MTR-specific metrics
    packets_sent = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)
    packet_loss_percent = Column(Integer, default=0)

    # Latency statistics
    latency_avg = Column(Integer, nullable=True)  # Average latency in ms
    latency_min = Column(Integer, nullable=True)  # Best latency
    latency_max = Column(Integer, nullable=True)  # Worst latency
    latency_stddev = Column(Integer, nullable=True)  # Standard deviation (jitter)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class PerformanceBaseline(Base):
    """Performance baselines for devices - used for anomaly detection"""

    __tablename__ = "performance_baselines"

    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(50), index=True, nullable=False, unique=True)
    device_name = Column(String(255))

    # Baseline metrics (calculated from historical data)
    baseline_latency_avg = Column(Integer, nullable=True)  # Normal average latency
    baseline_latency_stddev = Column(Integer, nullable=True)  # Normal variation
    baseline_packet_loss = Column(Integer, default=0)  # Normal packet loss %

    # Thresholds for anomaly detection
    latency_warning_threshold = Column(Integer, nullable=True)  # Warning if exceeded
    latency_critical_threshold = Column(Integer, nullable=True)  # Critical if exceeded
    packet_loss_threshold = Column(Integer, default=5)  # Alert if loss > this %

    # Metadata
    samples_count = Column(Integer, default=0)  # Number of samples used for baseline
    last_calculated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    migrations_dir = "migrations"
    if os.path.exists(migrations_dir):
        if USE_POSTGRES or DATABASE_URL.startswith("postgresql"):
            # PostgreSQL migrations using SQLAlchemy connection
            from sqlalchemy import text

            db = SessionLocal()
            try:
                sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
                for sql_file in sql_files:
                    sql_path = os.path.join(migrations_dir, sql_file)
                    with open(sql_path, "r") as f:
                        sql_script = f.read()

                    # Convert SQLite-specific syntax to PostgreSQL if needed
                    sql_script = sql_script.replace("AUTOINCREMENT", "SERIAL")

                    try:
                        # Execute each statement separately for PostgreSQL
                        for statement in sql_script.split(";"):
                            if statement.strip():
                                db.execute(text(statement))
                        db.commit()
                    except Exception:
                        db.rollback()
                        pass  # Migration may already be applied
            finally:
                db.close()
        else:
            # SQLite migrations
            import sqlite3

            db_path = str(engine.url).replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
            for sql_file in sql_files:
                sql_path = os.path.join(migrations_dir, sql_file)
                with open(sql_path, "r") as f:
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
