# src/ui/settings_view.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QGroupBox, QMessageBox)
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
        
        # Account Linking Section
        self.setup_account_linking(layout)
        
        # Platform Authentication Section
        self.setup_platform_auth(layout)
        
        # Application Settings Section
        self.setup_app_settings(layout)
        
        # Advanced Game Management Section
        self.setup_game_management(layout)
        
        # Storage Optimization Section
        self.setup_storage_settings(layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def setup_account_linking(self, layout):
        """
        Setup account linking section for different platforms
        
        :param layout: Main layout to add section to
        """
        account_group = QGroupBox("Account Linking")
        account_layout = QVBoxLayout()
        
        # Linking status and buttons for each platform
        for platform in Platform:
            platform_layout = QHBoxLayout()
            
            # Platform label
            label = QLabel(platform.value.capitalize())
            platform_layout.addWidget(label)
            
            # Account username/email
            account_input = QLineEdit()
            account_input.setPlaceholderText(f"Enter {platform.value} username")
            platform_layout.addWidget(account_input)
            
            # Link/Unlink button
            link_btn = QPushButton("Link Account")
            link_btn.clicked.connect(lambda checked, p=platform.value, input=account_input: 
                                     self.link_platform_account(p, input.text()))
            platform_layout.addWidget(link_btn)
            
            account_layout.addLayout(platform_layout)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
    
    def link_platform_account(self, platform, account_info):
        """
        Link a platform account
        
        :param platform: Platform to link
        :param account_info: Account username or email
        """
        try:
            # Validate and link account
            if self.launcher.auth.link_account(platform, account_info):
                QMessageBox.information(self, "Account Linked", 
                                        f"{platform.capitalize()} account linked successfully!")
            else:
                QMessageBox.warning(self, "Link Failed", 
                                    f"Failed to link {platform.capitalize()} account.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error linking account: {str(e)}")
    
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
    
    def setup_game_management(self, layout):
        """
        Setup advanced game management settings
        
        :param layout: Main layout to add section to
        """
        game_group = QGroupBox("Game Management")
        game_layout = QVBoxLayout()
        
        # Platform preference for multi-platform games
        multi_platform_layout = QHBoxLayout()
        multi_platform_label = QLabel("Preferred Platform for Multi-Platform Games:")
        self.multi_platform_combo = QComboBox()
        
        # Populate with available platforms
        for platform in Platform:
            self.multi_platform_combo.addItem(platform.value.capitalize())
        
        # Set default from config
        default_platform = self.launcher.config.get('default_multi_platform', Platform.STEAM.value)
        self.multi_platform_combo.setCurrentText(default_platform.capitalize())
        
        multi_platform_layout.addWidget(multi_platform_label)
        multi_platform_layout.addWidget(self.multi_platform_combo)
        game_layout.addLayout(multi_platform_layout)
        
        # Option to auto-sync game saves across platforms
        self.auto_sync_saves = QCheckBox("Automatically Sync Game Saves")
        self.auto_sync_saves.setChecked(self.launcher.config.get('auto_sync_saves', False))
        game_layout.addWidget(self.auto_sync_saves)
        
        # Save game management settings button
        save_game_btn = QPushButton("Save Game Management Settings")
        save_game_btn.clicked.connect(self.save_game_management_settings)
        game_layout.addWidget(save_game_btn)
        
        game_group.setLayout(game_layout)
        layout.addWidget(game_group)
    
    def save_game_management_settings(self):
        """Save game management configuration settings"""
        try:
            # Update multi-platform game preference
            self.launcher.config.set('default_multi_platform', 
                                     self.multi_platform_combo.currentText().lower())
            
            # Update save sync preference
            self.launcher.config.set('auto_sync_saves', 
                                     self.auto_sync_saves.isChecked())
            
            # Save configuration
            self.launcher.config.save()
            
            QMessageBox.information(self, "Settings Saved", 
                                    "Game management settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
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
    
    def save_app_settings(self):
        """Save application configuration settings"""
        try:
            # Update install path
            self.launcher.config.set('default_install_path', self.install_path.text())
            
            # Update concurrent downloads
            self.launcher.config.set('concurrent_downloads', 
                                     int(self.downloads_spinner.currentText()))
            
            # Update auto update setting
            self.launcher.config.set('auto_update', 
                                     self.auto_update_check.isChecked())
            
            # Update cloud gaming setting
            self.launcher.config.set('cloud_gaming_enabled', 
                                     self.cloud_gaming_check.isChecked())
            
            # Save configuration
            self.launcher.config.save()
            
            QMessageBox.information(self, "Settings Saved", 
                                    "Application settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
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
    
    def save_storage_settings(self):
        """Save storage configuration settings"""
        try:
            # Update storage optimization setting
            self.launcher.config.set('storage_optimization', 
                                     self.storage_optimize_check.isChecked())
            
            # Update platform installation priority
            current_priorities = self.launcher.config.get('platform_priorities', {})
            selected_platform = self.platform_priority.currentText().lower()
            
            # Adjust priority for selected platform
            for platform in current_priorities:
                if platform == selected_platform:
                    current_priorities[platform] = 1  # Highest priority
                else:
                    current_priorities[platform] += 1  # Increment other priorities
            
            self.launcher.config.set('platform_priorities', current_priorities)
            
            # Save configuration
            self.launcher.config.save()
            
            QMessageBox.information(self, "Settings Saved", 
                                    "Storage settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")