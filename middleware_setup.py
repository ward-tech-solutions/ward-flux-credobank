"""
WARD TECH SOLUTIONS - Setup Middleware
Redirects to setup wizard if platform not configured
"""
import logging
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import SetupWizardState

logger = logging.getLogger(__name__)


# Routes that should always be accessible (even during setup)
ALLOWED_ROUTES = ["/setup", "/api/v1/setup", "/api/v1/health", "/static", "/docs", "/redoc", "/openapi.json"]


def is_setup_complete() -> bool:
    """Check if initial setup has been completed"""
    db = SessionLocal()
    try:
        state = db.query(SetupWizardState).first()
        if not state:
            return False
        return state.is_complete
    except Exception:
        # If table doesn't exist yet, setup is not complete
        return False
    finally:
        db.close()


async def setup_check_middleware(request: Request, call_next):
    """
    Middleware to check if setup is complete.
    If not, redirect all requests to setup wizard.
    """
    path = request.url.path

    # Allow access to setup routes and static files
    for allowed in ALLOWED_ROUTES:
        if path.startswith(allowed):
            return await call_next(request)

    # Check if setup is complete
    if not is_setup_complete():
        # Redirect to setup wizard
        if request.url.path != "/setup":
            return RedirectResponse(url="/setup", status_code=302)

    # Continue with normal request processing
    return await call_next(request)
