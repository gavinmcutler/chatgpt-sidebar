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
        else:
            # Reload settings from config when showing
            self._reload_settings()
        self.setCurrentIndex(1)
    
    def _reload_settings(self) -> None:
        """Reload all settings from config into UI controls."""
        # General settings
        self.chk_launch_startup.setChecked(self.config.get_autostart())
        self.chk_start_docked.setChecked(self.config.is_docked())
        self.chk_always_on_top.setChecked(self.config.get_always_on_top())
        
        current_edge = self.config.get_edge()
        if current_edge == AppBarEdge.LEFT:
            self.radio_left.setChecked(True)
        else:
            self.radio_right.setChecked(True)
        
        # Update both slider and spinbox for width
        width_percent = self.config.get_width_percent()
        self.width_spinbox.setValue(width_percent)
        self.width_slider.setValue(width_percent // 5)
        
        # Storage settings
        self.chk_stay_signed_in.setChecked(self.config.get_stay_signed_in())
        
        # Appearance settings
        current_theme = self.config.get_theme()
        if current_theme == "system":
            self.radio_system.setChecked(True)
        elif current_theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)
        
        self.opacity_slider.setValue(int(self.config.get_opacity() * 100))
        
        current_fontsize = self.config.get_font_size()
        if current_fontsize == "small":
            self.radio_small.setChecked(True)
        elif current_fontsize == "medium":
            self.radio_medium.setChecked(True)
        else:
            self.radio_large.setChecked(True)
        
        # Disable Apply button after reloading
        self.btn_apply.setEnabled(False)
    
    # -------------------------------------------------------------------------
    # Settings UI construction
    # -------------------------------------------------------------------------
    
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
        
        # Create fixed footer with buttons
        footer = self._create_settings_footer()
        settings_layout.addWidget(footer)
    
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
        self._create_appearance_section(content_layout)
        self._create_storage_section(content_layout)
        
        # Add spacer at the end
        content_layout.addStretch()
        
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
    
    def _create_appearance_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the appearance settings section.
        
        Args:
            parent_layout: Parent layout to add section to
        """
        # Appearance group box
        appearance_group = QGroupBox("Appearance")
        appearance_group.setStyleSheet(f"""
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
        
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(12)
        appearance_layout.setContentsMargins(10, 15, 10, 10)
        
        # Add appearance controls
        self._add_theme_settings(appearance_layout)
        self._add_opacity_settings(appearance_layout)
        self._add_font_size_settings(appearance_layout)
        
        # Add stretch
        appearance_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        parent_layout.addWidget(appearance_group)
    
    def _add_theme_settings(self, layout: QVBoxLayout) -> None:
        """Add theme selection settings."""
        label = QLabel("Theme")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout.setSpacing(15)
        
        self.theme_group = QButtonGroup()
        self.radio_system = QRadioButton("Match system")
        self.radio_light = QRadioButton("Light")
        self.radio_dark = QRadioButton("Dark")
        
        self.radio_system.setStyleSheet(self._get_radio_stylesheet())
        self.radio_light.setStyleSheet(self._get_radio_stylesheet())
        self.radio_dark.setStyleSheet(self._get_radio_stylesheet())
        
        self.theme_group.addButton(self.radio_system, 0)
        self.theme_group.addButton(self.radio_light, 1)
        self.theme_group.addButton(self.radio_dark, 2)
        
        current_theme = self.config.get_theme()
        if current_theme == "system":
            self.radio_system.setChecked(True)
        elif current_theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)
        
        theme_layout.addWidget(self.radio_system)
        theme_layout.addWidget(self.radio_light)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addStretch()
        
        layout.addWidget(theme_widget)
        layout.addSpacing(8)
    
    def _add_opacity_settings(self, layout: QVBoxLayout) -> None:
        """Add opacity/transparency settings."""
        label = QLabel("Transparency / Opacity")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(8)
        
        self.opacity_slider = QSlider(QtCore.Qt.Horizontal)
        self.opacity_slider.setMinimum(50)  # 50% minimum
        self.opacity_slider.setMaximum(100)  # 100% maximum
        self.opacity_slider.setValue(int(self.config.get_opacity() * 100))
        self.opacity_slider.setStyleSheet(self._get_slider_stylesheet())
        
        self.opacity_label = QLabel(f"{int(self.config.get_opacity() * 100)}%")
        self.opacity_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['fg']};
                font-size: 11px;
                min-width: 40px;
            }}
        """)
        
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        
        layout.addWidget(opacity_widget)
        layout.addSpacing(8)
    
    def _add_font_size_settings(self, layout: QVBoxLayout) -> None:
        """Add font size settings."""
        label = QLabel("Font size for chat text")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        fontsize_widget = QWidget()
        fontsize_layout = QHBoxLayout(fontsize_widget)
        fontsize_layout.setContentsMargins(0, 0, 0, 0)
        fontsize_layout.setSpacing(15)
        
        self.fontsize_group = QButtonGroup()
        self.radio_small = QRadioButton("Small")
        self.radio_medium = QRadioButton("Medium")
        self.radio_large = QRadioButton("Large")
        
        self.radio_small.setStyleSheet(self._get_radio_stylesheet())
        self.radio_medium.setStyleSheet(self._get_radio_stylesheet())
        self.radio_large.setStyleSheet(self._get_radio_stylesheet())
        
        self.fontsize_group.addButton(self.radio_small, 0)
        self.fontsize_group.addButton(self.radio_medium, 1)
        self.fontsize_group.addButton(self.radio_large, 2)
        
        current_fontsize = self.config.get_font_size()
        if current_fontsize == "small":
            self.radio_small.setChecked(True)
        elif current_fontsize == "medium":
            self.radio_medium.setChecked(True)
        else:
            self.radio_large.setChecked(True)
        
        fontsize_layout.addWidget(self.radio_small)
        fontsize_layout.addWidget(self.radio_medium)
        fontsize_layout.addWidget(self.radio_large)
        fontsize_layout.addStretch()
        
        layout.addWidget(fontsize_widget)
        layout.addSpacing(8)
    
    def _create_storage_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the storage settings section.
        
        Args:
            parent_layout: Parent layout to add section to
        """
        # Storage group box
        storage_group = QGroupBox("Storage")
        storage_group.setStyleSheet(f"""
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
        
        storage_layout = QVBoxLayout(storage_group)
        storage_layout.setSpacing(12)
        storage_layout.setContentsMargins(10, 15, 10, 10)
        
        # Add storage controls
        self._add_stay_signed_in_settings(storage_layout)
        self._add_sign_out_button(storage_layout)
        
        # Add stretch
        storage_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        parent_layout.addWidget(storage_group)
    
    def _add_stay_signed_in_settings(self, layout: QVBoxLayout) -> None:
        """Add stay signed in settings."""
        label = QLabel("Session")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        self.chk_stay_signed_in = QCheckBox("Stay signed in")
        self.chk_stay_signed_in.setStyleSheet(self._get_checkbox_stylesheet())
        self.chk_stay_signed_in.setChecked(self.config.get_stay_signed_in())
        layout.addWidget(self.chk_stay_signed_in)
        
        layout.addSpacing(8)
    
    def _add_sign_out_button(self, layout: QVBoxLayout) -> None:
        """Add sign out button."""
        label = QLabel("Account")
        label.setStyleSheet(self._get_label_stylesheet())
        layout.addWidget(label)
        
        self.btn_sign_out = QPushButton("Sign out")
        self.btn_sign_out.setStyleSheet(f"""
            QPushButton {{
                color: {self.colors['fg']};
                background-color: {self.colors['panel']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {self.colors['hover']};
                border: 1px solid #d13438;
            }}
            QPushButton:pressed {{
                background-color: {self.colors['pressed']};
            }}
        """)
        self.btn_sign_out.clicked.connect(self._on_sign_out)
        layout.addWidget(self.btn_sign_out)
        
        layout.addSpacing(8)
    
    def _create_settings_footer(self) -> QFrame:
        """Create fixed footer with Apply and Restore buttons.
        
        Returns:
            QFrame: Footer frame with buttons
        """
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['panel']};
                border-top: 1px solid {self.colors['border']};
            }}
        """)
        
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 10, 15, 10)
        footer_layout.setSpacing(10)
        
        self.btn_restore_default = QPushButton("Restore to Default")
        self.btn_restore_default.setStyleSheet(self._get_button_stylesheet())
        self.btn_restore_default.clicked.connect(self._on_restore_defaults)
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet(self._get_button_stylesheet())
        self.btn_apply.clicked.connect(self._on_apply_settings)
        
        footer_layout.addWidget(self.btn_restore_default)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_apply)
        
        # Connect all controls to enable Apply button when changed
        self._connect_change_handlers()
        
        return footer
    
    # -------------------------------------------------------------------------
    # Stylesheet methods
    # -------------------------------------------------------------------------
    
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
    
    # -------------------------------------------------------------------------
    # Settings event handlers
    # -------------------------------------------------------------------------
    
    def _connect_change_handlers(self) -> None:
        """Connect all setting controls to enable Apply button on change."""
        # General section
        self.chk_launch_startup.stateChanged.connect(self._on_setting_changed)
        self.chk_start_docked.stateChanged.connect(self._on_setting_changed)
        self.position_group.buttonClicked.connect(self._on_setting_changed)
        self.width_slider.valueChanged.connect(self._on_setting_changed)
        self.chk_always_on_top.stateChanged.connect(self._on_setting_changed)
        
        # Appearance section
        self.theme_group.buttonClicked.connect(self._on_setting_changed)
        self.opacity_slider.valueChanged.connect(self._on_setting_changed)
        self.fontsize_group.buttonClicked.connect(self._on_setting_changed)
        
        # Storage section
        self.chk_stay_signed_in.stateChanged.connect(self._on_setting_changed)
    
    def _on_setting_changed(self) -> None:
        """Enable Apply button when a setting is changed."""
        self.btn_apply.setEnabled(True)
    
    def _on_apply_settings(self) -> None:
        """Apply and save all settings."""
        logger.info("Applying settings...")
        
        # General settings
        self.config.set_autostart(self.chk_launch_startup.isChecked())
        self.config.set_docked(self.chk_start_docked.isChecked())
        self.config.set_edge(self.position_group.checkedId())
        self.config.set_width_percent(self.width_spinbox.value())
        self.config.set_always_on_top(self.chk_always_on_top.isChecked())
        
        # Appearance settings
        if self.radio_system.isChecked():
            self.config.set_theme("system")
        elif self.radio_light.isChecked():
            self.config.set_theme("light")
        else:
            self.config.set_theme("dark")
        
        self.config.set_opacity(self.opacity_slider.value() / 100.0)
        
        if self.radio_small.isChecked():
            self.config.set_font_size("small")
        elif self.radio_medium.isChecked():
            self.config.set_font_size("medium")
        else:
            self.config.set_font_size("large")
        
        # Storage settings
        self.config.set_stay_signed_in(self.chk_stay_signed_in.isChecked())
        
        # Emit signal with changed settings
        changed_settings = {
            'autostart': self.chk_launch_startup.isChecked(),
            'docked': self.chk_start_docked.isChecked(),
            'edge': self.position_group.checkedId(),
            'width_percent': self.width_spinbox.value(),
            'always_on_top': self.chk_always_on_top.isChecked(),
            'theme': self.config.get_theme(),
            'opacity': self.config.get_opacity(),
            'font_size': self.config.get_font_size(),
            'stay_signed_in': self.chk_stay_signed_in.isChecked(),
        }
        self.settings_changed.emit(changed_settings)
        
        # Disable Apply button after saving
        self.btn_apply.setEnabled(False)
        logger.info("Settings applied successfully")
    
    def _on_restore_defaults(self) -> None:
        """Restore all settings to default values."""
        logger.info("Restoring default settings...")
        
        # General defaults
        self.chk_launch_startup.setChecked(False)
        self.chk_start_docked.setChecked(True)
        self.radio_left.setChecked(True)
        self.width_slider.setValue(4)  # 20%
        self.chk_always_on_top.setChecked(True)
        
        # Appearance defaults
        self.radio_system.setChecked(True)
        self.opacity_slider.setValue(100)
        self.radio_medium.setChecked(True)
        
        # Storage defaults
        self.chk_stay_signed_in.setChecked(True)
        
        # Enable Apply button so user can save defaults
        self.btn_apply.setEnabled(True)
        logger.info("Default settings restored (click Apply to save)")
    
    def _on_sign_out(self) -> None:
        """Handle sign out button click."""
        # Emit signal to main window to sign out
        self.settings_changed.emit({'sign_out': True})
        logger.info("User requested to sign out")

