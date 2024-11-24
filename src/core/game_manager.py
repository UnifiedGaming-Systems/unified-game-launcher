# src/core/game_manager.py

import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
from dataclasses import dataclass
from enum import Enum

class Platform(Enum):
    STEAM = "steam"
    EPIC = "epic"
    XBOX = "xbox"
    PLAYSTATION = "playstation"
    GOG = "gog"

@dataclass
class GameInstallation:
    platform: Platform
    install_path: Path
    executable_path: Path
    app_id: str
    version: str
    size: int

class GameInfo:
    def __init__(self, name: str, platforms: Dict[Platform, str]):
        self.name = name
        self.platforms = platforms  # Dictionary of Platform -> app_id
        self.installations: Dict[Platform, GameInstallation] = {}
        self.active_platform: Optional[Platform] = None
        
    def add_installation(self, installation: GameInstallation):
        self.installations[installation.platform] = installation
        if not self.active_platform:
            self.active_platform = installation.platform

class GameManager:
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the game manager
        :param config_path: Path to config directory
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or Path.home() / ".unified_launcher"
        self.config_path.mkdir(exist_ok=True)
        
        self.games: Dict[str, GameInfo] = {}
        self.platform_apis = {}
        self._load_game_mappings()
        
    def _load_game_mappings(self):
        """Load game mappings from config file"""
        mapping_file = self.config_path / "game_mappings.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
                    for game_name, data in mappings.items():
                        platforms = {Platform(p): id for p, id in data['platforms'].items()}
                        self.games[game_name] = GameInfo(game_name, platforms)
            except Exception as e:
                self.logger.error(f"Failed to load game mappings: {e}")

    def save_game_mappings(self):
        """Save game mappings to config file"""
        mapping_file = self.config_path / "game_mappings.json"
        try:
            mappings = {}
            for game_name, game_info in self.games.items():
                mappings[game_name] = {
                    'platforms': {p.value: id for p, id in game_info.platforms.items()}
                }
            with open(mapping_file, 'w') as f:
                json.dump(mappings, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save game mappings: {e}")

    def register_platform_api(self, platform: Platform, api_instance: Any):
        """Register a platform API instance"""
        self.platform_apis[platform] = api_instance

    def scan_installations(self):
        """Scan for installed games across all platforms"""
        for platform, api in self.platform_apis.items():
            try:
                installed_games = api.get_installed_games()
                for game in installed_games:
                    self._process_installation(platform, game)
            except Exception as e:
                self.logger.error(f"Failed to scan {platform.value} installations: {e}")

    def _process_installation(self, platform: Platform, game_data: Dict[str, Any]):
        """Process a game installation from a platform"""
        game_name = game_data.get('name') or game_data.get('app_name')
        if not game_name:
            return

        # Create or update game info
        if game_name not in self.games:
            self.games[game_name] = GameInfo(game_name, {platform: game_data['app_id']})
        else:
            self.games[game_name].platforms[platform] = game_data['app_id']

        # Create installation info
        install_path = Path(game_data['install_dir'])
        exe_path = install_path
        if platform == Platform.EPIC:
            exe_path = install_path / game_data['launch_exe']
        elif platform == Platform.STEAM:
            # Steam usually has the executable in the game folder
            exe_path = install_path / f"{game_name}.exe"

        installation = GameInstallation(
            platform=platform,
            install_path=install_path,
            executable_path=exe_path,
            app_id=game_data['app_id'],
            version=game_data.get('version', '1.0'),
            size=int(game_data.get('size_on_disk', 0))
        )
        self.games[game_name].add_installation(installation)

    def launch_game(self, game_name: str, platform: Optional[Platform] = None) -> bool:
        """
        Launch a game using the specified platform
        :param game_name: Name of the game to launch
        :param platform: Optional platform override
        :return: True if launch successful
        """
        if game_name not in self.games:
            self.logger.error(f"Game {game_name} not found")
            return False

        game_info = self.games[game_name]
        launch_platform = platform or game_info.active_platform

        if not launch_platform:
            self.logger.error(f"No platform specified for {game_name}")
            return False

        try:
            api = self.platform_apis.get(launch_platform)
            if not api:
                self.logger.error(f"No API found for platform {launch_platform}")
                return False

            app_id = game_info.platforms.get(launch_platform)
            if not app_id:
                self.logger.error(f"No app ID found for {game_name} on {launch_platform}")
                return False

            # Handle cloud gaming platforms
            if launch_platform in [Platform.XBOX, Platform.PLAYSTATION]:
                return self._launch_cloud_game(api, app_id, launch_platform)
            
            return api.launch_game(app_id)

        except Exception as e:
            self.logger.error(f"Failed to launch {game_name}: {e}")
            return False

    def _launch_cloud_game(self, api: Any, app_id: str, platform: Platform) -> bool:
        """Handle launching cloud gaming sessions"""
        try:
            if platform == Platform.XBOX:
                # Launch Xbox Cloud Gaming in default browser
                return api.launch_cloud_game(app_id)
            elif platform == Platform.PLAYSTATION:
                # Launch PS Remote Play
                return api.launch_remote_play(app_id)
            return False
        except Exception as e:
            self.logger.error(f"Failed to launch cloud game: {e}")
            return False

    def get_games_by_platform(self, platform: Optional[Platform] = None) -> List[str]:
        """
        Get list of games, optionally filtered by platform
        :param platform: Optional platform filter
        :return: List of game names
        """
        if not platform:
            return list(self.games.keys())
        
        return [
            name for name, info in self.games.items()
            if platform in info.platforms
        ]

    def set_active_platform(self, game_name: str, platform: Platform) -> bool:
        """
        Set the active platform for a game
        :param game_name: Name of the game
        :param platform: Platform to set as active
        :return: True if successful
        """
        if game_name not in self.games:
            return False
            
        game_info = self.games[game_name]
        if platform not in game_info.platforms:
            return False
            
        game_info.active_platform = platform
        return True

    def get_installation_info(self, game_name: str) -> Optional[GameInstallation]:
        """Get installation info for a game"""
        if game_name not in self.games:
            return None
            
        game_info = self.games[game_name]
        if not game_info.active_platform:
            return None
            
        return game_info.installations.get(game_info.active_platform)