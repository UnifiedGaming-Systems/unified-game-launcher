# src/api/steam_api.py

import os
import vdf
import json
import logging
from typing import Dict, List, Optional, Any
import requests
from pathlib import Path
import winreg  # For Windows Steam installation detection

class SteamAPI:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Steam API wrapper
        :param api_key: Steam Web API key (optional for some features)
        """
        self.api_key = api_key or os.getenv('STEAM_API_KEY')
        self.base_url = "https://api.steampowered.com"
        self.logger = logging.getLogger(__name__)
        self.steam_path = self._find_steam_path()

    def _find_steam_path(self) -> Optional[Path]:
        """Find Steam installation directory"""
        try:
            if os.name == 'nt':  # Windows
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
                path = winreg.QueryValueEx(key, "InstallPath")[0]
                winreg.CloseKey(key)
                return Path(path)
            elif os.name == 'posix':  # Linux/MacOS
                possible_paths = [
                    Path.home() / ".steam",
                    Path.home() / ".local/share/Steam",
                    Path("/usr/share/steam"),
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
        except Exception as e:
            self.logger.error(f"Failed to find Steam path: {e}")
        return None

    def get_owned_games(self, steam_id: str) -> List[Dict[str, Any]]:
        """
        Get list of owned games for a Steam user
        :param steam_id: Steam user ID
        :return: List of games with details
        """
        if not self.api_key:
            raise ValueError("Steam API key is required for this operation")

        endpoint = f"{self.base_url}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("response", {}).get("games", [])
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch owned games: {e}")
            return []

    def get_library_folders(self) -> List[Path]:
        """Get all Steam library folders"""
        if not self.steam_path:
            return []

        library_folders_path = self.steam_path / "steamapps/libraryfolders.vdf"
        try:
            with open(library_folders_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
                folders = []
                
                # Parse library folders from VDF
                for key, value in data.get('libraryfolders', {}).items():
                    if key.isdigit() and isinstance(value, dict):
                        path = value.get('path')
                        if path:
                            folders.append(Path(path))
                
                return folders
        except Exception as e:
            self.logger.error(f"Failed to parse library folders: {e}")
            return []

    def get_installed_games(self) -> List[Dict[str, Any]]:
        """Get list of installed games and their locations"""
        installed_games = []
        library_folders = self.get_library_folders()

        for folder in library_folders:
            apps_path = folder / "steamapps"
            if not apps_path.exists():
                continue

            # Parse all manifest files
            for manifest in apps_path.glob("appmanifest_*.acf"):
                try:
                    with open(manifest, 'r', encoding='utf-8') as f:
                        app_data = vdf.load(f)
                        app_state = app_data.get('AppState', {})
                        
                        game_info = {
                            'app_id': app_state.get('appid'),
                            'name': app_state.get('name'),
                            'install_dir': str(apps_path / "common" / app_state.get('installdir', '')),
                            'size_on_disk': app_state.get('SizeOnDisk'),
                            'last_updated': app_state.get('LastUpdated'),
                            'state_flags': app_state.get('StateFlags'),
                            'manifest_path': str(manifest)
                        }
                        installed_games.append(game_info)
                except Exception as e:
                    self.logger.error(f"Failed to parse manifest {manifest}: {e}")

        return installed_games

    def get_game_details(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a game
        :param app_id: Steam application ID
        :return: Game details or None if not found
        """
        endpoint = f"https://store.steampowered.com/api/appdetails"
        params = {"appids": app_id}

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get(str(app_id), {}).get('data')
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch game details for {app_id}: {e}")
            return None

    def launch_game(self, app_id: str) -> bool:
        """
        Launch a Steam game using the Steam protocol
        :param app_id: Steam application ID
        :return: True if launch command was successful
        """
        try:
            import webbrowser
            return webbrowser.open(f"steam://rungameid/{app_id}")
        except Exception as e:
            self.logger.error(f"Failed to launch game {app_id}: {e}")
            return False

# Example usage:
if __name__ == "__main__":
    # Initialize with API key from environment variable
    steam = SteamAPI()
    
    # Get installed games
    installed = steam.get_installed_games()
    print(f"Found {len(installed)} installed games:")
    for game in installed:
        print(f"- {game['name']} (App ID: {game['app_id']})")
        
    # Example: Get owned games for a user
    # steam_id = "YOUR_STEAM_ID"
    # owned_games = steam.get_owned_games(steam_id)
    # print(f"\nOwned games: {len(owned_games)}")