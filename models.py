"""
WARD TECH SOLUTIONS - Database Models
Multi-tenant configuration support
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class Organization(Base):
    """Organization/Company configuration"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=True)

    # Zabbix Configuration
    zabbix_url = Column(String(500), nullable=False)
    zabbix_user = Column(String(255), nullable=False)
    zabbix_password = Column(String(255), nullable=False)

    # Selected host groups (JSON array of group IDs)
    monitored_groups = Column(JSON, default=list)

    # Company Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#5EBBA8")

    # Status
    is_active = Column(Boolean, default=True)
    is_setup_complete = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemConfig(Base):
    """System-wide configuration settings"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SetupWizardState(Base):
    """Track setup wizard progress"""
    __tablename__ = "setup_wizard_state"

    id = Column(Integer, primary_key=True, index=True)

    # Setup steps
    step_1_welcome = Column(Boolean, default=False)
    step_2_zabbix = Column(Boolean, default=False)
    step_3_groups = Column(Boolean, default=False)
    step_4_admin = Column(Boolean, default=False)
    step_5_complete = Column(Boolean, default=False)

    # Overall status
    is_complete = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Note: User model is defined in database.py
# We import it in setup_wizard.py when needed
