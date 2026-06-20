"""
Authentication and authorization utilities for HE5 AI.

This module provides helper functions for:
- Checking user access based on IAM authentication
- Decorators for access control on routes
- Role-based access control (viewer, admin, organizer)

Security Notes:
- All routes must use appropriate decorators (@page_login_required, @require_role)
- Role hierarchy: viewer < admin < organizer
- Always validate user input and check permissions before database operations
- Never trust client-side data - always verify on server side
"""
from functools import wraps
from flask import g, redirect, url_for, flash, jsonify, request
from utils.db_utils import get_db
from utils.permissions import (
    ROLE_HIERARCHY, ROLE_VIEWER, ROLE_ADMIN, ROLE_ORGANIZER,
    VALID_ROLES, is_valid_role, role_has_permission
)

# Import IAM-provided decorators and helpers directly.
# The application assumes He5Lib is available; if it is not,
# startup should fail loudly rather than silently degrading auth.
from He5Lib.he5IAMConnect import (
    page_login_required as iam_page_login_required,
    api_login_required as iam_api_login_required,   # for API routes (returns JSON 401 on unauth)
    getUserName,
    getUserEmail,
)


def get_iam_user_id():
    """
    Get the current user IAM ID from Flask's g object.
    
    Returns:
        str or None: IAM user ID, or None if not authenticated
    """
    return getattr(g, 'user_id', None)


def get_user_id():
    """
    Get the current user's database ID from IAM ID.
    Fetches the database user_id based on the external auth ID from Flask's g object.
    
    Returns:
        int or None: Database user ID, or None if not authenticated or user not found
    """
    iam_user_id = get_iam_user_id()
    if not iam_user_id:
        return None
    
    db = get_db()
    try:
        from models import User
        user = db.query(User).filter(User.google_id == str(iam_user_id)).first()
        return user.id if user else None
    finally:
        db.close()


def get_or_create_user(iam_user_id, name=None, email=None):
    """
    Get or create a user in the database from IAM user ID.
    
    Args:
        iam_user_id: IAM user ID
        name: User name (optional)
        email: User email (optional)
        
    Returns:
        User: User object
    """
    from utils.db_utils import get_db
    from models import User
    
    db = get_db()
    try:
        user = db.query(User).filter(User.google_id == str(iam_user_id)).first()
        
        if not user:
            # Get user info from IAM if available
            try:
                from He5Lib.he5IAMConnect import getUserName, getUserEmail
                if not name:
                    name = getUserName() or None
                if not email:
                    email = getUserEmail() or None
            except:
                pass
            
            user = User(
                google_id=str(iam_user_id),
                name=name,
                email=email,
                role=ROLE_VIEWER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update user info if provided
            if name and not user.name:
                user.name = name
            if email and not user.email:
                user.email = email
            if name or email:
                db.commit()
        
        return user
    finally:
        db.close()


def _ensure_app_user_created():
    """
    Internal helper: ensure that there is a corresponding application-level
    User row for the currently authenticated IAM user.

    - Uses g.user_id (external auth id) and optional g.user_name / g.user_email.
    - Stores the DB user id on g.db_user_id for downstream use.
    """
    iam_user_id = get_iam_user_id()
    if not iam_user_id:
        return None

    name = getattr(g, 'user_name', None)
    email = getattr(g, 'user_email', None)

    user = get_or_create_user(iam_user_id, name=name, email=email)
    try:
        g.user_role = getattr(user, 'role', ROLE_VIEWER) or ROLE_VIEWER
    except Exception:
        pass
    try:
        g.db_user_id = user.id
    except Exception:
        # g may not allow attribute assignment in some edge cases; ignore.
        pass
    return user


def app_page_login_required(f):
    """
    Application-level page login decorator.

    Responsibilities:
    - Delegate to IAM login (iam_page_login_required) so IAM auth is enforced.
    - Ensure a corresponding User row exists in our DB for the IAM user.
    - Expose DB user id as g.db_user_id.
    """
    @wraps(f)
    @iam_page_login_required
    def decorated_function(*args, **kwargs):
        _ensure_app_user_created()
        return f(*args, **kwargs)

    return decorated_function


def app_api_login_required(f):
    """
    Application-level API login decorator.

    Responsibilities:
    - Delegate to IAM login (iam_api_login_required) so IAM auth is enforced.
    - Ensure a corresponding User row exists in our DB for the IAM user.
    - Expose DB user id as g.db_user_id.
    """
    @wraps(f)
    @iam_api_login_required
    def decorated_function(*args, **kwargs):
        _ensure_app_user_created()
        return f(*args, **kwargs)

    return decorated_function


def require_role(required_role='viewer'):
    """
    Decorator to require a specific role for route access.
    
    Usage:
        @bp.route('/admin/settings')
        @page_login_required
        @require_role('admin')
        def admin_settings():
            ...
    
    Args:
        required_role: Required role ('viewer', 'admin', 'organizer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_user_id()
            if not user_id:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Authentication required.'}), 401
                else:
                    # Redirect to IAM login
                    from config import IAM_PATH, BASE_PATH
                    from urllib.parse import urlencode
                    flash('Authentication required. Please log in.', 'error')
                    redirect_url = BASE_PATH if BASE_PATH.startswith(('http://', 'https://')) else f'https://{BASE_PATH}'
                    login_url = f"{IAM_PATH}/app-login?{urlencode({'redirect': redirect_url})}"
                    return redirect(login_url)
            
            # For now, all authenticated users have 'viewer' role minimum
            # In a full implementation, you would check the user's role from database
            user_role = getattr(g, 'user_role', ROLE_VIEWER)
            
            if not role_has_permission(user_role, required_role):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': f'You need {required_role} role to access this.'}), 403
                else:
                    flash(f'You need {required_role} role to access this.', 'error')
                    return redirect(url_for('public.home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
