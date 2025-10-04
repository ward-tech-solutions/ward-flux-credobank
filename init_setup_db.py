"""
WARD TECH SOLUTIONS - Initialize Setup Database
Creates tables for multi-tenant setup wizard
"""
from database import engine, Base, User
from models import Organization, SystemConfig, SetupWizardState

def init_setup_tables():
    """Create all setup-related tables"""
    print("Creating setup wizard tables...")

    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)

    print("✅ Setup tables created successfully!")
    print("\nTables created:")
    print("  - organizations")
    print("  - system_config")
    print("  - setup_wizard_state")
    print("  - users")

if __name__ == "__main__":
    init_setup_tables()
