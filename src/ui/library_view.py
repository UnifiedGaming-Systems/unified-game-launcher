from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QComboBox, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt

from ..core.game_manager import Platform

class LibraryView(QWidget):
    def __init__(self, launcher):
        """
        Initialize the library view
        
        :param launcher: UnifiedLauncher instance
        """
        super().__init__()
        self.launcher = launcher
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Filter and search controls
        self.setup_controls(layout)
        
        # Game table
        self.game_table = QTableWidget()
        layout.addWidget(self.game_table)
        self.setup_game_table()
        
        # Refresh library on initialization
        self.refresh()
    
    def setup_controls(self, layout):
        """
        Setup filter and search controls
        
        :param layout: Main layout to add controls to
        """
        controls_layout = QHBoxLayout()
        
        # Platform filter
        self.platform_filter = QComboBox()
        self.platform_filter.addItem("All Platforms")
        for platform in Platform:
            self.platform_filter.addItem(platform.value.capitalize())
        self.platform_filter.currentTextChanged.connect(self.refresh)
        controls_layout.addWidget(self.platform_filter)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search games...")
        self.search_bar.textChanged.connect(self.refresh)
        controls_layout.addWidget(self.search_bar)
        
        layout.addLayout(controls_layout)
    
    def setup_game_table(self):
        """Setup game table columns and initial configuration"""
        headers = ["Game", "Platform", "Installed", "Cloud Gaming", "Actions"]
        self.game_table.setColumnCount(len(headers))
        self.game_table.setHorizontalHeaderLabels(headers)
        self.game_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    
    def refresh(self):
        """
        Refresh the game library view
        Filter games based on platform and search term
        """
        # Clear existing rows
        self.game_table.setRowCount(0)
        
        # Get filter values
        selected_platform = self.platform_filter.currentText().lower()
        search_term = self.search_bar.text().lower()
        
        # Iterate through games
        for game_name in self.launcher.game_manager.games:
            # Apply filters
            if selected_platform != "all platforms":
                platforms = [p.value for p in self.launcher.game_manager.games[game_name].platforms]
                if selected_platform not in platforms:
                    continue
            
            if search_term and search_term not in game_name.lower():
                continue
            
            # Add game to table
            row = self.game_table.rowCount()
            self.game_table.insertRow(row)
            
            # Game name
            self.game_table.setItem(row, 0, QTableWidgetItem(game_name))
            
            # Platforms
            platforms_str = ", ".join([p.value.capitalize() for p in self.launcher.game_manager.games[game_name].platforms])
            self.game_table.setItem(row, 1, QTableWidgetItem(platforms_str))
            
            # Installation status
            installed_status = "Yes" if self.launcher.game_manager.get_installation_info(game_name) else "No"
            self.game_table.setItem(row, 2, QTableWidgetItem(installed_status))
            
            # Cloud gaming availability
            cloud_gaming = self.launcher.library.is_cloud_gaming_available(game_name)
            cloud_status = ", ".join([p.value.capitalize() for p in cloud_gaming])
            self.game_table.setItem(row, 3, QTableWidgetItem(cloud_status or "N/A"))
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            
            # Launch button
            launch_btn = QPushButton("Launch")
            launch_btn.clicked.connect(lambda checked, name=game_name: self.launch_game(name))
            action_layout.addWidget(launch_btn)
            
            # Cloud gaming button
            if cloud_gaming:
                cloud_btn = QPushButton("Cloud")
                cloud_btn.clicked.connect(lambda checked, name=game_name: self.launch_cloud_game(name))
                action_layout.addWidget(cloud_btn)
            
            action_layout.setContentsMargins(0, 0, 0, 0)
            self.game_table.setCellWidget(row, 4, action_widget)
    
    def launch_game(self, game_name):
        """
        Launch a game
        
        :param game_name: Name of the game to launch
        """
        self.launcher.game_manager.launch_game(game_name)
    
    def launch_cloud_game(self, game_name):
        """
        Launch cloud gaming for a game
        
        :param game_name: Name of the game to launch in cloud
        """
        cloud_platforms = self.launcher.library.is_cloud_gaming_available(game_name)
        if cloud_platforms:
            # Prioritize Xbox Cloud Gaming or PlayStation Remote Play
            platform = list(cloud_platforms.keys())[0]
            self.launcher.game_manager.launch_game(game_name, platform)