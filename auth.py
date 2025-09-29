# Authentication and authorization module
import hashlib
import secrets
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Simple in-memory token storage (in production, use Redis or database)
TOKEN_STORE: Dict[str, Dict] = {}
USER_PERMISSIONS: Dict[str, List[str]] = {}

# Default permissions
DEFAULT_PERMISSIONS = ["chat", "metrics"]

class AuthManager:
    def __init__(self):
        self.token_expiry_hours = 24
        self.max_requests_per_hour = 100
        
    def generate_token(self, user_id: str, permissions: List[str] = None) -> str:
        """
        Generate a new authentication token
        
        Args:
            user_id: User identifier
            permissions: List of permissions for the user
            
        Returns:
            Authentication token
        """
        if permissions is None:
            permissions = DEFAULT_PERMISSIONS.copy()
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Store token with metadata
        TOKEN_STORE[token] = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": time.time(),
            "expires_at": time.time() + (self.token_expiry_hours * 3600),
            "last_used": time.time(),
            "request_count": 0,
            "hourly_requests": 0,
            "hourly_reset": time.time() + 3600
        }
        
        # Store user permissions
        USER_PERMISSIONS[user_id] = permissions
        
        logger.info(f"Generated token for user {user_id} with permissions: {permissions}")
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate authentication token
        
        Args:
            token: Authentication token
            
        Returns:
            Token metadata if valid, None otherwise
        """
        if token not in TOKEN_STORE:
            return None
        
        token_data = TOKEN_STORE[token]
        
        # Check if token is expired
        if time.time() > token_data["expires_at"]:
            del TOKEN_STORE[token]
            return None
        
        # Update last used time
        token_data["last_used"] = time.time()
        token_data["request_count"] += 1
        
        # Check hourly rate limit
        if time.time() > token_data["hourly_reset"]:
            token_data["hourly_requests"] = 0
            token_data["hourly_reset"] = time.time() + 3600
        
        token_data["hourly_requests"] += 1
        
        if token_data["hourly_requests"] > self.max_requests_per_hour:
            logger.warning(f"Rate limit exceeded for token {token[:8]}...")
            return None
        
        return token_data
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke authentication token
        
        Args:
            token: Authentication token
            
        Returns:
            True if token was revoked, False if not found
        """
        if token in TOKEN_STORE:
            del TOKEN_STORE[token]
            logger.info(f"Token {token[:8]}... revoked")
            return True
        return False
    
    def revoke_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of tokens revoked
        """
        revoked_count = 0
        tokens_to_remove = []
        
        for token, data in TOKEN_STORE.items():
            if data["user_id"] == user_id:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            del TOKEN_STORE[token]
            revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def check_permission(self, token: str, permission: str) -> bool:
        """
        Check if token has specific permission
        
        Args:
            token: Authentication token
            permission: Permission to check
            
        Returns:
            True if permission granted, False otherwise
        """
        token_data = self.validate_token(token)
        if not token_data:
            return False
        
        return permission in token_data["permissions"]
    
    def get_user_stats(self, user_id: str) -> Dict:
        """
        Get user statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            User statistics dictionary
        """
        user_tokens = []
        total_requests = 0
        
        for token, data in TOKEN_STORE.items():
            if data["user_id"] == user_id:
                user_tokens.append({
                    "token": token[:8] + "...",
                    "created_at": data["created_at"],
                    "last_used": data["last_used"],
                    "request_count": data["request_count"],
                    "expires_at": data["expires_at"]
                })
                total_requests += data["request_count"]
        
        return {
            "user_id": user_id,
            "active_tokens": len(user_tokens),
            "total_requests": total_requests,
            "permissions": USER_PERMISSIONS.get(user_id, []),
            "tokens": user_tokens
        }
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = time.time()
        expired_tokens = []
        
        for token, data in TOKEN_STORE.items():
            if current_time > data["expires_at"]:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del TOKEN_STORE[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    def get_system_stats(self) -> Dict:
        """
        Get system-wide authentication statistics
        
        Returns:
            System statistics dictionary
        """
        total_tokens = len(TOKEN_STORE)
        total_users = len(USER_PERMISSIONS)
        total_requests = sum(data["request_count"] for data in TOKEN_STORE.values())
        
        # Count active tokens (used in last hour)
        current_time = time.time()
        active_tokens = sum(1 for data in TOKEN_STORE.values() 
                          if current_time - data["last_used"] < 3600)
        
        return {
            "total_tokens": total_tokens,
            "active_tokens": active_tokens,
            "total_users": total_users,
            "total_requests": total_requests,
            "expired_tokens": self.cleanup_expired_tokens()
        }

# Global auth manager instance
auth_manager = AuthManager()

# Convenience functions
def generate_token(user_id: str, permissions: List[str] = None) -> str:
    """Generate authentication token"""
    return auth_manager.generate_token(user_id, permissions)

def validate_token(token: str) -> Optional[Dict]:
    """Validate authentication token"""
    return auth_manager.validate_token(token)

def check_permission(token: str, permission: str) -> bool:
    """Check token permission"""
    return auth_manager.check_permission(token, permission)

def revoke_token(token: str) -> bool:
    """Revoke authentication token"""
    return auth_manager.revoke_token(token)

def get_user_stats(user_id: str) -> Dict:
    """Get user statistics"""
    return auth_manager.get_user_stats(user_id)

def get_system_stats() -> Dict:
    """Get system statistics"""
    return auth_manager.get_system_stats()
