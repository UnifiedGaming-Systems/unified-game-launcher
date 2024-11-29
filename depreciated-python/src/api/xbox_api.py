# src/api/xbox_api.py

import os
import json
import logging
import winreg
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import socket
import xml.etree.ElementTree as ET
import subprocess
from base64 import b64encode
import secrets

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from Microsoft login"""
    def do_GET(self):
        """Handle the OAuth callback GET request"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Parse the callback URL for the authorization code
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        # Store the auth code in the server instance
        if 'code' in query_components:
            self.server.auth_code = query_components['code'][0]
        
        # Send a response to the user
        self.wfile.write(b"""
            <html>
                <body>
                    <h1>Authorization Complete!</h1>
                    <p>You can close this window and return to the application.</p>
                    <script>window.close()</script>
                </body>
            </html>
        """)

class XboxAPI:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize Xbox/Microsoft Store API wrapper
        :param client_id: Xbox Live API client ID
        :param client_secret: Xbox Live API client secret
        """
        self.client_id = client_id or os.getenv('XBOX_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('XBOX_CLIENT_SECRET')
        self.logger = logging.getLogger(__name__)
        self.xbox_path = self._find_xbox_path()
        self.base_url = "https://xbox-live-api.xboxlive.com"
        self.auth_token = None
        self.xtoken = None
        self.user_token = None
        self.refresh_token = None
        
        # OAuth endpoints
        self.oauth_auth_url = "https://login.live.com/oauth20_authorize.srf"
        self.oauth_token_url = "https://login.live.com/oauth20_token.srf"
        self.redirect_uri = "http://localhost:8919/callback"  # Local callback URL
        
        # User info
        self.user_info = None

    def start_auth_server(self) -> Tuple[HTTPServer, int]:
        """Start local server to handle OAuth callback"""
        # Find an available port starting from 8919
        port = 8919
        while port < 9000:
            try:
                server = HTTPServer(('localhost', port), OAuthCallbackHandler)
                server.auth_code = None
                return server, port
            except socket.error:
                port += 1
        raise Exception("No available ports found for auth server")

    def authenticate_with_browser(self) -> bool:
        """
        Start browser-based authentication flow
        Returns: True if authentication successful
        """
        if not self.client_id:
            self.logger.error("Xbox Live API client ID not provided")
            return False

        try:
            # Generate state parameter for security
            state = secrets.token_urlsafe(16)
            
            # Start local server to handle callback
            server, port = self.start_auth_server()
            self.redirect_uri = f"http://localhost:{port}/callback"

            # Construct authorization URL
            auth_params = {
                'client_id': self.client_id,
                'response_type': 'code',
                'redirect_uri': self.redirect_uri,
                'scope': 'Xboxlive.signin Xboxlive.offline_access',
                'state': state
            }
            
            auth_url = f"{self.oauth_auth_url}?{urllib.parse.urlencode(auth_params)}"
            
            # Open browser for user authentication
            webbrowser.open(auth_url)
            
            # Start server in a thread to handle callback
            server_thread = threading.Thread(target=server.handle_request)
            server_thread.start()
            server_thread.join(timeout=300)  # Wait up to 5 minutes for auth
            
            # Get authorization code from server
            auth_code = getattr(server, 'auth_code', None)
            if not auth_code:
                self.logger.error("No authorization code received")
                return False
            
            # Exchange authorization code for tokens
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(self.oauth_token_url, data=token_data)
            response.raise_for_status()
            token_response = response.json()
            
            self.auth_token = token_response.get('access_token')
            self.refresh_token = token_response.get('refresh_token')
            
            # Get Xbox Live token
            return self._get_xbox_token()

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    def _get_xbox_token(self) -> bool:
        """Exchange OAuth token for Xbox Live token"""
        try:
            # Exchange OAuth token for Xbox Live token
            xbox_auth_url = "https://user.auth.xboxlive.com/user/authenticate"
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            xbox_data = {
                'Properties': {
                    'AuthMethod': 'RPS',
                    'SiteName': 'user.auth.xboxlive.com',
                    'RpsTicket': f'd={self.auth_token}'
                },
                'RelyingParty': 'http://auth.xboxlive.com',
                'TokenType': 'JWT'
            }

            response = requests.post(xbox_auth_url, json=xbox_data, headers=headers)
            response.raise_for_status()
            
            auth_response = response.json()
            self.xtoken = auth_response.get('Token')
            self.user_token = auth_response.get('DisplayClaims', {}).get('xui', [{}])[0].get('uhs')

            # Get user information
            self._get_user_info()
            return True

        except Exception as e:
            self.logger.error(f"Failed to get Xbox token: {e}")
            return False

    def _get_user_info(self):
        """Get Xbox Live user information"""
        if not self.xtoken or not self.user_token:
            return

        try:
            headers = {
                'Authorization': f'XBL3.0 x={self.user_token};{self.xtoken}',
                'Accept': 'application/json'
            }

            response = requests.get(
                'https://profile.xboxlive.com/users/me/profile/settings',
                headers=headers
            )
            response.raise_for_status()
            self.user_info = response.json()

        except Exception as e:
            self.logger.error(f"Failed to get user info: {e}")

    def refresh_auth_token(self) -> bool:
        """Refresh the OAuth token using the refresh token"""
        if not self.refresh_token:
            return False

        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }

            response = requests.post(self.oauth_token_url, data=data)
            response.raise_for_status()
            
            token_response = response.json()
            self.auth_token = token_response.get('access_token')
            self.refresh_token = token_response.get('refresh_token')  # Get new refresh token
            
            return self._get_xbox_token()

        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")
            return False

    # ... (rest of the existing methods remain the same: _find_xbox_path, get_installed_games, etc.)

# Example usage:
if __name__ == "__main__":
    # Initialize Xbox API
    xbox = XboxAPI()
    
    # Start browser-based authentication
    print("Opening browser for Xbox Live authentication...")
    if xbox.authenticate_with_browser():
        print("Authentication successful!")
        
        # Get user information
        if xbox.user_info:
            print(f"Logged in as: {xbox.user_info.get('profileUsers', [{}])[0].get('settings', [{}])[0].get('value')}")
        
        # Get installed games
        installed = xbox.get_installed_games()
        print(f"\nFound {len(installed)} installed Xbox/Microsoft Store games:")
        for game in installed:
            print(f"- {game['name']} (Package: {game['package_family_name']})")
    else:
        print("Authentication failed!")