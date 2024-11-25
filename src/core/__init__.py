# src/core/__init__.py

import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .auth import UnifiedAuth
from .game_manager import GameManager, Platform
from .library import UnifiedLibrary

class UnifiedLauncher:
    """
    Main initialization class for the Unified Game Launcher
    Coordinates configuration, authentication, game management, and library functions
    """
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize core components of the Unified Game Launcher
        
        :param config_dir: Optional custom configuration directory
        """
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Initialize core components
        self.config = Config(config_dir)
        self.auth = UnifiedAuth(config_dir)
        self.game_manager = GameManager(config_dir)
        self.library = UnifiedLibrary(self.game_manager, config_dir)

        # Register platform APIs and authentication
        self._setup_platform_integrations()

    def _setup_platform_integrations(self):
        """
        Setup and register platform-specific APIs and authentication
        """
        platforms = [
            Platform.STEAM,
            Platform.EPIC,
            Platform.XBOX,
            Platform.PLAYSTATION,
            Platform.GOG
        ]

        for platform in platforms:
            try:
                # Dynamically import platform-specific API
                module = __import__(f'..api.{platform.value}_api', fromlist=['PlatformAPI'])
                api_class = getattr(module, 'PlatformAPI')
                
                # Initialize API with config and authentication
                api_instance = api_class(
                    self.config.get_api_key(platform.value),
                    self.config.get_install_path(platform.value)
                )

                # Register API with game manager and authentication
                self.game_manager.register_platform_api(platform, api_instance)
                self.auth.register_platform_api(platform.value, api_instance)
            except ImportError as e:
                self.logger.warning(f"Could not load {platform.value} API: {e}")
            except Exception as e:
                self.logger.error(f"Error setting up {platform.value} integration: {e}")

    def initialize(self):
        """
        Perform full initialization of the launcher
        Scans for installed games, authenticates platforms
        """
        try:
            # Authenticate platforms
            for platform in Platform:
                self.auth.authenticate(platform.value)

            # Scan for installed games
            self.game_manager.scan_installations()

            self.logger.info("Unified Launcher initialized successfully")
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")

    def sync_library(self):
        """
        Synchronize game library across platforms
        """
        try:
            # Rescan installations
            self.game_manager.scan_installations()

            # Sync owned content
            for game_name in self.game_manager.games:
                for platform in self.game_manager.games[game_name].platforms:
                    # TODO: Implement content synchronization logic
                    pass

            self.logger.info("Library synchronized")
        except Exception as e:
            self.logger.error(f"Library synchronization failed: {e}")

# Optional entry point for direct initialization
def initialize_launcher(config_dir: Optional[Path] = None) -> UnifiedLauncher:
    """
    Convenience function to initialize the Unified Launcher
    
    :param config_dir: Optional custom configuration directory
    :return: Initialized UnifiedLauncher instance
    """
    launcher = UnifiedLauncher(config_dir)
    launcher.initialize()
    return launcher