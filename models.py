"""
User model for Flask-Login
"""
from flask_login import UserMixin


class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.first_name = user_data.get('first_name')
        self.last_name = user_data.get('last_name')
        self.role = user_data.get('role')
        self.org_id = user_data.get('org_id')
        self.permissions = user_data.get('permissions', [])
        self.is_super_admin = user_data.get('is_super_admin', False)
        self.is_active = user_data.get('is_active', True)
    
    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role in ['super_admin', 'org_admin'] or self.is_super_admin
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        if self.is_super_admin:
            return True
        return permission in self.permissions