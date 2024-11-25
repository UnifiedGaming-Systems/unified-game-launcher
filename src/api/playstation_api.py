# src/api/playstation_api.py

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path
import winreg
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import socket
import webbrowser
import subprocess

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from PlayStation login"""
    def do_GET(self):
        """Handle the OAuth callback GET request"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if 'code' in query_components:
            self.server.auth_code = query_components['code'][0]
        
        self.wfile.write(b"""
            <html><body>
                <h1>PlayStation Authorization Complete!</h1>
                <p>You can close this window and return to the application.</p>
                <script>window.close()</script>
            </body></html>
        """)

class PlayStationAPI:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize PlayStation API wrapper
        :param client_id: PlayStation Network OAuth client ID
        :param client_secret: PlayStation Network OAuth client secret
        """
        self.client_id = client_id or os.getenv('PS_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('PS_CLIENT_SECRET')
        self.logger = logging.getLogger(__name__)
        self.ps_path = self._find_ps_path()
        self.remote_play_path = self._find_remote_play_path()
        
        # API endpoints
        self.auth_url = "https://auth.api.sonyentertainmentnetwork.com/2.0/oauth/authorize"
        self.token_url = "https://auth.api.sonyentertainmentnetwork.com/2.0/oauth/token"
        self.base_url = "https://m.np.playstation.com/api/graphql"
        
        # Authentication tokens
        self.access_token = None
        self.refresh_token = None
        self.npsso_token = None

    def _find_ps_path(self) -> Optional[Path]:
        """Find PlayStation installed games directory"""
        try:
            if os.name == 'nt':  # Windows
                # Check common installation paths
                possible_paths = [
                    Path(os.environ['PROGRAMFILES']) / "PlayStation" / "Games",
                    Path(os.environ['PROGRAMFILES(X86)']) / "PlayStation" / "Games"
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
            elif os.name == 'posix':  # Linux/MacOS
                possible_paths = [
                    Path.home() / "Library" / "Application Support" / "PlayStation",  # macOS
                    Path.home() / ".local" / "share" / "PlayStation"  # Linux
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
        except Exception as e:
            self.logger.error(f"Failed to find PlayStation path: {e}")
        return None

    def _find_remote_play_path(self) -> Optional[Path]:
        """Find PS Remote Play installation"""
        try:
            if os.name == 'nt':  # Windows
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Sony Corporation\PS Remote Play")
                path = winreg.QueryValueEx(key, "Path")[0]
                winreg.CloseKey(key)
                return Path(path)
            elif os.name == 'posix':  # Linux/MacOS
                possible_paths = [
                    Path("/Applications/PS Remote Play.app"),  # macOS
                    Path.home() / ".local" / "share" / "playstation-remote-play"  # Linux
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
        except Exception as e:
            self.logger.error(f"Failed to find PS Remote Play path: {e}")
        return None

    def authenticate(self) -> bool:
        """Start browser-based authentication flow"""
        if not self.client_id:
            self.logger.error("PlayStation client ID not provided")
            return False

        try:
            # Start local server to handle callback
            server = HTTPServer(('localhost', 8919), OAuthCallbackHandler)
            server.auth_code = None
            
            # Construct authorization URL
            auth_params = {
                'client_id': self.client_id,
                'response_type': 'code',
                'redirect_uri': 'http://localhost:8919/callback',
                'scope': 'psn:mobile.v2.core psn:clientapp'
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
            return self._get_tokens(auth_code)

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    def _get_tokens(self, auth_code: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost:8919/callback'
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
            self.refresh_token = tokens.get('refresh_token')
            
            return bool(self.access_token)

        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")
            return False

    def get_installed_games(self) -> List[Dict[str, Any]]:
        """Get list of installed PlayStation games"""
        installed_games = []
        
        if not self.ps_path:
            return installed_games

        try:
            # Parse installation directory
            for game_dir in self.ps_path.iterdir():
                if game_dir.is_dir():
                    # Look for game metadata file
                    metadata_file = game_dir / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            game_info = {
                                'name': metadata.get('name'),
                                'title_id': metadata.get('title_id'),
                                'install_dir': str(game_dir),
                                'size': metadata.get('size'),
                                'version': metadata.get('version'),
                                'platform': 'PlayStation'
                            }
                            installed_games.append(game_info)

        except Exception as e:
            self.logger.error(f"Failed to get installed games: {e}")

        return installed_games

    def get_owned_games(self) -> List[Dict[str, Any]]:
        """Get list of owned PlayStation games"""
        if not self.access_token:
            self.logger.error("Authentication required")
            return []

        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # GraphQL query for owned games
            query = """
            query GetOwnedGames {
                libraryTitles {
                    games {
                        titleId
                        name
                        platform
                        thumbnail
                        size
                    }
                }
            }
            """
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json={'query': query}
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('libraryTitles', {}).get('games', [])

        except Exception as e:
            self.logger.error(f"Failed to get owned games: {e}")
            return []

    def launch_remote_play(self, title_id: Optional[str] = None) -> bool:
        """
        Launch PS Remote Play application
        :param title_id: Optional game title ID to launch directly
        :return: True if launch successful
        """
        if not self.remote_play_path:
            self.logger.error("PS Remote Play not found")
            return False

        try:
            if os.name == 'nt':
                exe_path = self.remote_play_path / "RemotePlay.exe"
                args = [str(exe_path)]
                if title_id:
                    args.extend(['--launch-game', title_id])
                subprocess.Popen(args)
            else:
                # macOS/Linux
                if title_id:
                    subprocess.Popen(['open', '-a', 'PS Remote Play', f'--args --launch-game {title_id}'])
                else:
                    subprocess.Popen(['open', '-a', 'PS Remote Play'])
            return True

        except Exception as e:
            self.logger.error(f"Failed to launch Remote Play: {e}")
            return False

    def download_to_console(self, title_id: str) -> bool:
        """
        Initiate download of a game to the connected PlayStation console
        :param title_id: PlayStation game title ID
        :return: True if download initiated successfully
        """
        if not self.access_token:
            self.logger.error("Authentication required")
            return False

        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # GraphQL mutation to start download
            mutation = """
            mutation StartDownload($titleId: String!) {
                startDownload(titleId: $titleId) {
                    success
                    message
                }
            }
            """
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json={
                    'query': mutation,
                    'variables': {'titleId': title_id}
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('startDownload', {}).get('success', False)

        except Exception as e:
            self.logger.error(f"Failed to initiate download: {e}")
            return False

# Example usage:
if __name__ == "__main__":
    # Initialize PlayStation API
    ps = PlayStationAPI()
    
    # Authenticate (opens browser)
    if ps.authenticate():
        print("Authentication successful!")
        
        # Get installed games
        installed = ps.get_installed_games()
        print(f"\nFound {len(installed)} installed PlayStation games:")
        for game in installed:
            print(f"- {game['name']} (Title ID: {game['title_id']})")
            
        # Get owned games (requires authentication)
        owned = ps.get_owned_games()
        print(f"\nFound {len(owned)} owned PlayStation games")
        
        # Launch Remote Play
        ps.launch_remote_play()