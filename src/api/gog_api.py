# src/api/gog_api.py

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path
import winreg
import sqlite3
from datetime import datetime, timezone
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import socket

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from GOG login"""
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
        
        self.wfile.write(b"""
            <html><body>
                <h1>Authorization Complete!</h1>
                <p>You can close this window and return to the application.</p>
                <script>window.close()</script>
            </body></html>
        """)

class GOGAPI:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize GOG API wrapper
        :param client_id: GOG OAuth client ID
        :param client_secret: GOG OAuth client secret
        """
        self.client_id = client_id or os.getenv('GOG_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('GOG_CLIENT_SECRET')
        self.logger = logging.getLogger(__name__)
        self.gog_path = self._find_gog_path()
        self.galaxy_db_path = self._find_galaxy_db()
        
        # API endpoints
        self.auth_url = "https://auth.gog.com/auth"
        self.token_url = "https://auth.gog.com/token"
        self.api_base_url = "https://embed.gog.com"
        
        # Authentication tokens
        self.access_token = None
        self.refresh_token = None
        
    def _find_gog_path(self) -> Optional[Path]:
        """Find GOG Galaxy installation directory"""
        try:
            if os.name == 'nt':  # Windows
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\GalaxyClient")
                path = winreg.QueryValueEx(key, "Path")[0]
                winreg.CloseKey(key)
                return Path(path)
            elif os.name == 'posix':  # Linux/MacOS
                possible_paths = [
                    Path.home() / "Library/Application Support/GOG.com/Galaxy",  # macOS
                    Path.home() / ".local/share/GOG.com/Galaxy"  # Linux
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
        except Exception as e:
            self.logger.error(f"Failed to find GOG Galaxy path: {e}")
        return None

    def _find_galaxy_db(self) -> Optional[Path]:
        """Find GOG Galaxy database path"""
        if not self.gog_path:
            return None
            
        if os.name == 'nt':
            db_path = self.gog_path / "storage" / "galaxy.db"
        else:
            db_path = self.gog_path / "storage" / "galaxy.db"
            
        return db_path if db_path.exists() else None

    def authenticate(self) -> bool:
        """Start browser-based authentication flow"""
        if not self.client_id:
            self.logger.error("GOG client ID not provided")
            return False

        try:
            # Start local server to handle callback
            server, port = self._start_auth_server()
            redirect_uri = f"http://localhost:{port}/callback"

            # Construct authorization URL
            auth_params = {
                'client_id': self.client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'read'
            }
            
            auth_url = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"
            
            # Open browser for authentication
            webbrowser.open(auth_url)
            
            # Wait for callback
            server_thread = threading.Thread(target=server.handle_request)
            server_thread.start()
            server_thread.join(timeout=300)  # 5 minute timeout
            
            # Get authorization code
            auth_code = getattr(server, 'auth_code', None)
            if not auth_code:
                return False
                
            # Exchange code for tokens
            return self._get_tokens(auth_code, redirect_uri)

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    def _start_auth_server(self) -> tuple[HTTPServer, int]:
        """Start local server to handle OAuth callback"""
        port = 8919
        while port < 9000:
            try:
                server = HTTPServer(('localhost', port), OAuthCallbackHandler)
                server.auth_code = None
                return server, port
            except socket.error:
                port += 1
        raise Exception("No available ports found for auth server")

    def _get_tokens(self, auth_code: str, redirect_uri: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': redirect_uri
            }
            
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens.get('access_token')
            self.refresh_token = tokens.get('refresh_token')
            
            return bool(self.access_token and self.refresh_token)

        except Exception as e:
            self.logger.error(f"Failed to get tokens: {e}")
            return False

    def refresh_auth_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            return False

        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }

            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens.get('access_token')
            self.refresh_token = tokens.get('refresh_token')  # New refresh token
            
            return bool(self.access_token)

        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")
            return False

    def get_installed_games(self) -> List[Dict[str, Any]]:
        """Get list of installed GOG games"""
        installed_games = []
        
        if not self.galaxy_db_path:
            return installed_games

        try:
            # Connect to Galaxy database
            conn = sqlite3.connect(self.galaxy_db_path)
            cursor = conn.cursor()
            
            # Query installed games
            cursor.execute("""
                SELECT 
                    ProductName, 
                    ProductId, 
                    InstallDirectory,
                    VersionName,
                    InstalledSize
                FROM Products 
                WHERE IsInstalled = 1
            """)
            
            for row in cursor.fetchall():
                game_info = {
                    'name': row[0],
                    'app_id': str(row[1]),
                    'install_dir': row[2],
                    'version': row[3],
                    'size_on_disk': row[4],
                    'platform': 'GOG'
                }
                installed_games.append(game_info)
                
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to get installed games: {e}")

        return installed_games

    def get_owned_games(self) -> List[Dict[str, Any]]:
        """Get list of owned GOG games"""
        if not self.access_token:
            self.logger.error("Authentication required")
            return []

        owned_games = []
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # GOG API paginates results
            page = 1
            while True:
                response = requests.get(
                    f"{self.api_base_url}/user/games",
                    params={'page': page},
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                games = data.get('games', [])
                if not games:
                    break
                    
                owned_games.extend(games)
                page += 1

        except Exception as e:
            self.logger.error(f"Failed to get owned games: {e}")

        return owned_games

    def launch_game(self, app_id: str) -> bool:
        """
        Launch a GOG game
        :param app_id: GOG game ID
        :return: True if launch successful
        """
        try:
            # GOG Galaxy protocol
            return webbrowser.open(f"goggalaxy://runGame/{app_id}")
        except Exception as e:
            self.logger.error(f"Failed to launch game {app_id}: {e}")
            return False

    def get_game_details(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a game
        :param app_id: GOG game ID
        :return: Game details or None if not found
        """
        try:
            response = requests.get(f"{self.api_base_url}/products/{app_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get game details for {app_id}: {e}")
            return None

# Example usage:
if __name__ == "__main__":
    # Initialize GOG API
    gog = GOGAPI()
    
    # Authenticate (opens browser)
    if gog.authenticate():
        print("Authentication successful!")
        
        # Get installed games
        installed = gog.get_installed_games()
        print(f"\nFound {len(installed)} installed GOG games:")
        for game in installed:
            print(f"- {game['name']} (ID: {game['app_id']})")
            
        # Get owned games (requires authentication)
        owned = gog.get_owned_games()
        print(f"\nFound {len(owned)} owned GOG games")