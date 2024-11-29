# src/api/epic_api.py

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import winreg
import requests
from datetime import datetime, timezone

class EpicAPI:
    def __init__(self):
        """Initialize Epic Games API wrapper"""
        self.logger = logging.getLogger(__name__)
        self.epic_path = self._find_epic_path()
        self.manifest_path = self._get_manifest_path()

    def _find_epic_path(self) -> Optional[Path]:
        """Find Epic Games installation directory"""
        try:
            if os.name == 'nt':  # Windows
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher")
                path = winreg.QueryValueEx(key, "AppDataPath")[0]
                winreg.CloseKey(key)
                return Path(path)
            elif os.name == 'posix':  # Linux/MacOS
                possible_paths = [
                    Path.home() / ".config/Epic",
                    Path.home() / "Library/Application Support/Epic"
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
        except Exception as e:
            self.logger.error(f"Failed to find Epic Games path: {e}")
        return None

    def _get_manifest_path(self) -> Optional[Path]:
        """Get the path to Epic Games manifest files"""
        if not self.epic_path:
            return None
        
        if os.name == 'nt':
            return self.epic_path.parent / "EpicGamesLauncher" / "Data" / "Manifests"
        else:
            return self.epic_path / "Manifests"

    def get_installed_games(self) -> List[Dict[str, Any]]:
        """Get list of installed Epic Games and their locations"""
        installed_games = []
        
        if not self.manifest_path or not self.manifest_path.exists():
            self.logger.error("Epic Games manifest path not found")
            return installed_games

        # Parse all .item manifest files
        for manifest_file in self.manifest_path.glob("*.item"):
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    
                    # Extract relevant information
                    game_info = {
                        'app_name': manifest_data.get('DisplayName'),
                        'app_id': manifest_data.get('AppName'),
                        'install_dir': manifest_data.get('InstallLocation'),
                        'install_size': manifest_data.get('InstallSize'),
                        'version': manifest_data.get('AppVersion'),
                        'launch_exe': manifest_data.get('LaunchExecutable'),
                        'manifest_path': str(manifest_file),
                        'is_dlc': manifest_data.get('bIsDLC', False),
                        'last_updated': manifest_data.get('LastUpdated'),
                        'platform': 'Epic'
                    }
                    
                    # Only add if it's not DLC
                    if not game_info['is_dlc']:
                        installed_games.append(game_info)
            except Exception as e:
                self.logger.error(f"Failed to parse manifest {manifest_file}: {e}")

        return installed_games

    def get_owned_games(self, auth_token: str) -> List[Dict[str, Any]]:
        """
        Get list of owned games (requires Epic Games authentication)
        Note: This is a placeholder as Epic doesn't provide a public API
        """
        self.logger.warning("Epic Games owned games API not implemented - requires OAuth authentication")
        return []

    def launch_game(self, app_name: str) -> bool:
        """
        Launch an Epic Games game using the com.epicgames.launcher:// protocol
        :param app_name: Epic Games application name
        :return: True if launch command was successful
        """
        try:
            import webbrowser
            # Format: com.epicgames.launcher://apps/[AppName]?action=launch
            launch_url = f"com.epicgames.launcher://apps/{app_name}?action=launch"
            return webbrowser.open(launch_url)
        except Exception as e:
            self.logger.error(f"Failed to launch game {app_name}: {e}")
            return False

    def get_library_folders(self) -> List[Path]:
        """Get all Epic Games library folders"""
        library_folders = []
        
        if not self.epic_path:
            return library_folders

        try:
            # Check for custom installation locations in Epic's config
            config_path = self.epic_path / "UnrealEngineLauncher" / "Config" / "LauncherInstallationList.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for installation in data.get('InstallationList', []):
                        path = installation.get('InstallLocation')
                        if path:
                            library_folders.append(Path(path))
        except Exception as e:
            self.logger.error(f"Failed to parse Epic Games library folders: {e}")

        return library_folders

    def get_game_details(self, app_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a game from manifest
        :param app_name: Epic Games application name
        :return: Game details or None if not found
        """
        if not self.manifest_path:
            return None

        try:
            # Search through manifests for the game
            for manifest_file in self.manifest_path.glob("*.item"):
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    if manifest_data.get('AppName') == app_name:
                        return {
                            'name': manifest_data.get('DisplayName'),
                            'publisher': manifest_data.get('MainGamePublisher'),
                            'version': manifest_data.get('AppVersion'),
                            'install_size': manifest_data.get('InstallSize'),
                            'install_path': manifest_data.get('InstallLocation'),
                            'launch_exe': manifest_data.get('LaunchExecutable'),
                            'requires_launcher': manifest_data.get('bRequiresLauncher', True)
                        }
        except Exception as e:
            self.logger.error(f"Failed to get game details for {app_name}: {e}")
        
        return None

# Example usage:
if __name__ == "__main__":
    # Initialize Epic API
    epic = EpicAPI()
    
    # Get installed games
    installed = epic.get_installed_games()
    print(f"Found {len(installed)} installed Epic games:")
    for game in installed:
        print(f"- {game['app_name']} (App ID: {game['app_id']})")
        
        # Get additional details
        details = epic.get_game_details(game['app_id'])
        if details:
            print(f"  Version: {details['version']}")
            print(f"  Install Size: {details['install_size']} bytes")
            print(f"  Launch EXE: {details['launch_exe']}")