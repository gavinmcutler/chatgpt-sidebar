"""Main window that composes all components."""

import ctypes
import sys
import winreg
from typing import Optional, Set, Tuple
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtGui import QGuiApplication

from .ui.topbar import TopBar
from .ui.sidebar import Sidebar
from .ui.theme import ThemeManager
from .platform.appbar_win import AppBarWin, AppBarEdge, AppBarNotification
from .web.engine_qtwebengine import QtWebEngine
from .settings.config import Config
from .features.screenshot import (
    find_visible_window_in_rect, capture_window_to_qimage,
    qimage_to_png_base64, hide_window, show_window
)
from .features.paste_js import build_paste_js
from .utils.logging import get_logger


logger = get_logger(__name__)


# Constants
DEFAULT_WIDTH = 420
DEFAULT_URL = "https://chat.openai.com/"
DEFAULT_TITLE = "ChatGPT Sidebar"
TOAST_DURATION = 3000
SCREENSHOT_TOAST_DURATION = 1500


class MainWindow(QWidget):
    """Main application window that composes all components."""
    
    def __init__(
        self,
        desired_width: int = DEFAULT_WIDTH,
        edge: str = "left",
        title: str = DEFAULT_TITLE,
        url: str = DEFAULT_URL,
        parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the main window.
        
        Args:
            desired_width: Initial width of the sidebar
            edge: Initial edge ("left" or "right")
            title: Window title
            url: URL to load in webview
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # Initialize configuration
        self.config = Config()
        self.desired_width = self.config.get_width(desired_width)
        self.edge_str = "left" if self.config.get_edge() == AppBarEdge.LEFT else "right"
        self.is_docked = self.config.is_docked()
        
        # Theme and colors
        self.colors = ThemeManager.detect_theme_colors()
        self.icons = ThemeManager.get_control_icons(self.colors)
        
        # Set up window flags for docked mode
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Initialize AppBar (will be set up after show())
        callback_msg = ctypes.windll.user32.RegisterWindowMessageW("APPBARMSG_CHATGPT_SIDEBAR")
        self.appbar: Optional[AppBarWin] = None
        self._callback_msg = callback_msg
        
        # Create UI layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create top bar
        self.topbar = TopBar(self.colors, self)
        self.main_layout.addWidget(self.topbar)
        
        # Create web engine
        self.engine = QtWebEngine(self)
        self.engine.navigate(url)
        
        # Create sidebar (stacked widget with webview and settings)
        self.sidebar = Sidebar(self.engine.get_widget(), self.colors, self.icons, self.config, self)
        self.main_layout.addWidget(self.sidebar, 1)
        
        # Connect topbar signals
        self.topbar.screenshot_clicked.connect(self.on_screenshot_to_chat)
        self.topbar.settings_clicked.connect(self.on_show_settings)
        self.topbar.toggle_side_clicked.connect(self.on_toggle_side)
        self.topbar.toggle_dock_clicked.connect(self.on_toggle_dock)
        self.topbar.exit_clicked.connect(self.on_exit)
        
        # Update topbar button states
        self._update_topbar_buttons()
        
        # Initialize toast system
        self._toast_label: Optional[QLabel] = None
        self._toast_timer = QTimer()
        self._toast_timer.timeout.connect(self._hide_toast)
        self._toast_timer.setSingleShot(True)
        
        # Set up drag support for undocked mode
        self._drag = False
        self._drag_pos = QtCore.QPoint()
        
        # Register AppBar after window is shown
        if self.is_docked:
            QTimer.singleShot(0, self._register_appbar)
        else:
            QTimer.singleShot(0, self._start_undocked)
    
    def _register_appbar(self) -> None:
        """Register the window as an AppBar."""
        hwnd = int(self.winId())
        self.appbar = AppBarWin(hwnd, self._callback_msg)
        self.appbar.dock(self.edge_str, self.desired_width)
        logger.info("AppBar registered and docked")
    
    def _start_undocked(self) -> None:
        """Start in undocked mode."""
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Restore geometry if available
        geometry = self.config.get_undocked_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size and center
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width = min(900, int(screen.width() * 0.8))
            height = min(1000, int(screen.height() * 0.9))
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_topbar_buttons()
    
    def _update_topbar_buttons(self) -> None:
        """Update topbar button states."""
        self.topbar.update_side_button(self.edge_str)
        self.topbar.update_dock_button(self.is_docked)
    
    # Event handlers
    def on_screenshot_to_chat(self) -> None:
        """Capture screenshot and paste into chat."""
        logger.info("Screenshot button clicked")
        try:
            if not self.appbar:
                self._show_toast("Screenshot only works in docked mode")
                return
            
            # Get opposite work area
            work_rect = self.appbar.get_opposite_work_area()
            
            # Find target window
            excluded_hwnds: Set[int] = {int(self.winId())}
            hwnd_target = find_visible_window_in_rect(work_rect, excluded_hwnds)
            
            if not hwnd_target:
                logger.warning("No window found to capture")
                self._show_toast("No window to capture in the work area.")
                return
            
            # Hide our window temporarily
            hide_window(int(self.winId()))
            try:
                img = capture_window_to_qimage(hwnd_target)
            finally:
                show_window(int(self.winId()))
            
            if img is None or img.isNull():
                logger.error("Failed to capture window image")
                self._show_toast("Couldn't capture that window.")
                return
            
            # Convert to base64
            b64 = qimage_to_png_base64(img)
            
            # Paste via JavaScript
            js = build_paste_js(b64)
            self.engine.evaluate_js(js, self._after_paste_result)
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            self._show_toast("Screenshot failed. Please try again.")
    
    def _after_paste_result(self, ok: bool) -> None:
        """Handle paste result callback."""
        if not ok:
            self._show_toast("Couldn't paste into the chat. Click the message box and retry.")
        else:
            self._show_toast("Screenshot attached.", duration_ms=SCREENSHOT_TOAST_DURATION)
    
    def on_show_settings(self) -> None:
        """Show settings view."""
        self.sidebar.show_settings()
    
    def on_toggle_side(self) -> None:
        """Toggle between left and right edge."""
        if self.edge_str == "left":
            self.edge_str = "right"
            edge_int = AppBarEdge.RIGHT
        else:
            self.edge_str = "left"
            edge_int = AppBarEdge.LEFT
        
        self.config.set_edge(edge_int)
        self._update_topbar_buttons()
        
        if self.is_docked and self.appbar:
            self.appbar.dock(self.edge_str, self.desired_width)
    
    def on_toggle_dock(self) -> None:
        """Toggle between docked and undocked state."""
        if self.is_docked:
            self._undock()
        else:
            self._redock()
    
    def on_exit(self) -> None:
        """Exit the application."""
        self._save_preferences()
        self.close()
        QApplication.quit()
    
    def _undock(self) -> None:
        """Undock from AppBar to normal window."""
        if self.appbar:
            self.appbar.undock()
            self.appbar = None
        
        self.is_docked = False
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Restore geometry
        geometry = self.config.get_undocked_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        else:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width = min(900, int(screen.width() * 0.8))
            height = min(1000, int(screen.height() * 0.9))
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_topbar_buttons()
        self.config.set_undocked_geometry(self.saveGeometry())
        self.config.set_docked(False)
    
    def _redock(self) -> None:
        """Redock to AppBar."""
        if self.isMaximized():
            self.showNormal()
            QApplication.processEvents()
        
        self.config.set_undocked_geometry(self.saveGeometry())
        
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        self.show()
        
        # Register and dock
        hwnd = int(self.winId())
        self.appbar = AppBarWin(hwnd, self._callback_msg)
        self.appbar.dock(self.edge_str, self.desired_width)
        self.is_docked = True
        
        # Refresh webview
        def refresh_webview():
            if self.engine.get_widget():
                self.engine.get_widget().updateGeometry()
                self.engine.get_widget().update()
                self.engine.get_widget().repaint()
                QApplication.processEvents()
        
        QTimer.singleShot(100, refresh_webview)
        
        self._update_topbar_buttons()
        self.config.set_docked(True)
    
    def _save_preferences(self) -> None:
        """Save preferences to config."""
        edge_int = AppBarEdge.LEFT if self.edge_str == "left" else AppBarEdge.RIGHT
        self.config.set_edge(edge_int)
        self.config.set_width(self.desired_width)
        self.config.set_docked(self.is_docked)
    
    # Toast notifications
    def _show_toast(self, message: str, duration_ms: int = TOAST_DURATION) -> None:
        """Show a toast message."""
        if self._toast_label:
            self._toast_label.deleteLater()
        
        self._toast_label = QLabel(message, self)
        self._toast_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.colors['panel']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }}
        """)
        self._toast_label.setAlignment(QtCore.Qt.AlignCenter)
        self._toast_label.adjustSize()
        
        x = self.topbar.x() + 10
        y = self.topbar.y() + self.topbar.height() + 5
        self._toast_label.move(x, y)
        self._toast_label.show()
        self._toast_label.raise_()
        
        self._toast_timer.start(duration_ms)
    
    def _hide_toast(self) -> None:
        """Hide the toast message."""
        if self._toast_label:
            self._toast_label.deleteLater()
            self._toast_label = None
    
    # Mouse event handlers for dragging (undocked mode)
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse press for dragging."""
        if e.button() == QtCore.Qt.LeftButton and not self.is_docked:
            self._drag = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse move for dragging."""
        if self._drag and not self.is_docked:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse release."""
        self._drag = False
    
    # Native event handler for AppBar notifications
    def nativeEvent(self, eventType: bytes, message: int) -> Tuple[bool, int]:
        """Handle native Windows events for AppBar.
        
        Args:
            eventType: Event type
            message: Message pointer
            
        Returns:
            Tuple[bool, int]: (handled, result)
        """
        if not self.is_docked or not self.appbar:
            return False, 0
        
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self._callback_msg and msg.wParam == AppBarNotification.POSCHANGED:
                self.appbar.reposition()
        
        return False, 0
    
    # Close event
    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        """Handle close event.
        
        Args:
            e: Close event
        """
        self._save_preferences()
        
        if self.appbar:
            self.appbar.undock()
        
        super().closeEvent(e)
        QApplication.quit()

