from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt

from ..core.game_manager import Platform

class SettingsView(QWidget):
    def __init__(self, launcher):
        """
        Initialize the settings view
        
        :param launcher: UnifiedLauncher instance
        """
        super().__init__()
        self.launcher = launcher
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Platform Authentication Section
        self.setup_platform_auth(layout)
        
        # Application Settings Section
        self.setup_app_settings(layout)
        
        # Storage Optimization Section
        self.setup_storage_settings(layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def setup_platform_auth(self, layout):
        """
        Setup platform authentication settings
        
        :param layout: Main layout to add section to
        """
        auth_group = QGroupBox("Platform Authentication")
        auth_layout = QVBoxLayout()
        
        for platform in Platform:
            platform_layout = QHBoxLayout()
            
            # Platform label
            label = QLabel(platform.value.capitalize())
            platform_layout.addWidget(label)
            
            # Authentication status
            status_label = QLabel("Not Connected")
            status_label.setObjectName(f"{platform.value}_status")
            platform_layout.addWidget(status_label)
            
            # Connect/Disconnect button
            auth_btn = QPushButton("Connect")
            auth_btn.clicked.connect(lambda checked, p=platform.value: self.toggle_platform_auth(p))
            platform_layout.addWidget(auth_btn)
            
            auth_layout.addLayout(platform_layout)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
    
    def setup_app_settings(self, layout):
        """
        Setup general application settings
        
        :param layout: Main layout to add section to
        """
        app_group = QGroupBox("Application Settings")
        app_layout = QVBoxLayout()
        
        # Default installation path
        install_layout = QHBoxLayout()
        install_label = QLabel("Default Install Path:")
        self.install_path = QLineEdit()
        self.install_path.setText(str(self.launcher.config.get('default_install_path')))
        install_layout.addWidget(install_label)
        install_layout.addWidget(self.install_path)
        app_layout.addLayout(install_layout)
        
        # Concurrent downloads
        downloads_layout = QHBoxLayout()
        downloads_label = QLabel("Concurrent Downloads:")
        self.downloads_spinner = QComboBox()
        self.downloads_spinner.addItems([str(i) for i in range(1, 6)])
        self.downloads_spinner.setCurrentText(str(self.launcher.config.get('concurrent_downloads', 1)))
        downloads_layout.addWidget(downloads_label)
        downloads_layout.addWidget(self.downloads_spinner)
        app_layout.addLayout(downloads_layout)
        
        # Checkboxes for toggleable settings
        self.auto_update_check = QCheckBox("Automatic Updates")
        self.auto_update_check.setChecked(self.launcher.config.get('auto_update', True))
        app_layout.addWidget(self.auto_update_check)
        
        self.cloud_gaming_check = QCheckBox("Cloud Gaming Enabled")
        self.cloud_gaming_check.setChecked(self.launcher.config.get('cloud_gaming_enabled', True))
        app_layout.addWidget(self.cloud_gaming_check)
        
        # Save settings button
        save_btn = QPushButton("Save Application Settings")
        save_btn.clicked.connect(self.save_app_settings)
        app_layout.addWidget(save_btn)
        
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)
    
    def setup_storage_settings(self, layout):
        """
        Setup storage optimization settings
        
        :param layout: Main layout to add section to
        """
        storage_group = QGroupBox("Storage Optimization")
        storage_layout = QVBoxLayout()
        
        # Storage optimization toggle
        self.storage_optimize_check = QCheckBox("Enable Storage Optimization")
        self.storage_optimize_check.setChecked(self.launcher.config.get('storage_optimization', True))
        storage_layout.addWidget(self.storage_optimize_check)
        
        # Platform installation priority
        priority_layout = QHBoxLayout()
        priority_label = QLabel("Platform Installation Priority:")
        self.platform_priority = QComboBox()
        
        # Get current platform priorities
        priorities = self.launcher.config.get('platform_priorities', {})
        sorted_platforms = sorted(priorities.items(), key=lambda x: x[1])
        
        for platform, _ in sorted_platforms:
            self.platform_priority.addItem(platform.capitalize())
        
        priority_layout.addWidget(priority_label)
        priority_layout.addWidget(self.platform_priority)
        storage_layout.addLayout(priority_layout)
        
        # Save storage settings button
        save_storage_btn = QPushButton("Save Storage Settings")
        save_storage_btn.clicked.connect(self.save_storage_settings)
        storage_layout.addWidget(save_storage_btn)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
    
    def toggle_platform_auth(self, platform):
        """
        Toggle authentication for a specific platform
        
        :param platform: Platform to authenticate
        """
        try:
            # Attempt to authenticate
            if self.launcher.auth.authenticate(platform):
                status_label = self.findChild(QLabel, f"{platform}_status")
                if status_label:
                    status_label.setText("Connected")
            else:
                # Handle authentication failure
                status_label = self.findChild(QLabel, f"{platform}_status")
                if status_label:
                    status_label.setText("Connection Failed")
        except Exception as e:
            print(f"Authentication error for {platform}: {e}")
    
    def save_app_settings(self):
        """Save application