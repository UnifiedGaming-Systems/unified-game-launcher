# src/core/auth.py

import os
from typing import Dict, Optional, Any
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta

class PlaformAuth:
    """
    Manages authenticaton for a single platform
    """
    def __init__(self, platform: str):
        """
        Initalize platform authentication
        :param platform: Name of the platform (steam, epic, xbox, etc)
        """

        self.platform = platform
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.user_id = None

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated
        :return: True if authenticated and token is valid
        """
        return (
            self.access_token is not None and
            self.token_expires_at is not None and 
            datetime.now() < self.token_expires_at
        )
    
    def update_tokens(self, access_token: str, refresh_token: Optional[str] = None, expires_in: Optional[int] = None):
        """
        Update authentication tokens
        :param access_token: New access token
        :param refresh_token: Optional new refresh token
        :param expires_in: Token validity duration in seconds
        """
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        
        # Set expiration time
        if expires_in:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

class UnifiedAuth:
    """
    Centralized authentication mangement for multiple game platforms
    """
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the authentication manager
        :param config_path: Optional path to config directory
        """

        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or Path.home() / ".unified_launcher"
        self.config_path.mkdir(exist_ok=True)

        # Authentication storage for different platforms
        self.platform_auths: Dict[str, PlaformAuth] = {}

        # Authentication APIs for different platforms
        self.platform_apis: Dict[str, Any] = {}

        # Load existing authentication data
        self._load_auth_data()

    def _load_auth_data(self):
        """Load saved authentication data from file"""
        auth_file = self.config_path / "auth_data.json"
        if not auth_file.exists():
            return
        
        try:
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)
                for platform, data in auth_data.items():
                    auth = PlaformAuth(platform)
                    auth.access_token = data.get('access_token')
                    auth.refresh_token = data.get('refresh_token')
                    auth.user_id = data.get('user_id')

                    # Restore expiration time if available
                    expires_at = data.get('token_expires_at')
                    if expires_at:
                        auth.token_expires_at = datetime.fromisoformat(expires_at)

                    self.platform_auths[platform] = auth
        
        except Exception as e:
            self.logger.error(f"Failed to load authentication data: {e}")
    
    def save_auth_data(self):
        """Save authentication data to file"""
        try:
            auth_data = {}
            for platform, auth in self.platform_apis.items():
                auth_data[platform] = {
                    'access_token': auth.access_token,
                    'refresh_token': auth.refresh_token,
                    'user_id': auth.user_id,
                    'token_expires_at': auth.token_expires_at.isoformat() if auth.token_expires_at else None
                }

            auth_file = self.config_path / "auth_data.json"
            with open(auth_file, 'w') as f:
                json.dump(auth_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save authentication data: {e}")

    def register_platform_api(self, platform: str, api_instance: Any):
        """
        Register an API instance for a platform
        :param platform: Platform name
        :param api_instance: API instance with authentication methods
        """
        self.platform_apis[platform] = api_instance

        # Initialize platform authentication if not exists
        if platform not in self.platform_apis:
            self.platform_auths[platform] = PlaformAuth(platform)

    def authenticate(self, platform: str) -> bool:
        """
        Authenticate a specific platform
        :param platform: Platform to authenticate
        :return: True if authentication successful
        """

        api = self.platform_apis.get(platform)
        if not api:
            self.logger.error(f"No API found for {platform}")
            return False
        
        # If already authenticated return True
        if platform in self.platform_auths and self.platform_auths[platform].is_authenticated():
            return True
        
        try:
            # Attempt to authenticate
            if api.authenticate():
                # Update tokens
                auth = self.platform_auths[platform]
                auth.access_token = getattr(api, 'access_token', None)
                auth.refresh_token = getattr(api, 'refresh_token', None)

                # Save authentication data
                self.save_auth_data()
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Authentication failed for {platform}: {e}")
            return False
        
    def refresh_token(self, platform: str) -> bool:
        """
        Refresh authentication token for a platform
        :param platform: Platform to refresh
        :return: True if refresh successful
        """
        api = self.platform_apis.get(platform)
        auth = self.platform_auths.get(platform)

        if not api or not auth:
            self.logger.error(f"No API or auth found for {platform}")
            return False
        
        try:
            # Use platform-specific token refresh method
            if api.refresh_auth_token():
                auth.access_token = getattr(api, 'access_token', None)
                auth.refresh_token = getattr(api, 'refresh_token', None)

                # Save updated authentication data
                self.save_auth_data()
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Token refresh failed for {platform}: {e}")
            return False
        
    def get_access_token(self, platform: str) -> Optional[str]:
        """
        Get current access token for a platform
        :param platform: Platform to get token for
        :return: Access token or None
        """
        auth = self.platform_auths(platform)
        if not auth or auth.is_authenticated():
            return None
        return auth.access_token
    
    def logout(self, platform: str):
        """
        Logout from a specific platform
        :param platform: Platform to logout from
        """
        if platform in self.platform_auths:
            del self.platform_auths[platform]
            self.save_auth_data()