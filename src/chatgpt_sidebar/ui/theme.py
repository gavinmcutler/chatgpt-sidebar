"""Theme management and styling."""

import logging
from typing import Dict, Optional
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QPalette, QIcon

from ..constants import (
    BUTTON_SIZE_PX,
    BUTTON_PADDING_PX,
)


logger = logging.getLogger(__name__)


# Theme color palettes
DARK_THEME = {
    'bg': '#1a1a1a',
    'panel': '#2d2d2d',
    'fg': '#ffffff',
    'border': '#404040',
    'hover': '#404040',
    'pressed': '#505050',
    'accent': '#0078d4'
}

LIGHT_THEME = {
    'bg': '#ffffff',
    'panel': '#f8f8f8',
    'fg': '#323130',
    'border': '#d1d1d1',
    'hover': '#f3f2f1',
    'pressed': '#e1dfdd',
    'accent': '#0078d4'
}


class ThemeManager:
    """Manages theme detection and styling for the application."""
    
    @staticmethod
    def detect_theme_colors(theme_preference: str = "system") -> Dict[str, str]:
        """Detect or select theme and return color palette.
        
        Args:
            theme_preference: User's theme preference ("system", "light", or "dark")
        
        Returns:
            Dict[str, str]: Color palette for the selected/detected theme
        """
        # If user has chosen a specific theme, use it
        if theme_preference == "light":
            logger.info("Using light theme (user preference)")
            return LIGHT_THEME
        elif theme_preference == "dark":
            logger.info("Using dark theme (user preference)")
            return DARK_THEME
        
        # Otherwise, detect system theme
        app = QApplication.instance()
        if app is None:
            logger.warning("No QApplication instance found for theme detection")
            return LIGHT_THEME
        
        # Try to detect dark theme
        is_dark = False
        try:
            if hasattr(app.styleHints(), 'colorScheme'):
                is_dark = app.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark
            else:
                # Fallback: check window color lightness
                palette = app.palette()
                window_color = palette.color(QPalette.Window)
                is_dark = window_color.value() < 128
        except Exception as e:
            logger.warning(f"Failed to detect theme, using light theme as fallback: {e}")
            is_dark = False
        
        theme = DARK_THEME if is_dark else LIGHT_THEME
        logger.info(f"Detected {'dark' if is_dark else 'light'} theme (system)")
        return theme
    
    @staticmethod
    def create_control_bar_stylesheet(colors: Dict[str, str]) -> str:
        """Create stylesheet for control bar based on theme colors.
        
        Args:
            colors: Color palette dictionary
            
        Returns:
            str: CSS stylesheet
        """
        return f"""
            QFrame {{
                background-color: {colors['panel']};
                border-top: 1px solid {colors['border']};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: {BUTTON_PADDING_PX}px;
                min-width: {BUTTON_SIZE_PX - 4}px;
                min-height: {BUTTON_SIZE_PX - 4}px;
                max-width: {BUTTON_SIZE_PX}px;
                max-height: {BUTTON_SIZE_PX}px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {colors['hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['pressed']};
            }}
            QPushButton:focus {{
                outline: none;
                border: none;
            }}
        """
    
    @staticmethod
    def recolor_pixmap(pixmap: QtGui.QPixmap, color: str) -> QtGui.QPixmap:
        """Recolor a pixmap to the specified color.
        
        Args:
            pixmap: Source pixmap
            color: Target color
            
        Returns:
            QtGui.QPixmap: Recolored pixmap
        """
        try:
            result = QtGui.QPixmap(pixmap.size())
            result.fill(QtCore.Qt.transparent)
            
            painter = QtGui.QPainter(result)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QtGui.QColor(color))
            painter.setBrush(QtGui.QColor(color))
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            return result
        except Exception as e:
            logger.warning(f"Failed to recolor pixmap: {e}")
            return pixmap
    
    @staticmethod
    def create_geometric_icon(icon_type: str, colors: Dict[str, str]) -> QIcon:
        """Create a simple geometric icon.
        
        Args:
            icon_type: Type of icon to create
            colors: Color palette
            
        Returns:
            QIcon: Created icon
        """
        pixmap = QtGui.QPixmap(20, 20)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        pen = QtGui.QPen(QtGui.QColor(colors['fg']))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtGui.QColor(colors['fg']))
        
        center_x, center_y = 10, 10
        
        if icon_type == 'left':
            painter.drawPolygon([
                QtCore.QPoint(center_x + 3, center_y - 5),
                QtCore.QPoint(center_x - 3, center_y),
                QtCore.QPoint(center_x + 3, center_y + 5)
            ])
        elif icon_type == 'right':
            painter.drawPolygon([
                QtCore.QPoint(center_x - 3, center_y - 5),
                QtCore.QPoint(center_x + 3, center_y),
                QtCore.QPoint(center_x - 3, center_y + 5)
            ])
        elif icon_type == 'dock':
            painter.drawRect(center_x - 5, center_y - 5, 10, 10)
        elif icon_type == 'undock':
            painter.drawRect(center_x - 3, center_y - 3, 7, 7)
            painter.drawRect(center_x - 1, center_y - 1, 7, 7)
        elif icon_type == 'exit':
            painter.drawLine(center_x - 4, center_y - 4, center_x + 4, center_y + 4)
            painter.drawLine(center_x + 4, center_y - 4, center_x - 4, center_y + 4)
        elif icon_type == 'camera':
            painter.drawEllipse(center_x - 5, center_y - 3, 10, 7)
            painter.drawRect(center_x - 2, center_y + 2, 4, 2)
            painter.drawEllipse(center_x - 2, center_y - 2, 5, 4)
        elif icon_type == 'settings':
            painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)
            painter.drawEllipse(center_x - 2, center_y - 2, 4, 4)
            painter.drawRect(center_x - 1, center_y - 7, 2, 3)
            painter.drawRect(center_x - 1, center_y + 4, 2, 3)
            painter.drawRect(center_x - 7, center_y - 1, 3, 2)
            painter.drawRect(center_x + 4, center_y - 1, 3, 2)
        
        painter.end()
        return QIcon(pixmap)
    
    @staticmethod
    def create_icon(theme_name: str, colors: Dict[str, str]) -> QIcon:
        """Create icon with proper fallback.
        
        Args:
            theme_name: Icon theme name
            colors: Color palette
            
        Returns:
            QIcon: Created icon
        """
        # Try system theme first
        icon = QIcon.fromTheme(theme_name)
        if not icon.isNull():
            return icon
        
        # Try built-in Qt icons
        builtin_icons = {
            'go-previous': QStyle.SP_ArrowLeft,
            'go-next': QStyle.SP_ArrowRight,
            'view-fullscreen': QStyle.SP_TitleBarNormalButton,
            'view-restore': QStyle.SP_TitleBarNormalButton,
            'window-close': QStyle.SP_TitleBarCloseButton,
            'camera-photo': QStyle.SP_FileDialogDetailedView,
            'settings': QStyle.SP_ComputerIcon
        }
        
        if theme_name in builtin_icons:
            pixmap = QApplication.style().standardPixmap(builtin_icons[theme_name])
            if not pixmap.isNull():
                colored_pixmap = ThemeManager.recolor_pixmap(pixmap, colors['fg'])
                return QIcon(colored_pixmap)
        
        # Fallback to geometric icons
        return ThemeManager.create_geometric_icon(theme_name, colors)
    
    @staticmethod
    def get_control_icons(colors: Dict[str, str]) -> Dict[str, QIcon]:
        """Get all control icons with theme adaptation.
        
        Args:
            colors: Color palette
            
        Returns:
            Dict[str, QIcon]: Dictionary of icon names to QIcon objects
        """
        return {
            'left': ThemeManager.create_icon('go-previous', colors),
            'right': ThemeManager.create_icon('go-next', colors),
            'dock': ThemeManager.create_icon('view-fullscreen', colors),
            'undock': ThemeManager.create_icon('view-restore', colors),
            'exit': ThemeManager.create_icon('window-close', colors),
            'camera': ThemeManager.create_icon('camera-photo', colors),
            'settings': ThemeManager.create_geometric_icon('settings', colors)
        }

