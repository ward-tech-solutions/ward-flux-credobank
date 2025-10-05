"""Initialize database and create default admin user"""
import logging
from database import init_db, SessionLocal, User
from auth import get_password_hash
from database import UserRole

logger = logging.getLogger(__name__)

# Create database tables
logger.info("Creating database tables...")
init_db()

# Create default admin user
db = SessionLocal()
admin_exists = db.query(User).filter(User.username == "admin").first()

if not admin_exists:
    admin = User(
        username="admin",
        email="admin@credobank.ge",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("✅ Admin user created successfully!")
    logger.info("   Username: admin")
    logger.info("   Password: admin123")
    logger.info("   ⚠️  Please change this password after first login!")
else:
    logger.info("⚠️  Admin user already exists")

db.close()
logger.info("\n✅ Database initialization complete!")
