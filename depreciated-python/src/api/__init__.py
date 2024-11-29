# src/api/__init__.py

from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .steam_api import SteamAPI
from .epic_api import EpicAPI
from .gog_api import GOGAPI
from .xbox_api import XboxAPI
from .playstation_api import PlayStationAPI

class UnifiedGameAPI:
    """Unified interface for managing multiple gaming platform APIs"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified gaming API
        
        :param config: Dictionary containing API keys and credentials:
            {
                'steam_api_key': str,
                'epic_client_id': str,
                'epic_client_secret': str,
                'gog_client_id': str,
                'gog_client_secret': str,
                'xbox_client_id': str,
                'xbox_client_secret': str,
                'ps_client_id': str,
                'ps_client_secret': str
            }
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Initialize platform APIs
        self.steam = SteamAPI(api_key=self.config.get('steam_api_key'))
        self.epic = EpicAPI(
            client_id=self.config.get('epic_client_id'),
            client_secret=self.config.get('epic_client_secret')
        )
        self.gog = GOGAPI(
            client_id=self.config.get('gog_client_id'),
            client_secret=self.config.get('gog_client_secret')
        )
        self.xbox = XboxAPI(
            client_id=self.config.get('xbox_client_id'),
            client_secret=self.config.get('xbox_client_secret')
        )
        self.playstation = PlayStationAPI(
            client_id=self.config.get('ps_client_id'),
            client_secret=self.config.get('ps_client_secret')
        )
        
        # Track authenticated platforms
        self.authenticated_platforms = set()

    async def authenticate_platform(self, platform: str) -> bool:
        """
        Authenticate with a specific gaming platform
        
        :param platform: Platform identifier ('steam', 'epic', 'gog', 'xbox', 'playstation')
        :return: True if authentication successful
        """
        try:
            if platform == 'steam':
                # Steam doesn't require OAuth authentication
                if self.config.get('steam_api_key'):
                    self.authenticated_platforms.add('steam')
                    return True
            elif platform == 'epic':
                # Epic authentication
                success = await self.epic.authenticate()
                if success:
                    self.authenticated_platforms.add('epic')
                return success
            elif platform == 'gog':
                # GOG authentication
                success = self.gog.authenticate()
                if success:
                    self.authenticated_platforms.add('gog')
                return success
            elif platform == 'xbox':
                # Xbox authentication
                success = self.xbox.authenticate_with_browser()
                if success:
                    self.authenticated_platforms.add('xbox')
                return success
            elif platform == 'playstation':
                # PlayStation authentication
                success = self.playstation.authenticate()
                if success:
                    self.authenticated_platforms.add('playstation')
                return success
            else:
                self.logger.error(f"Unknown platform: {platform}")
                return False
        except Exception as e:
            self.logger.error(f"Authentication failed for {platform}: {e}")
            return False

    def get_installed_games(self, platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get list of installed games across all or specified platforms
        
        :param platforms: List of platforms to check, or None for all platforms
        :return: List of installed games with platform information
        """
        installed_games = []
        platforms = platforms or ['steam', 'epic', 'gog', 'xbox', 'playstation']
        
        for platform in platforms:
            try:
                if platform == 'steam':
                    games = self.steam.get_installed_games()
                elif platform == 'epic':
                    games = self.epic.get_installed_games()
                elif platform == 'gog':
                    games = self.gog.get_installed_games()
                elif platform == 'xbox':
                    games = self.xbox.get_installed_games()
                elif platform == 'playstation':
                    games = self.playstation.get_installed_games()
                else:
                    continue
                
                # Add platform information to each game
                for game in games:
                    game['platform'] = platform
                    game['launch_platform'] = platform  # Default launch platform
                
                installed_games.extend(games)
                
            except Exception as e:
                self.logger.error(f"Failed to get installed games for {platform}: {e}")
        
        return installed_games

    def get_owned_games(self, platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get list of owned games across all or specified platforms
        
        :param platforms: List of platforms to check, or None for all authenticated platforms
        :return: List of owned games with platform information
        """
        owned_games = []
        platforms = platforms or list(self.authenticated_platforms)
        
        for platform in platforms:
            try:
                if platform not in self.authenticated_platforms:
                    continue
                    
                if platform == 'steam':
                    games = self.steam.get_owned_games(steam_id=self.config.get('steam_id', ''))
                elif platform == 'epic':
                    games = self.epic.get_owned_games()
                elif platform == 'gog':
                    games = self.gog.get_owned_games()
                elif platform == 'xbox':
                    games = self.xbox.get_owned_games()
                elif platform == 'playstation':
                    games = self.playstation.get_owned_games()
                else:
                    continue
                
                # Add platform information to each game
                for game in games:
                    game['platform'] = platform
                
                owned_games.extend(games)
                
            except Exception as e:
                self.logger.error(f"Failed to get owned games for {platform}: {e}")
        
        return owned_games

    def launch_game(self, game_id: str, platform: str) -> bool:
        """
        Launch a game using the specified platform
        
        :param game_id: Game identifier
        :param platform: Platform to launch the game from
        :return: True if launch successful
        """
        try:
            if platform == 'steam':
                return self.steam.launch_game(game_id)
            elif platform == 'epic':
                return self.epic.launch_game(game_id)
            elif platform == 'gog':
                return self.gog.launch_game(game_id)
            elif platform == 'xbox':
                return self.xbox.launch_game(game_id)
            elif platform == 'playstation':
                return self.playstation.launch_remote_play(game_id)
            else:
                self.logger.error(f"Unknown platform: {platform}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to launch game {game_id} on {platform}: {e}")
            return False

    def identify_duplicate_games(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify games owned on multiple platforms
        
        :return: Dictionary mapping game names to lists of platform-specific versions
        """
        all_games = self.get_owned_games()
        duplicates = {}
        
        # Group games by name
        for game in all_games:
            name = game.get('name', '').lower()
            if name:
                if name not in duplicates:
                    duplicates[name] = []
                duplicates[name].append(game)
        
        # Filter out non-duplicates
        return {name: versions for name, versions in duplicates.items() if len(versions) > 1}

    def get_game_details(self, game_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a game
        
        :param game_id: Game identifier
        :param platform: Platform the game is on
        :return: Game details or None if not found
        """
        try:
            if platform == 'steam':
                return self.steam.get_game_details(game_id)
            elif platform == 'epic':
                return self.epic.get_game_details(game_id)
            elif platform == 'gog':
                return self.gog.get_game_details(game_id)
            elif platform == 'xbox':
                return self.xbox.get_game_details(game_id)
            elif platform == 'playstation':
                # PlayStation API doesn't have a direct game details endpoint
                # We'll try to find it in the owned games list
                owned_games = self.playstation.get_owned_games()
                return next((game for game in owned_games if game.get('title_id') == game_id), None)
            else:
                self.logger.error(f"Unknown platform: {platform}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get game details for {game_id} on {platform}: {e}")
            return None

    def download_game(self, game_id: str, platform: str) -> bool:
        """
        Initiate game download for platforms that support it
        
        :param game_id: Game identifier
        :param platform: Platform to download from
        :return: True if download initiated successfully
        """
        try:
            if platform == 'playstation':
                return self.playstation.download_to_console(game_id)
            else:
                self.logger.error(f"Download not supported for platform: {platform}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to initiate download for {game_id} on {platform}: {e}")
            return False