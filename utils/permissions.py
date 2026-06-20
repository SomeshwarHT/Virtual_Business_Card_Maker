"""
Permission helpers for the Virtual Business Card Maker app.

The app keeps a simple three-role model:
- viewer: can browse and create their own cards
- admin: can manage most card content
- organizer: can manage all card and app-level settings
"""

# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    "viewer": 1,
    "admin": 2,
    "organizer": 3,
}

# Role names as constants
ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"
ROLE_ORGANIZER = "organizer"

# Valid roles list
VALID_ROLES = [ROLE_VIEWER, ROLE_ADMIN, ROLE_ORGANIZER]


def is_valid_role(role):
    """Return True when the supplied role is one of the supported roles."""
    return role in VALID_ROLES


def role_has_permission(user_role, required_role):
    """
    Check whether a role meets or exceeds the required role.

    This is the compatibility helper used by auth_ulties.py for route guards.
    """
    if not is_valid_role(user_role) or not is_valid_role(required_role):
        return False

    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


# Permission definitions by feature for the business card app
PERMISSIONS = {
    "cards.view": [ROLE_VIEWER, ROLE_ADMIN, ROLE_ORGANIZER],
    "cards.create": [ROLE_VIEWER, ROLE_ADMIN, ROLE_ORGANIZER],
    "cards.edit": [ROLE_ADMIN, ROLE_ORGANIZER],
    "cards.delete": [ROLE_ADMIN, ROLE_ORGANIZER],
    "cards.design": [ROLE_ADMIN, ROLE_ORGANIZER],
    "cards.print": [ROLE_VIEWER, ROLE_ADMIN, ROLE_ORGANIZER],
    "templates.manage": [ROLE_ADMIN, ROLE_ORGANIZER],
    "settings.view": [ROLE_ORGANIZER],
    "settings.edit": [ROLE_ORGANIZER],
}


def has_permission(user_role, permission):
    """
    Check whether a role has a named feature permission.
    """
    if not is_valid_role(user_role):
        return False

    allowed_roles = PERMISSIONS.get(permission, [])
    return user_role in allowed_roles


def get_minimum_role_for_permission(permission):
    """
    Return the lowest role that can use a permission, or None if unknown.
    """
    allowed_roles = PERMISSIONS.get(permission, [])
    if not allowed_roles:
        return None

    min_level = min(ROLE_HIERARCHY.get(role, 999) for role in allowed_roles)
    for role, level in ROLE_HIERARCHY.items():
        if level == min_level and role in allowed_roles:
            return role

    return None
