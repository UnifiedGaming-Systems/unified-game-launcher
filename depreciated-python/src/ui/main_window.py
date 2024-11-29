# src/ui/main_window.py

import sys
from PyQt6.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QStackedWidget, QSidebar)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from .library_view import LibraryView
from .settings_view import SettingsView

class MainWindow(QMainWindow):
    def __init__(self, launcher):
        """
        Initialize the main application window
        
        :param launcher: UnifiedLauncher instance
        """
        super().__init__()
        self.launcher = launcher
        
        # Window setup
        self.setWindowTitle("Unified Game Launcher")
        self.resize(1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Sidebar for navigation
        self.create_sidebar(main_layout)
        
        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Create views
        self.library_view = LibraryView(self.launcher)
        self.settings_view = SettingsView(self.launcher)
        
        # Add views to stacked widget
        self.stacked_widget.addWidget(self.library_view)
        self.stacked_widget.addWidget(self.settings_view)
        
        # Set initial view
        self.stacked_widget.setCurrentWidget(self.library_view)
    
    def create_sidebar(self, main_layout):
        """
        Create sidebar with navigation buttons
        
        :param main_layout: Main horizontal layout
        """
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(200)
        
        # Navigation buttons
        nav_buttons = [
            ("Library", self.show_library),
            ("Settings", self.show_settings)
        ]
        
        for label, slot in nav_buttons:
            button = QPushButton(label)
            button.clicked.connect(slot)
            sidebar_layout.addWidget(button)
        
        # Add stretch to push buttons to top
        sidebar_layout.addStretch()
        
        main_layout.addWidget(sidebar)
    
    def show_library(self):
        """Switch to library view"""
        self.stacked_widget.setCurrentWidget(self.library_view)
    
    def show_settings(self):
        """Switch to settings view"""
        self.stacked_widget.setCurrentWidget(self.settings_view)
    
    def refresh_library(self):
        """Refresh library view"""
        self.library_view.refresh()

def run_launcher(launcher):
    """
    Run the Unified Game Launcher application
    
    :param launcher: UnifiedLauncher instance
    """
    app = QApplication(sys.argv)
    main_window = MainWindow(launcher)
    main_window.show()
    sys.exit(app.exec())