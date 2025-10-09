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
        
        # Calculate width from percentage
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width_percent = self.config.get_width_percent()
        self.desired_width = int(screen.width() * width_percent / 100)
        
        self.edge_str = "left" if self.config.get_edge() == AppBarEdge.LEFT else "right"
        self.is_docked = self.config.is_docked()
        
        # Theme and colors
        theme_preference = self.config.get_theme()
        self.colors = ThemeManager.detect_theme_colors(theme_preference)
        self.icons = ThemeManager.get_control_icons(self.colors)
        
        # Set up window flags for docked mode
        flags = self.windowFlags() | QtCore.Qt.FramelessWindowHint
        if self.config.get_always_on_top():
            flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
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
        
        # Connect sidebar signals
        self.sidebar.settings_changed.connect(self.on_settings_changed)
        
        # Update topbar button states
        self._update_topbar_buttons()
        
        # Apply saved appearance settings
        self._apply_initial_settings()
        
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
    
    def _apply_initial_settings(self) -> None:
        """Apply saved appearance settings on startup.
        
        Applies settings that can be changed without restart:
        - Window opacity
        - Web content zoom (font size)
        """
        # Apply opacity
        opacity = self.config.get_opacity()
        self.setWindowOpacity(opacity)
        
        # Apply zoom (from saved zoom or font size)
        zoom = self.config.get_zoom()
        self.engine.set_zoom(zoom)
        
        logger.info(f"Applied initial settings: opacity={opacity}, zoom={zoom}")
    
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
    
    def on_settings_changed(self, settings: dict) -> None:
        """Handle settings changes.
        
        Args:
            settings: Dictionary of changed settings
        """
        logger.info(f"Settings changed: {settings}")
        
        # Apply opacity changes
        if 'opacity' in settings:
            opacity = settings['opacity']
            self.setWindowOpacity(opacity)
            logger.info(f"Applied opacity: {opacity}")
        
        # Apply font size changes (via zoom)
        if 'font_size' in settings:
            font_size = settings['font_size']
            zoom_map = {
                'small': 0.85,
                'medium': 1.0,
                'large': 1.15
            }
            zoom = zoom_map.get(font_size, 1.0)
            self.config.set_zoom(zoom)
            self.engine.set_zoom(zoom)
            logger.info(f"Applied font size: {font_size} (zoom: {zoom})")
        
        # Apply always on top changes
        if 'always_on_top' in settings:
            always_on_top = settings['always_on_top']
            
            # Only apply immediately in undocked mode
            # In docked mode, it requires restart to avoid AppBar issues
            if not self.is_docked:
                if always_on_top:
                    self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
                else:
                    self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
                self.show()
                logger.info(f"Applied always on top: {always_on_top}")
            else:
                logger.info(f"Always on top setting saved: {always_on_top} (will apply on restart)")
        
        # Handle autostart (Windows registry)
        if 'autostart' in settings:
            autostart = settings['autostart']
            self._set_autostart(autostart)
            logger.info(f"Applied autostart: {autostart}")
        
        # Handle sign out
        if 'sign_out' in settings and settings['sign_out']:
            self._sign_out()
            return  # Don't show other messages
        
        # Note: Theme, edge, width, docked state, and always on top (when docked)
        # typically require an app restart to fully apply
        requires_restart = []
        if 'theme' in settings:
            requires_restart.append('theme')
        if 'edge' in settings:
            # Check if edge changed from current window state
            current_edge = AppBarEdge.LEFT if self.edge_str == "left" else AppBarEdge.RIGHT
            if settings['edge'] != current_edge:
                requires_restart.append('position')
        if 'docked' in settings and settings['docked'] != self.is_docked:
            requires_restart.append('dock mode')
        if 'width_percent' in settings:
            requires_restart.append('width')
        if 'always_on_top' in settings and self.is_docked:
            requires_restart.append('always on top')
        
        if requires_restart:
            restart_msg = f"Some settings ({', '.join(requires_restart)}) will take effect after restarting the app"
            self._show_toast(restart_msg, duration=5000)
            logger.info(restart_msg)
        else:
            self._show_toast("Settings applied successfully")
    
    def _sign_out(self) -> None:
        """Sign out by clearing authentication cookies and reloading."""
        try:
            # Clear only authentication cookies to sign out
            if self.engine and hasattr(self.engine, '_profile') and self.engine._profile:
                profile = self.engine._profile
                
                # Clear all cookies (this signs the user out)
                if hasattr(profile, 'cookieStore'):
                    profile.cookieStore().deleteAllCookies()
                    logger.info("Cleared authentication cookies")
                
                # Reload the page to show login screen
                self.engine.navigate(DEFAULT_URL)
                
                self._show_toast("Signed out successfully", duration=2000)
                logger.info("User signed out")
            else:
                self._show_toast("Failed to sign out", duration=3000)
                logger.error("Web engine or profile not available")
                
        except Exception as e:
            logger.error(f"Failed to sign out: {e}")
            self._show_toast(f"Error signing out: {e}", duration=4000)
    
    def _set_autostart(self, enable: bool) -> None:
        """Enable or disable autostart via Windows registry.
        
        Args:
            enable: Whether to enable autostart
        """
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if enable:
                exe_path = sys.executable
                # If running from Python, use the script path
                if exe_path.endswith("python.exe") or exe_path.endswith("pythonw.exe"):
                    import __main__
                    if hasattr(__main__, '__file__'):
                        exe_path = f'"{sys.executable}" "{__main__.__file__}"'
                else:
                    exe_path = f'"{exe_path}"'
                
                winreg.SetValueEx(key, "ChatGPTSidebar", 0, winreg.REG_SZ, exe_path)
                logger.info(f"Autostart enabled: {exe_path}")
            else:
                try:
                    winreg.DeleteValue(key, "ChatGPTSidebar")
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass  # Value doesn't exist, already disabled
            
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to set autostart: {e}")
            self._show_toast(f"Failed to set autostart: {e}", duration=4000)
    
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
        """Save preferences to config.
        
        Note: All settings are saved immediately when changed via the settings UI.
        This method is kept for backwards compatibility but does nothing to avoid
        overwriting user preferences with the current window state on exit.
        """
        pass
    
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

