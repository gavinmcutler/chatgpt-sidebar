"""Top control bar UI component."""

from typing import Dict
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtGui import QIcon

from .theme import ThemeManager


class TopBar(QFrame):
    """Top control bar with navigation and action buttons."""
    
    # Signals
    screenshot_clicked = Signal()
    settings_clicked = Signal()
    toggle_side_clicked = Signal()
    toggle_dock_clicked = Signal()
    exit_clicked = Signal()
    
    def __init__(self, colors: Dict[str, str], parent=None) -> None:
        """Initialize the top control bar.
        
        Args:
            colors: Theme color palette
            parent: Parent widget
        """
        super().__init__(parent)
        self.colors = colors
        self.icons = ThemeManager.get_control_icons(colors)
        
        # Configure frame
        self.setFrameShape(QFrame.NoFrame)
        self.setFixedHeight(34)
        self.setStyleSheet(ThemeManager.create_control_bar_stylesheet(colors))
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        # Create buttons
        self.btn_screenshot = QPushButton()
        self.btn_settings = QPushButton()
        self.btn_toggle_side = QPushButton()
        self.btn_toggle_dock = QPushButton()
        self.btn_exit = QPushButton()
        
        # Set initial icons and tooltips
        self._update_icons()
        
        # Connect signals
        self.btn_screenshot.clicked.connect(self.screenshot_clicked.emit)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        self.btn_toggle_side.clicked.connect(self.toggle_side_clicked.emit)
        self.btn_toggle_dock.clicked.connect(self.toggle_dock_clicked.emit)
        self.btn_exit.clicked.connect(self.exit_clicked.emit)
        
        # Add buttons to layout
        layout.addWidget(self.btn_screenshot)
        layout.addWidget(self.btn_settings)
        layout.addStretch()
        layout.addWidget(self.btn_toggle_side)
        layout.addWidget(self.btn_toggle_dock)
        layout.addWidget(self.btn_exit)
    
    def _update_icons(self) -> None:
        """Update button icons and tooltips."""
        # Screenshot button
        self.btn_screenshot.setIcon(self.icons['camera'])
        self.btn_screenshot.setToolTip("Attach a screenshot to the current chat")
        self.btn_screenshot.setAccessibleName("Screenshot")
        
        # Settings button
        self.btn_settings.setIcon(self.icons['settings'])
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setAccessibleName("Settings")
        
        # Exit button
        self.btn_exit.setIcon(self.icons['exit'])
        self.btn_exit.setToolTip("Exit")
    
    def update_side_button(self, edge: str) -> None:
        """Update the side toggle button based on current edge.
        
        Args:
            edge: Current edge ("left" or "right")
        """
        if edge.lower() == "left":
            self.btn_toggle_side.setIcon(self.icons['right'])
            self.btn_toggle_side.setToolTip("Switch to right")
        else:
            self.btn_toggle_side.setIcon(self.icons['left'])
            self.btn_toggle_side.setToolTip("Switch to left")
    
    def update_dock_button(self, is_docked: bool) -> None:
        """Update the dock toggle button based on docked state.
        
        Args:
            is_docked: Whether the sidebar is currently docked
        """
        if is_docked:
            self.btn_toggle_dock.setIcon(self.icons['undock'])
            self.btn_toggle_dock.setToolTip("Pop out")
        else:
            self.btn_toggle_dock.setIcon(self.icons['dock'])
            self.btn_toggle_dock.setToolTip("Dock")

