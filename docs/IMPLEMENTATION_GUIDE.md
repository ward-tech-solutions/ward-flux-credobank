# 🚀 User Authentication & Bulk Operations - Implementation Guide

## ✅ What's Already Created

I've created 3 new files for you:

1. **`database.py`** - Database models for users
2. **`auth.py`** - Complete authentication system with JWT
3. **bulk_operations.py** - Bulk CSV/Excel import/export

---

## 📦 Installation Steps

### Step 1: Install Dependencies

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
source .venv/bin/activate
pip install python-jose[cryptography] passlib[bcrypt] sqlalchemy alembic pandas openpyxl
```

### Step 2: Initialize Database

Create a Python script to set up the database and create the first admin user:

```bash
python3 << 'EOF'
from database import init_db, SessionLocal, User
from auth import get_password_hash
from database import UserRole

# Create database tables
init_db()

# Create default admin user
db = SessionLocal()
admin_exists = db.query(User).filter(User.username == "admin").first()

if not admin_exists:
    admin = User(
        username="admin",
        email="admin@credobank.ge",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),  # Change this password!
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created: username='admin', password='admin123'")
else:
    print("⚠️  Admin user already exists")

db.close()
EOF
```

---

## 🔧 Add API Endpoints to main.py

Add these imports at the top of `main.py`:

```python
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import pandas as pd

from database import get_db, User, UserRole, init_db
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    create_user, UserCreate, UserResponse, Token,
    require_admin, require_manager_or_admin, require_tech_or_admin
)
from bulk_operations import (
    parse_csv_file, parse_excel_file, validate_bulk_import_data,
    process_bulk_import, bulk_update_devices, bulk_delete_devices,
    generate_csv_template, export_devices_to_csv, export_devices_to_excel,
    BulkOperationResult
)
```

### Add to lifespan function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    init_db()

    # Existing code...
    app.state.zabbix = ZabbixClient()
    # ... rest of your code
```

### Authentication Endpoints (Add after existing @app routes):

```python
# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns JWT token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # Only admins can create users
):
    """Register new user (admin only)"""
    # Check if username exists
    from auth import get_user_by_username, get_user_by_email
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user(db, user_data)
    return user

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return current_user

@app.get("/api/v1/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    return users

@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.full_name = update_data.full_name
    user.email = update_data.email
    user.role = update_data.role
    user.region = update_data.region
    if update_data.password:
        from auth import get_password_hash
        user.hashed_password = get_password_hash(update_data.password)

    db.commit()
    db.refresh(user)
    return user

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted"}

# ============================================
# Bulk Operations Endpoints
# ============================================

@app.get("/api/v1/bulk/template")
async def download_bulk_import_template(
    current_user: User = Depends(require_tech_or_admin)
):
    """Download CSV template for bulk import"""
    from fastapi.responses import StreamingResponse
    csv_content = generate_csv_template()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_import_template.csv"}
    )

@app.post("/api/v1/bulk/import", response_model=BulkOperationResult)
async def bulk_import_devices(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(require_tech_or_admin)
):
    """Bulk import devices from CSV/Excel"""
    zabbix = request.app.state.zabbix

    # Parse file
    if file.filename.endswith('.csv'):
        df = await parse_csv_file(file)
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = await parse_excel_file(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel")

    # Validate data
    is_valid, errors = validate_bulk_import_data(df)
    if not is_valid:
        return BulkOperationResult(
            success=False,
            total=0,
            successful=0,
            failed=0,
            errors=[{"error": err} for err in errors],
            details=[]
        )

    # Process import
    result = await process_bulk_import(df, zabbix)
    return result

@app.post("/api/v1/bulk/update", response_model=BulkOperationResult)
async def bulk_update(
    request: Request,
    host_ids: List[str],
    update_data: dict,
    current_user: User = Depends(require_tech_or_admin)
):
    """Bulk update multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_update_devices(host_ids, update_data, zabbix)
    return result

@app.post("/api/v1/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete(
    request: Request,
    host_ids: List[str],
    current_user: User = Depends(require_admin)  # Only admin can bulk delete
):
    """Bulk delete multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_delete_devices(host_ids, zabbix)
    return result

@app.get("/api/v1/bulk/export/csv")
async def export_csv(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Export all devices to CSV"""
    from fastapi.responses import StreamingResponse
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)
    csv_content = export_devices_to_csv(devices)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=devices_export.csv"}
    )

@app.get("/api/v1/bulk/export/excel")
async def export_excel(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Export all devices to Excel"""
    from fastapi.responses import StreamingResponse
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)
    excel_content = export_devices_to_excel(devices)
    return StreamingResponse(
        io.BytesIO(excel_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=devices_export.xlsx"}
    )
```

