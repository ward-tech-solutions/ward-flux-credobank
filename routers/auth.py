"""
WARD Tech Solutions - Authentication Router
Handles user authentication, registration, and user management
"""
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
    require_admin,
    Token,
    UserCreate,
    UserResponse,
)
from database import User, get_db

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["authentication"])


@router.post("/auth/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login endpoint - returns JWT token
    Rate limited to 5 attempts per minute to prevent brute force attacks
    """
    # Rate limiting disabled for easier deployment
    # if RATE_LIMITING_ENABLED and limiter:
    #     try:
    #         await limiter.check_request_limit(request, "5/minute")
    #     except:
    #         raise HTTPException(
    #             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #             detail="Too many login attempts. Please try again later."
    #         )
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Register new user (admin only)"""
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user(db, user_data)
    return user


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    import json
    # Ensure regions is properly serialized as JSON string if it's a list
    regions_value = current_user.regions
    if isinstance(regions_value, list):
        regions_value = json.dumps(regions_value)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        region=current_user.region,
        regions=regions_value,
        branches=current_user.branches,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """List all users (admin only)"""
    import json
    users = db.query(User).all()
    # Serialize regions field properly
    result = []
    for user in users:
        regions_value = user.regions
        if isinstance(regions_value, list):
            regions_value = json.dumps(regions_value)
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            region=user.region,
            regions=regions_value,
            branches=user.branches,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
        ))
    return result


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.full_name = update_data.full_name
    user.email = update_data.email
    user.role = update_data.role
    user.region = update_data.region
    user.regions = update_data.regions  # Support multiple regions
    if update_data.password:
        user.hashed_password = get_password_hash(update_data.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted"}
