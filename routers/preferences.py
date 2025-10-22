"""
WARD TECH SOLUTIONS - User Preferences API
Handles user preferences like theme, language, timezone, etc.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db, User
from auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user/preferences", tags=["preferences"])


class UserPreferences(BaseModel):
    """User preference model"""

    theme_preference: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    dashboard_layout: Optional[str] = None


class PreferenceUpdate(BaseModel):
    """Model for updating individual preferences"""

    theme_preference: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    dashboard_layout: Optional[str] = None


@router.get("/", response_model=UserPreferences)
async def get_user_preferences(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user's preferences"""
    return UserPreferences(
        theme_preference=current_user.theme_preference,
        language=current_user.language,
        timezone=current_user.timezone,
        notifications_enabled=current_user.notifications_enabled,
        dashboard_layout=current_user.dashboard_layout,
    )


@router.patch("/", response_model=UserPreferences)
async def update_user_preferences(
    preferences: PreferenceUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Update current user's preferences"""

    # Update only provided fields
    if preferences.theme_preference is not None:
        # Validate theme value
        if preferences.theme_preference not in ["light", "dark", "auto"]:
            raise HTTPException(status_code=400, detail="Invalid theme preference")
        current_user.theme_preference = preferences.theme_preference

    if preferences.language is not None:
        current_user.language = preferences.language

    if preferences.timezone is not None:
        current_user.timezone = preferences.timezone

    if preferences.notifications_enabled is not None:
        current_user.notifications_enabled = preferences.notifications_enabled

    if preferences.dashboard_layout is not None:
        current_user.dashboard_layout = preferences.dashboard_layout

    try:
        db.commit()
        db.refresh(current_user)

        return UserPreferences(
            theme_preference=current_user.theme_preference,
            language=current_user.language,
            timezone=current_user.timezone,
            notifications_enabled=current_user.notifications_enabled,
            dashboard_layout=current_user.dashboard_layout,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.put("/theme")
async def update_theme(
    theme: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Quick endpoint to update just the theme preference"""
    if theme not in ["light", "dark", "auto"]:
        raise HTTPException(status_code=400, detail="Invalid theme. Must be 'light', 'dark', or 'auto'")

    try:
        current_user.theme_preference = theme
        db.commit()

        return {"message": "Theme updated successfully", "theme": theme}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update theme: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update theme: {str(e)}")


@router.delete("/")
async def reset_preferences(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Reset all preferences to defaults"""
    try:
        current_user.theme_preference = "auto"
        current_user.language = "en"
        current_user.timezone = "UTC"
        current_user.notifications_enabled = True
        current_user.dashboard_layout = None

        db.commit()

        return {"message": "Preferences reset to defaults"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset preferences: {str(e)}")