---

## 🎨 Create Login Page

Create `templates/login.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Network Monitoring</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
    <style>
        .login-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 400px;
        }
        .login-box h1 {
            margin-bottom: 30px;
            text-align: center;
            color: #333;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn-login:hover {
            background: #5568d3;
        }
        .error-message {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-box">
            <h1>🔐 Network Monitor</h1>
            <div id="error-message" class="error-message"></div>
            <form id="login-form">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required autofocus>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn-login">Login</button>
            </form>
        </div>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('error-message');
            errorDiv.style.display = 'none';

            const formData = new FormData();
            formData.append('username', document.getElementById('username').value);
            formData.append('password', document.getElementById('password').value);

            try {
                const response = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('access_token', data.access_token);
                    window.location.href = '/';
                } else {
                    const error = await response.json();
                    errorDiv.textContent = error.detail || 'Login failed';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Network error. Please try again.';
                errorDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>
```

Add route to `main.py`:

```python
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    return templates.TemplateResponse("login.html", {"request": request})
```

---

## 📄 Next Steps - What YOU Need to Do

### 1. Update `requirements.txt`

Copy the contents of `requirements_new.txt` I created into your `requirements.txt`

### 2. Install packages:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the database initialization script (shown above in Step 2)

### 4. Test the authentication:

```bash
curl -X POST http://10.10.12.88:5001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

You should get a JWT token back!

### 5. Create additional UI pages:

- **User Management Page** (`templates/users.html`) - List, create, edit, delete users
- **Bulk Import Page** (`templates/bulk-import.html`) - Upload CSV/Excel
- **Devices page updates** - Add checkboxes for bulk selection

---

## 🔒 Security Recommendations

1. **Change the SECRET_KEY** in `auth.py`:
   ```bash
   openssl rand -hex 32
   ```
   Use that output as your SECRET_KEY

2. **Change default admin password** immediately after first login

3. **Use HTTPS** in production (not HTTP)

4. **Add rate limiting** for login attempts

5. **Use PostgreSQL** instead of SQLite for production

---

## 📊 Role Permissions Summary

| Feature | Admin | Regional Manager | Technician | Viewer |
|---------|-------|------------------|------------|--------|
| View Dashboard | ✅ | ✅ (their region) | ✅ | ✅ |
| View Devices | ✅ | ✅ (their region) | ✅ | ✅ |
| Add Device | ✅ | ✅ | ✅ | ❌ |
| Edit Device | ✅ | ✅ | ✅ | ❌ |
| Delete Device | ✅ | ❌ | ❌ | ❌ |
| Bulk Operations | ✅ | ✅ | ✅ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ |
| View Reports | ✅ | ✅ (their region) | ✅ | ✅ |

---

## 🧪 Testing

Test with these curl commands:

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://10.10.12.88:5001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# 2. Get current user
curl -H "Authorization: Bearer $TOKEN" \
  http://10.10.12.88:5001/api/v1/auth/me

# 3. List users
curl -H "Authorization: Bearer $TOKEN" \
  http://10.10.12.88:5001/api/v1/users

# 4. Download bulk import template
curl -H "Authorization: Bearer $TOKEN" \
  http://10.10.12.88:5001/api/v1/bulk/template -o template.csv

# 5. Export devices to CSV
curl -H "Authorization: Bearer $TOKEN" \
  http://10.10.12.88:5001/api/v1/bulk/export/csv -o devices.csv
```

---

Need help with any step? Let me know!
