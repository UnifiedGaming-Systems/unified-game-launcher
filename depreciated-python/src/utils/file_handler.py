import os
import shutil
import platform
import hashlib
from typing import List, Dict, Optional, Union
import psutil

from src.utils.logger import get_logger

class FileHandler:
    """
    Comprehensive file handling utility for cross-platform game management.
    Supports file operations, storage management, and game installation tracking.
    """
    
    def __init__(self, 
                 base_game_dir: Optional[str] = None, 
                 log_level: int = None):
        """
        Initialize FileHandler with optional base game directory.
        
        Args:
            base_game_dir (Optional[str]): Base directory for game installations
            log_level (Optional[int]): Logging level for file operations
        """
        # Logger setup
        self.logger = get_logger()
        
        # Determine base game installation directory
        if base_game_dir:
            self.base_game_dir = base_game_dir
        else:
            self.base_game_dir = self._get_default_game_dir()
        
        # Ensure base directory exists
        os.makedirs(self.base_game_dir, exist_ok=True)
        
        # Platform-specific separator
        self.path_sep = os.path.sep
    
    def _get_default_game_dir(self) -> str:
        """
        Determine default game installation directory based on platform.
        
        Returns:
            str: Recommended game installation path
        """
        system = platform.system().lower()
        
        if system == 'windows':
            return os.path.join(os.path.expanduser('~'), 'Games', 'UnifiedGameLauncher')
        elif system == 'darwin':  # macOS
            return os.path.join(os.path.expanduser('~'), 'Games')
        else:  # Linux
            return os.path.join(os.path.expanduser('~'), '.local', 'share', 'UnifiedGameLauncher', 'games')
    
    def create_game_directory(self, 
                               game_name: str, 
                               platform: Optional[str] = None) -> str:
        """
        Create a platform-specific game installation directory.
        
        Args:
            game_name (str): Name of the game
            platform (Optional[str]): Gaming platform (Steam, Epic, etc.)
        
        Returns:
            str: Full path to created game directory
        """
        # Sanitize game name for directory creation
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        
        # Create platform-specific subdirectory if platform is provided
        if platform:
            game_path = os.path.join(self.base_game_dir, platform, safe_game_name)
        else:
            game_path = os.path.join(self.base_game_dir, safe_game_name)
        
        os.makedirs(game_path, exist_ok=True)
        
        self.logger.log_platform_action(
            platform or 'Universal', 
            'Create Game Directory', 
            {'game_name': game_name, 'path': game_path}
        )
        
        return game_path
    
    def copy_game_files(self, 
                         source_path: str, 
                         destination_path: str, 
                         platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Copy game files with progress tracking and logging.
        
        Args:
            source_path (str): Source directory of game files
            destination_path (str): Destination directory for game files
            platforms (Optional[List[str]]): Platforms associated with the game
        
        Returns:
            Dict containing copy operation details
        """
        copy_result = {
            'total_files': 0,
            'copied_files': 0,
            'total_size': 0,
            'copied_size': 0,
            'success': False
        }
        
        try:
            # Walk through source directory
            for root, _, files in os.walk(source_path):
                for file in files:
                    src_file = os.path.join(root, file)
                    relative_path = os.path.relpath(src_file, source_path)
                    dst_file = os.path.join(destination_path, relative_path)
                    
                    # Create destination subdirectory if needed
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(src_file, dst_file)
                    
                    # Update copy results
                    copy_result['total_files'] += 1
                    copy_result['copied_files'] += 1
                    file_size = os.path.getsize(src_file)
                    copy_result['total_size'] += file_size
                    copy_result['copied_size'] += file_size
            
            copy_result['success'] = True
            
            # Log platform-specific copy action
            self.logger.log_platform_action(
                ', '.join(platforms) if platforms else 'Universal', 
                'Game Files Copy', 
                {
                    'source': source_path, 
                    'destination': destination_path,
                    'total_files': copy_result['total_files'],
                    'total_size_mb': round(copy_result['total_size'] / (1024 * 1024), 2)
                }
            )
        
        except Exception as e:
            copy_result['success'] = False
            self.logger.error(
                "Game files copy failed", 
                exc_info=e, 
                context={'source': source_path, 'destination': destination_path}
            )
        
        return copy_result
    
    def calculate_file_hash(self, 
                             file_path: str, 
                             hash_algorithm: str = 'sha256') -> str:
        """
        Calculate hash of a file for verification.
        
        Args:
            file_path (str): Path to the file
            hash_algorithm (str): Hash algorithm to use
        
        Returns:
            str: Hex digest of the file hash
        """
        hash_func = hashlib.new(hash_algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    def get_drive_space(self, path: Optional[str] = None) -> Dict[str, int]:
        """
        Get available and total drive space.
        
        Args:
            path (Optional[str]): Path to check drive space. 
                                  If None, checks base game directory.
        
        Returns:
            Dict with drive space information in bytes
        """
        check_path = path or self.base_game_dir
        
        try:
            usage = shutil.disk_usage(check_path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free
            }
        except Exception as e:
            self.logger.error(
                "Failed to retrieve drive space", 
                exc_info=e, 
                context={'path': check_path}
            )
            return {'total': 0, 'used': 0, 'free': 0}
    
    def is_game_running(self, game_name: str) -> bool:
        """
        Check if a game is currently running.
        
        Args:
            game_name (str): Name of the game to check
        
        Returns:
            bool: True if game is running, False otherwise
        """
        for proc in psutil.process_iter(['name']):
            if game_name.lower() in proc.info['name'].lower():
                return True
        return False

# Convenience function to get FileHandler instance
def get_file_handler(
    base_game_dir: Optional[str] = None, 
    log_level: Optional[int] = None
) -> FileHandler:
    """
    Convenience function to get FileHandler instance
    
    Args:
        base_game_dir (Optional[str]): Base directory for game installations
        log_level (Optional[int]): Logging level
    
    Returns:
        FileHandler: Configured file handler instance
    """
    return FileHandler(base_game_dir, log_level)

# Example usage demonstration
if __name__ == "__main__":
    # Initialize file handler
    file_handler = get_file_handler()
    
    # Demonstrate directory creation
    game_path = file_handler.create_game_directory("Destiny 2", "Steam")
    print(f"Game directory created: {game_path}")
    
    # Check drive space
    space_info = file_handler.get_drive_space()
    print(f"Free space: {space_info['free'] / (1024**3):.2f} GB")
    
    # Example file copy (mock paths)
    copy_result = file_handler.copy_game_files(
        "/source/game/files", 
        game_path, 
        platforms=["Steam", "Epic"]
    )
    print(f"Copy successful: {copy_result['success']}")