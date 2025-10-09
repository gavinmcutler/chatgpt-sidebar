"""Main sidebar UI with webview and settings."""

from typing import Dict, Optional
from PySide6 import QtCore
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame, QLabel,
    QPushButton, QCheckBox, QSlider, QSpinBox, QRadioButton, QButtonGroup,
    QGroupBox, QSpacerItem, QSizePolicy, QScrollArea
)
from PySide6.QtGui import QIcon

from ..platform.appbar_win import AppBarEdge
from ..utils.logging import get_logger


logger = get_logger(__name__)


class Sidebar(QStackedWidget):
    """Stacked widget containing webview and settings."""
    
    # Signals for settings changes
    settings_changed = Signal(dict)  # Emits dict of changed settings
    
    def __init__(self, web_widget: QWidget, colors: Dict[str, str], icons: Dict[str, QIcon], config, parent=None) -> None:
        """Initialize the sidebar.
        
        Args:
            web_widget: Web engine widget to display
            colors: Theme color palette
            icons: Icon dictionary
            config: Configuration manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.colors = colors
        self.icons = icons
        self.config = config
        
        # Add web view as first page (index 0)
        self.addWidget(web_widget)
        
        # Settings view will be created on demand
        self._settings_view: Optional[QWidget] = None
    
    def show_webview(self) -> None:
        """Show the webview page."""
        self.setCurrentIndex(0)
    
    def show_settings(self) -> None:
        """Show the settings page."""
        if self._settings_view is None:
            self._create_settings_view()
            self.addWidget(self._settings_view)
        self.setCurrentIndex(1)
    
    def _create_settings_view(self) -> None:
        """Create the settings view."""
        from ..platform.appbar_win import AppBarEdge
        
        self._settings_view = QWidget()
        settings_layout = QVBoxLayout(self._settings_view)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(0)
        
        # Create header with back button
        header = self._create_header()
        settings_layout.addWidget(header)
        
        # Create scrollable content area
        scroll_area = self._create_scroll_area()
        settings_layout.addWidget(scroll_area, 1)
    
    def _create_header(self) -> QFrame:
        """Create settings header with back button.
        
        Returns:
            QFrame: Header frame
        """
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['panel']};
                border-bottom: 1px solid {self.colors['border']};
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(10)
        
        # Back button
        self.btn_back = QPushButton()
        self.btn_back.setIcon(self.icons['left'])
        self.btn_back.setToolTip("Back to chat")
        self.btn_back.setFixedSize(30, 30)
        self.btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['pressed']};
            }}
        """)
        self.btn_back.clicked.connect(self.show_webview)
        
        # Settings title
        settings_title = QLabel("Settings")
        settings_title.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['fg']};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        
        header_layout.addWidget(self.btn_back)
        header_layout.addWidget(settings_title)
        header_layout.addStretch()
        
        return header
    
    def _create_scroll_area(self) -> QScrollArea:
        """Create scrollable settings area.
        
        Returns:
            QScrollArea: Scroll area with settings
        """
        content_area = QWidget()
        content_area.setStyleSheet(f"QWidget {{ background-color: {self.colors['bg']}; }}")
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_area)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {self.colors['bg']};
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['panel']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['accent']};
            }}
        """)
        
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # Create settings sections
        self._create_general_section(content_layout)
        
        return scroll_area
    
    def _create_general_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the general settings section.
        
        Args:
            parent_layout: Parent layout to add section to
        """
        # General group box
        general_group = QGroupBox("General")
        general_group.setStyleSheet(f"""
            QGroupBox {{
                color: {self.colors['fg']};
                font-size: 14px;
                font-weight: bold;
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(12)
        general_layout.setContentsMargins(10, 15, 10, 10)
        
        # Add settings controls
        self._add_startup_settings(general_layout)
        self._add_position_settings(general_layout)
        self._add_width_settings(general_layout)
        self._add_always_on_top_settings(general_layout)
        
        # Add stretch
        general_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        parent_layout.addWidget(general_group)
        
        # Add buttons
        self._create_settings_buttons(parent_layout)
    
    def _add_startup_settings(self, layout: QVBoxLayout) -> None:
        """Add startup behavior settings."""
        label = QLabel("Startup behavior")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        self.chk_launch_startup = QCheckBox("Launch on system startup")
        self.chk_launch_startup.setStyleSheet(self._get_checkbox_stylesheet())
        self.chk_launch_startup.setChecked(self.config.get_autostart())
        layout.addWidget(self.chk_launch_startup)
        
        self.chk_start_docked = QCheckBox("Start in docked mode")
        self.chk_start_docked.setStyleSheet(self._get_checkbox_stylesheet())
        self.chk_start_docked.setChecked(self.config.is_docked())
        layout.addWidget(self.chk_start_docked)
        
        layout.addSpacing(8)
    
    def _add_position_settings(self, layout: QVBoxLayout) -> None:
        """Add position settings."""
        label = QLabel("Default position")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        position_widget = QWidget()
        position_layout = QHBoxLayout(position_widget)
        position_layout.setContentsMargins(0, 0, 0, 0)
        position_layout.setSpacing(15)
        
        self.position_group = QButtonGroup()
        self.radio_left = QRadioButton("Left")
        self.radio_right = QRadioButton("Right")
        
        self.radio_left.setStyleSheet(self._get_radio_stylesheet())
        self.radio_right.setStyleSheet(self._get_radio_stylesheet())
        
        self.position_group.addButton(self.radio_left, AppBarEdge.LEFT)
        self.position_group.addButton(self.radio_right, AppBarEdge.RIGHT)
        
        current_edge = self.config.get_edge()
        if current_edge == AppBarEdge.LEFT:
            self.radio_left.setChecked(True)
        else:
            self.radio_right.setChecked(True)
        
        position_layout.addWidget(self.radio_left)
        position_layout.addWidget(self.radio_right)
        position_layout.addStretch()
        
        layout.addWidget(position_widget)
        layout.addSpacing(8)
    
    def _add_width_settings(self, layout: QVBoxLayout) -> None:
        """Add width settings."""
        label = QLabel("Default width")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        width_widget = QWidget()
        width_layout = QHBoxLayout(width_widget)
        width_layout.setContentsMargins(0, 0, 0, 0)
        width_layout.setSpacing(8)
        
        self.width_slider = QSlider(QtCore.Qt.Horizontal)
        self.width_slider.setMinimum(2)
        self.width_slider.setMaximum(10)
        self.width_slider.setValue(self.config.get_width_percent() // 5)
        self.width_slider.setStyleSheet(self._get_slider_stylesheet())
        self.width_slider.setMaximumWidth(120)
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setMinimum(10)
        self.width_spinbox.setMaximum(50)
        self.width_spinbox.setSingleStep(5)
        self.width_spinbox.setValue(self.config.get_width_percent())
        self.width_spinbox.setSuffix("%")
        self.width_spinbox.setStyleSheet(self._get_spinbox_stylesheet())
        self.width_spinbox.setMaximumWidth(60)
        
        self.width_slider.valueChanged.connect(lambda v: self.width_spinbox.setValue(v * 5))
        self.width_spinbox.valueChanged.connect(lambda v: self.width_slider.setValue(v // 5))
        
        width_layout.addWidget(self.width_slider, 1)
        width_layout.addWidget(self.width_spinbox)
        
        layout.addWidget(width_widget)
        layout.addSpacing(8)
    
    def _add_always_on_top_settings(self, layout: QVBoxLayout) -> None:
        """Add always on top settings."""
        label = QLabel("Always on top")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        self.chk_always_on_top = QCheckBox("Keep sidebar above other windows")
        self.chk_always_on_top.setStyleSheet(self._get_checkbox_stylesheet())
        self.chk_always_on_top.setChecked(self.config.get_always_on_top())
        layout.addWidget(self.chk_always_on_top)
        
        layout.addSpacing(8)
    
    def _create_settings_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Create Apply and Restore buttons."""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(10, 15, 10, 10)
        button_layout.setSpacing(10)
        
        self.btn_restore_default = QPushButton("Restore to Default")
        self.btn_restore_default.setStyleSheet(self._get_button_stylesheet())
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet(self._get_button_stylesheet())
        
        button_layout.addWidget(self.btn_restore_default)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_apply)
        
        parent_layout.addWidget(button_widget)
    
    # Stylesheet methods
    def _get_label_stylesheet(self) -> str:
        return f"""
            QLabel {{
                color: {self.colors['fg']};
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 5px;
            }}
        """
    
    def _get_checkbox_stylesheet(self) -> str:
        return f"""
            QCheckBox {{
                color: {self.colors['fg']};
                font-size: 11px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['border']};
                border-radius: 3px;
                background-color: {self.colors['panel']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['accent']};
                border: 1px solid {self.colors['accent']};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {self.colors['accent']};
            }}
        """
    
    def _get_radio_stylesheet(self) -> str:
        return f"""
            QRadioButton {{
                color: {self.colors['fg']};
                font-size: 11px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['panel']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.colors['accent']};
                border: 1px solid {self.colors['accent']};
            }}
            QRadioButton::indicator:hover {{
                border: 1px solid {self.colors['accent']};
            }}
        """
    
    def _get_slider_stylesheet(self) -> str:
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.colors['border']};
                height: 6px;
                background: {self.colors['panel']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.colors['accent']};
                border: 1px solid {self.colors['accent']};
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.colors['accent']};
            }}
        """
    
    def _get_spinbox_stylesheet(self) -> str:
        return f"""
            QSpinBox {{
                color: {self.colors['fg']};
                background-color: {self.colors['panel']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
            }}
            QSpinBox:focus {{
                border: 1px solid {self.colors['accent']};
            }}
        """
    
    def _get_button_stylesheet(self) -> str:
        return f"""
            QPushButton {{
                color: {self.colors['fg']};
                background-color: {self.colors['panel']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['pressed']};
            }}
            QPushButton:disabled {{
                color: {self.colors['border']};
                background-color: {self.colors['bg']};
                border: 1px solid {self.colors['border']};
            }}
            QPushButton:enabled {{
                border: 1px solid {self.colors['accent']};
            }}
        """

