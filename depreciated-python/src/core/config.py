from typing import Dict, Any, Optional
from pathlib import Path
import json
import os
from dotenv import load_dotenv
import logging

class Config:
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager
        :param config_dir: Optional custom config directory
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = config_dir or Path.home() / ".unified_launcher"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        
        # Load environment variables
        load_dotenv()
        
        # Default configuration
        self.defaults = {
            "steam_api_key": os.getenv("STEAM_API_KEY", ""),
            "epic_client_id": os.getenv("EPIC_CLIENT_ID", ""),
            "epic_client_secret": os.getenv("EPIC_CLIENT_SECRET", ""),
            "xbox_client_id": os.getenv("XBOX_CLIENT_ID", ""),
            "ps_client_id": os.getenv("PS_CLIENT_ID", ""),
            "default_install_path": str(Path.home() / "Games"),
            "concurrent_downloads": 1,
            "auto_update": True,
            "cloud_gaming_enabled": True,
            "storage_optimization": True,
            "platform_priorities": {
                "steam": 1,
                "epic": 2,
                "gog": 3,
                "xbox": 4,
                "playstation": 5
            }
        }
        
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    stored_config = json.load(f)
                    # Merge with defaults, preferring stored values
                    self.config = {**self.defaults, **stored_config}
            else:
                self.config = self.defaults.copy()
                self.save_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.config = self.defaults.copy()

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()

    def get_api_key(self, platform: str) -> str:
        """Get API key for specific platform"""
        key_mapping = {
            "steam": "steam_api_key",
            "epic": "epic_client_id",
            "xbox": "xbox_client_id",
            "playstation": "ps_client_id"
        }
        return self.get(key_mapping.get(platform, ""))

    def get_install_path(self, platform: Optional[str] = None) -> Path:
        """Get installation path, optionally platform-specific"""
        base_path = Path(self.get("default_install_path"))
        if platform:
            return base_path / platform
        return base_path

    def get_platform_priority(self, platform: str) -> int:
        """Get priority for platform (lower number = higher priority)"""
        priorities = self.get("platform_priorities", {})
        return priorities.get(platform, 999)