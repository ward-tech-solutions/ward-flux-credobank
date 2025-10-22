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

# PostgreSQL is now the default/required backend.
DATABASE_URL = os.getenv("DATABASE_URL")
ALLOW_SQLITE_FALLBACK = os.getenv("ALLOW_SQLITE_FALLBACK", "false").lower() == "true"

if not DATABASE_URL:
    if ALLOW_SQLITE_FALLBACK:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        DATABASE_URL = f"sqlite:///{data_dir}/ward_ops.db"
    else:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure a PostgreSQL connection string or set ALLOW_SQLITE_FALLBACK=true for legacy dev usage."
        )

USE_POSTGRES = DATABASE_URL.startswith("postgresql")

if not USE_POSTGRES:
    if not ALLOW_SQLITE_FALLBACK:
        raise RuntimeError(
            "SQLite fallback is disabled. Provide a PostgreSQL DATABASE_URL or explicitly opt-in by setting ALLOW_SQLITE_FALLBACK=true."
        )

# Create engine with appropriate configuration
# Connection pool sizing:
# - 50 Celery workers × 4 prefetch × 1.5 safety factor = 300 connections needed
# - pool_size: Base connections always open (100)
# - max_overflow: Additional connections on demand (200)
# - Total capacity: 300 connections
if USE_POSTGRES:
    engine = create_engine(
        DATABASE_URL,
        pool_size=100,              # Increased from 20 - base connection pool
        max_overflow=200,           # Increased from 40 - overflow connections
        pool_pre_ping=True,         # Test connections before use
        pool_recycle=1800,          # Recycle connections after 30min (was 1hr)
        pool_timeout=30,            # Wait max 30s for connection
        connect_args={
            'connect_timeout': 10,  # Connection timeout 10s
            'options': '-c statement_timeout=30000'  # Query timeout 30s
        },
        echo=False,
    )
else:
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
    region = Column(String(50), nullable=True)  # Legacy: For regional managers (single region)
    regions = Column(String(1000), nullable=True)  # JSON array of regions for multi-region support
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
        from models import Organization, SystemConfig, SetupWizardState, Device
    except ImportError:
        pass  # Models might not exist in older versions

    # Import monitoring models
    try:
        from monitoring.models import (
            MonitoringProfile,
            SNMPCredential,
            MonitoringTemplate,
            MonitoringItem,
            AlertRule,
            AlertHistory,
            DiscoveryRule,
            DiscoveryResult,
            MetricBaseline,
        )
    except ImportError:
        pass  # Monitoring models might not exist in older versions

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
