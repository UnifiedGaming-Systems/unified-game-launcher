# src/core/library.py

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import json
import logging
from .game_manager import Platform, GameInfo, GameInstallation

@dataclass
class GameContent:
    """Represents DLC or additional content for a game"""
    content_id: str
    name: str
    platform: Platform
    installed: bool
    size: int

class ContentType(Enum):
    BASE_GAME = "base"
    DLC = "dlc"
    EXPANSION = "expansion"
    SEASON_PASS = "season_pass"

class UnifiedLibrary:
    def __init__(self, game_manager, config_path: Optional[Path] = None):
        """
        Initialize the unified library
        :param game_manager: Instance of GameManager
        :param config_path: Optional path to config directory
        """
        self.logger = logging.getLogger(__name__)
        self.game_manager = game_manager
        self.config_path = config_path or Path.home() / ".unified_launcher"
        self.config_path.mkdir(exist_ok=True)
        
        # Dictionary to track owned content across platforms
        self.owned_content: Dict[str, Dict[Platform, Set[str]]] = {}
        # Dictionary to track shared installations
        self.shared_installations: Dict[str, Dict[Platform, Path]] = {}
        
        self._load_content_mappings()

    def _load_content_mappings(self):
        """Load content mappings from config file"""
        mapping_file = self.config_path / "content_mappings.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    data = json.load(f)
                    self.owned_content = {
                        game: {
                            Platform(p): set(content_ids)
                            for p, content_ids in platforms.items()
                        }
                        for game, platforms in data.get('owned_content', {}).items()
                    }
                    self.shared_installations = {
                        game: {
                            Platform(p): Path(path)
                            for p, path in platforms.items()
                        }
                        for game, platforms in data.get('shared_installations', {}).items()
                    }
            except Exception as e:
                self.logger.error(f"Failed to load content mappings: {e}")

    def save_content_mappings(self):
        """Save content mappings to config file"""
        mapping_file = self.config_path / "content_mappings.json"
        try:
            data = {
                'owned_content': {
                    game: {
                        p.value: list(content_ids)
                        for p, content_ids in platforms.items()
                    }
                    for game, platforms in self.owned_content.items()
                },
                'shared_installations': {
                    game: {
                        p.value: str(path)
                        for p, path in platforms.items()
                    }
                    for game, platforms in self.shared_installations.items()
                }
            }
            with open(mapping_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save content mappings: {e}")

    def register_owned_content(self, game_name: str, platform: Platform, content_ids: List[str]):
        """Register owned content for a game on a specific platform"""
        if game_name not in self.owned_content:
            self.owned_content[game_name] = {}
        if platform not in self.owned_content[game_name]:
            self.owned_content[game_name][platform] = set()
        self.owned_content[game_name][platform].update(content_ids)
        self.save_content_mappings()

    def setup_shared_installation(self, game_name: str, platforms: List[Platform], install_path: Path):
        """Setup a shared installation for a game across multiple platforms"""
        if game_name not in self.shared_installations:
            self.shared_installations[game_name] = {}
        
        for platform in platforms:
            self.shared_installations[game_name][platform] = install_path
        
        self.save_content_mappings()

    def get_available_platforms(self, game_name: str) -> List[Platform]:
        """Get list of platforms where the game is owned"""
        if game_name not in self.game_manager.games:
            return []
        return list(self.game_manager.games[game_name].platforms.keys())

    def get_owned_content(self, game_name: str, platform: Platform) -> List[str]:
        """Get list of owned content IDs for a game on a specific platform"""
        if game_name not in self.owned_content:
            return []
        return list(self.owned_content.get(game_name, {}).get(platform, set()))

    def is_cloud_gaming_available(self, game_name: str) -> Dict[Platform, bool]:
        """Check cloud gaming availability for a game"""
        result = {}
        game_info = self.game_manager.games.get(game_name)
        if not game_info:
            return result

        # Check Xbox Cloud Gaming availability
        if Platform.XBOX in game_info.platforms:
            result[Platform.XBOX] = True  # Could be enhanced with actual Xbox Cloud Gaming API check

        # Check PlayStation Remote Play availability
        if Platform.PLAYSTATION in game_info.platforms:
            result[Platform.PLAYSTATION] = True  # Could be enhanced with PS Remote Play availability check

        return result

    def get_installation_size(self, game_name: str) -> Dict[Platform, int]:
        """Get installation size across platforms"""
        result = {}
        game_info = self.game_manager.games.get(game_name)
        if not game_info:
            return result

        for platform, installation in game_info.installations.items():
            result[platform] = installation.size
        return result

    def optimize_storage(self, game_name: str) -> Optional[Platform]:
        """
        Determine optimal platform for installation based on owned content and available space
        Returns recommended platform for installation
        """
        if game_name not in self.game_manager.games:
            return None

        game_info = self.game_manager.games[game_name]
        platforms = self.get_available_platforms(game_name)
        
        if not platforms:
            return None

        # Simple logic: prefer platform with most owned content
        max_content = 0
        optimal_platform = None
        
        for platform in platforms:
            content_count = len(self.get_owned_content(game_name, platform))
            if content_count > max_content:
                max_content = content_count
                optimal_platform = platform

        return optimal_platform or platforms[0]