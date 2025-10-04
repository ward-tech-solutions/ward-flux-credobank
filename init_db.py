"""Initialize database and create default admin user"""
from database import init_db, SessionLocal, User
from auth import get_password_hash
from database import UserRole

# Create database tables
print("Creating database tables...")
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
        is_active=True
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created successfully!")
    print("   Username: admin")
    print("   Password: admin123")
    print("   ⚠️  Please change this password after first login!")
else:
    print("⚠️  Admin user already exists")

db.close()
print("\n✅ Database initialization complete!")
