# src/utils/logger.py

import os
import logging
from datetime import datetime
from typing import Optional, Union, Dict, Any
import traceback

class AppLogger:
    """
    Comprehensive logger for the Unified Game Launcher application.
    Supports multi-platform logging with structured, context-aware logging.
    """
    
    _instance = None
    
    def __new__(cls, 
                log_dir: Optional[str] = None, 
                log_level: int = logging.INFO):
        """
        Singleton implementation to ensure a single logger instance.
        
        Args:
            log_dir (Optional[str]): Directory to store log files. 
                                     If None, uses 'logs' in the project root.
            log_level (int): Logging level from logging module
        """
        if not cls._instance:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._initialize(log_dir, log_level)
        return cls._instance
    
    def _initialize(self, 
                    log_dir: Optional[str] = None, 
                    log_level: int = logging.INFO):
        """Initialize logging configuration"""
        # Determine log directory
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'logs'
        )
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('UnifiedGameLauncher')
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Log format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File Handler with daily rotation
        log_filename = f"game_launcher_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, log_filename)
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug messages with optional context"""
        extra = {'context': context} if context else None
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info messages with optional context"""
        extra = {'context': context} if context else None
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning messages with optional context"""
        extra = {'context': context} if context else None
        self.logger.warning(message, extra=extra)
    
    def error(self, 
              message: str, 
              exc_info: Optional[Union[bool, Exception]] = None, 
              context: Optional[Dict[str, Any]] = None):
        """
        Log error messages with comprehensive error tracking
        
        Args:
            message (str): Error message
            exc_info (Optional[Union[bool, Exception]]): Exception to log
            context (Optional[Dict]): Additional context information
        """
        # Prepare context for error logging
        error_context = context or {}
        
        # Add exception details if provided
        if exc_info:
            if isinstance(exc_info, Exception):
                error_context['exception_type'] = type(exc_info).__name__
                error_context['exception_details'] = str(exc_info)
                error_context['traceback'] = traceback.format_exc()
            else:
                error_context['traceback'] = traceback.format_exc()
        
        extra = {'context': error_context} if error_context else None
        self.logger.error(message, exc_info=bool(exc_info), extra=extra)
    
    def critical(self, 
                 message: str, 
                 exc_info: Optional[Union[bool, Exception]] = None, 
                 context: Optional[Dict[str, Any]] = None):
        """
        Log critical messages with comprehensive error tracking
        
        Args:
            message (str): Critical message
            exc_info (Optional[Union[bool, Exception]]): Exception to log
            context (Optional[Dict]): Additional context information
        """
        # Similar to error logging, but with critical severity
        error_context = context or {}
        
        if exc_info:
            if isinstance(exc_info, Exception):
                error_context['exception_type'] = type(exc_info).__name__
                error_context['exception_details'] = str(exc_info)
                error_context['traceback'] = traceback.format_exc()
            else:
                error_context['traceback'] = traceback.format_exc()
        
        extra = {'context': error_context} if error_context else None
        self.logger.critical(message, exc_info=bool(exc_info), extra=extra)
    
    def log_platform_action(self, 
                            platform: str, 
                            action: str, 
                            details: Optional[Dict[str, Any]] = None):
        """
        Log platform-specific actions with additional context
        
        Args:
            platform (str): Gaming platform (Steam, Epic, Xbox, etc.)
            action (str): Action performed
            details (Optional[Dict]): Additional action details
        """
        context = {
            'platform': platform,
            'action': action,
            **(details or {})
        }
        self.info(f"{platform} - {action}", context=context)

# Convenience function to get logger instance
def get_logger(
    log_dir: Optional[str] = None, 
    log_level: int = logging.INFO
) -> AppLogger:
    """
    Convenience function to get or create logger instance
    
    Args:
        log_dir (Optional[str]): Directory to store log files
        log_level (int): Logging level
    
    Returns:
        AppLogger: Configured logger instance
    """
    return AppLogger(log_dir, log_level)

# Example usage
if __name__ == "__main__":
    # Get logger instance
    logger = get_logger()
    
    # Log different types of messages
    logger.debug("Debugging information")
    
    logger.log_platform_action("Steam", "Game Installation", {
        "game_name": "Destiny 2",
        "install_path": "/games/destiny2"
    })
    
    try:
        # Simulate an error
        raise ValueError("Example platform integration error")
    except Exception as e:
        logger.error("Platform integration failed", exc_info=e, context={
            "platform": "Epic Games",
            "action": "Game Validation"
        })