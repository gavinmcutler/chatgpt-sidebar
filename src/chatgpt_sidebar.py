# chatgpt_sidebar.py
# Windows-only. Creates a left-docked AppBar with an embedded webview by default.
# Optionally docks the installed ChatGPT app with --native-app.
#
# Usage:
# pip install PySide6
# python chatgpt_sidebar.py                # embedded webview (default)
# python chatgpt_sidebar.py --native-app   # dock installed ChatGPT window instead
# python chatgpt_sidebar.py --width 480 --url https://chat.openai.com/

# Standard library imports
import argparse
import base64
import json
import logging
import os
import pathlib
import signal
import sys
from typing import Dict, Optional, Tuple

# Third-party imports
import ctypes
from ctypes import wintypes

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QBuffer
from PySide6.QtGui import QGuiApplication, QIcon, QPalette
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
)

# ---------------- Logging Setup ----------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chatgpt_sidebar.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# ---------------- Constants ----------------

# AppBar message constants
class AppBarMessage:
    NEW = 0x00000000
    REMOVE = 0x00000001
    QUERYPOS = 0x00000002
    SETPOS = 0x00000003

# AppBar notification constants
class AppBarNotification:
    POSCHANGED = 0x00000001

# AppBar edge constants
class AppBarEdge:
    LEFT = 0
    TOP = 1
    RIGHT = 2
    BOTTOM = 3

# Window positioning constants
class WindowPos:
    NOZORDER = 0x0004
    NOACTIVATE = 0x0010
    SHOWWINDOW = 0x0040

# Window handle constants
HWND_TOP = 0

# Window show constants
class SW:
    HIDE = 0
    SHOW = 5

# PrintWindow constants
PW_RENDERFULLCONTENT = 0x00000002

# GetAncestor constants
GA_ROOT = 2

# Bitmap constants
class BitmapInfo:
    RGB = 0  # BI_RGB
    BIT_COUNT_32 = 32
    PLANES = 1

# Application constants
class AppConstants:
    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 1000
    DEFAULT_URL = "https://chat.openai.com/"
    DEFAULT_TITLE = "ChatGPT Sidebar"
    TOAST_DURATION = 3000
    SCREENSHOT_TOAST_DURATION = 1500
    
    # Window class names for ChatGPT detection
    CHATGPT_CLASSES = [
        ("", "ChatGPT"),
        ("Chrome_WidgetWin_1", None),
        ("Chrome_WidgetWin_0", None),
    ]
    
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

user32   = ctypes.windll.user32
shell32  = ctypes.windll.shell32
gdi32    = ctypes.windll.gdi32

RegisterWindowMessageW = user32.RegisterWindowMessageW
FindWindowW            = user32.FindWindowW
SetWindowPos           = user32.SetWindowPos

# Win32 API function bindings
GetForegroundWindow = user32.GetForegroundWindow
WindowFromPoint = user32.WindowFromPoint
GetAncestor = user32.GetAncestor
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
EnumWindows = user32.EnumWindows
GetDesktopWindow = user32.GetDesktopWindow
ShowWindow = user32.ShowWindow
PrintWindow = user32.PrintWindow
MonitorFromWindow = user32.MonitorFromWindow
GetMonitorInfoW = user32.GetMonitorInfoW
GetSystemMetrics = user32.GetSystemMetrics

class RECT(ctypes.Structure):
    _fields_ = [("left",  ctypes.c_long),
                ("top",   ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom",ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class APPBARDATA(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("hWnd", wintypes.HWND),
                ("uCallbackMessage", ctypes.c_uint),
                ("uEdge", ctypes.c_uint),
                ("rc", RECT),
                ("lParam", ctypes.c_int)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_uint32)]

def SHAppBarMessage(msg, data):
    return shell32.SHAppBarMessage(ctypes.c_uint(msg), ctypes.byref(data))

# Helper functions for window capture
def _rect_to_tuple(rect):
    r = RECT()
    GetWindowRect(rect, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

def _get_top_level_at_point(x: int, y: int) -> int:
    """Get the top-level window at the specified point."""
    hwnd = WindowFromPoint(POINT(x, y))
    if not hwnd:
        return 0
    return GetAncestor(hwnd, GA_ROOT)

def _intersect_rects(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> Optional[Tuple[int, int, int, int]]:
    """Calculate the intersection of two rectangles."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1, y1 = max(ax1, bx1), max(ay1, by1)
    x2, y2 = min(ax2, bx2), min(ay2, by2)
    if x2 > x1 and y2 > y1:
        return (x1, y1, x2, y2)
    return None

# ---------------- Theme Manager Class ----------------

class ThemeManager:
    """Manages theme detection and styling for the application."""
    
    @staticmethod
    def detect_theme_colors() -> Optional[Dict[str, str]]:
        """Detect system theme and return color palette."""
        app = QApplication.instance()
        if app is None:
            logger.warning("No QApplication instance found for theme detection")
            return None
        
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
        
        theme = AppConstants.DARK_THEME if is_dark else AppConstants.LIGHT_THEME
        logger.info(f"Detected {'dark' if is_dark else 'light'} theme")
        return theme

    @staticmethod
    def create_control_bar_stylesheet(colors: Dict[str, str]) -> str:
        """Create stylesheet for control bar based on theme colors."""
        return f"""
            QFrame {{
                background-color: {colors['panel']};
                border-top: 1px solid {colors['border']};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px;
                min-width: 28px;
                min-height: 28px;
                max-width: 32px;
                max-height: 32px;
            }}
            QPushButton:hover {{
                background-color: {colors['hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['pressed']};
            }}
            QPushButton:focus {{
                outline: 2px solid {colors['accent']};
                outline-offset: 2px;
            }}
        """

    @staticmethod
    def create_icon(theme_name: str, fallback_text: str, colors: Dict[str, str]) -> QIcon:
        """Create icon with proper fallback."""
        # Try system theme first
        icon = QIcon.fromTheme(theme_name)
        if not icon.isNull():
            return icon
        
        # Try built-in Qt icons as second fallback
        builtin_icons = {
            'go-previous': QtGui.QIcon.StandardPixmap.SP_ArrowLeft,
            'go-next': QtGui.QIcon.StandardPixmap.SP_ArrowRight,
            'view-fullscreen': QtGui.QIcon.StandardPixmap.SP_TitleBarNormalButton,
            'view-restore': QtGui.QIcon.StandardPixmap.SP_TitleBarNormalButton,
            'window-close': QtGui.QIcon.StandardPixmap.SP_TitleBarCloseButton,
            'camera-photo': QtGui.QIcon.StandardPixmap.SP_FileDialogDetailedView
        }
        
        if theme_name in builtin_icons:
            # Create icon from standard pixmap
            pixmap = QtGui.QApplication.style().standardPixmap(builtin_icons[theme_name])
            if not pixmap.isNull():
                # Recolor the pixmap to match theme
                colored_pixmap = ThemeManager.recolor_pixmap(pixmap, colors['fg'])
                return QIcon(colored_pixmap)
        
        # Final fallback to geometric icons
        return ThemeManager.create_text_icon(theme_name, colors)
    
    @staticmethod
    def recolor_pixmap(pixmap: QtGui.QPixmap, color: str) -> QtGui.QPixmap:
        """Recolor a pixmap to the specified color."""
        try:
            # Create a new pixmap with the same size
            result = QtGui.QPixmap(pixmap.size())
            result.fill(QtCore.Qt.transparent)
            
            # Create a painter
            painter = QtGui.QPainter(result)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Set the color
            painter.setPen(QtGui.QColor(color))
            painter.setBrush(QtGui.QColor(color))
            
            # Draw the original pixmap as a mask
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.drawPixmap(0, 0, pixmap)
            
            painter.end()
            return result
        except Exception as e:
            logger.warning(f"Failed to recolor pixmap: {e}")
            return pixmap

    @staticmethod
    def create_text_icon(icon_type: str, colors: Dict[str, str]) -> QIcon:
        """Create a simple geometric icon as fallback."""
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        pen = QtGui.QPen(QtGui.QColor(colors['fg']))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtGui.QColor(colors['fg']))
        
        center_x, center_y = 12, 12
        
        if icon_type == 'left':
            # Draw left arrow
            painter.drawPolygon([
                QtCore.QPoint(center_x + 4, center_y - 6),
                QtCore.QPoint(center_x - 4, center_y),
                QtCore.QPoint(center_x + 4, center_y + 6)
            ])
        elif icon_type == 'right':
            # Draw right arrow
            painter.drawPolygon([
                QtCore.QPoint(center_x - 4, center_y - 6),
                QtCore.QPoint(center_x + 4, center_y),
                QtCore.QPoint(center_x - 4, center_y + 6)
            ])
        elif icon_type == 'dock':
            # Draw maximize icon (square)
            painter.drawRect(center_x - 6, center_y - 6, 12, 12)
        elif icon_type == 'undock':
            # Draw restore icon (overlapping squares)
            painter.drawRect(center_x - 4, center_y - 4, 8, 8)
            painter.drawRect(center_x - 2, center_y - 2, 8, 8)
        elif icon_type == 'exit':
            # Draw X
            painter.drawLine(center_x - 5, center_y - 5, center_x + 5, center_y + 5)
            painter.drawLine(center_x + 5, center_y - 5, center_x - 5, center_y + 5)
        elif icon_type == 'camera':
            # Draw camera icon
            painter.drawEllipse(center_x - 6, center_y - 4, 12, 8)
            painter.drawRect(center_x - 2, center_y + 2, 4, 3)
            painter.drawEllipse(center_x - 3, center_y - 2, 6, 4)
        
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def get_control_icons(colors: Dict[str, str]) -> Dict[str, QIcon]:
        """Get all control icons with theme adaptation."""
        return {
            'left': ThemeManager.create_icon('go-previous', 'left', colors),
            'right': ThemeManager.create_icon('go-next', 'right', colors),
            'dock': ThemeManager.create_icon('view-fullscreen', 'dock', colors),
            'undock': ThemeManager.create_icon('view-restore', 'undock', colors),
            'exit': ThemeManager.create_icon('window-close', 'exit', colors),
            'camera': ThemeManager.create_icon('camera-photo', 'camera', colors)
        }

# ---------------- JavaScript helpers for screenshot functionality ----------------

def _build_paste_js(b64: str) -> str:
    """JavaScript to inject image via synthetic paste event."""
    b64q = json.dumps(b64)  # safe string literal
    return f"""
    (function(){{
      const composer = document.querySelector(
        '[data-testid="composer"] textarea, [contenteditable="true"][data-testid="textbox"], div[contenteditable="true"]'
      );
      if (!composer) return false;
      
      function base64ToUint8Array(b64){{
        const binary = atob(b64);
        const len = binary.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
        return bytes;
      }}
      
      const bytes = base64ToUint8Array({b64q});
      const blob = new Blob([bytes], {{ type: 'image/png' }});
      const file = new File([blob], 'screenshot.png', {{ type: 'image/png' }});
      const dt = new DataTransfer();
      dt.items.add(file);
      
      let evt;
      try {{
        evt = new ClipboardEvent('paste', {{ 
          clipboardData: dt, 
          bubbles: true, 
          cancelable: true 
        }});
      }} catch (e) {{
        evt = new Event('paste', {{ bubbles: true, cancelable: true }});
        try {{ 
          Object.defineProperty(evt, 'clipboardData', {{ value: dt }}); 
        }} catch(e2) {{}}
      }}
      
      composer.focus();
      return composer.dispatchEvent(evt);
    }})();"""

# ---------------- Window Capture Helper Class ----------------

class WindowCapture:
    """Helper class for capturing window screenshots."""
    
    def __init__(self) -> None:
        """Initialize the window capture helper."""
        pass
    
    @staticmethod
    def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
        """Get rectangle of a window handle."""
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        return (r.left, r.top, r.right, r.bottom)
    
    @staticmethod
    def find_excluded_hwnds(exclude_self: int, exclude_native_chatgpt: Optional[int] = None) -> set:
        """Get set of HWNDs to exclude from capture."""
        excluded = {exclude_self}
        if exclude_native_chatgpt:
            excluded.add(exclude_native_chatgpt)
        return excluded
    
    @staticmethod
    def visible_top_window_in_rect(wr: Tuple[int, int, int, int], excluded_hwnds: set) -> int:
        """Find the top-most visible window in the given rectangle."""
        # 1) Try foreground window if it intersects and is not excluded
        fg = GetForegroundWindow()
        if fg and fg not in excluded_hwnds and IsWindowVisible(fg):
            rr = WindowCapture.get_window_rect(fg)
            if _intersect_rects(rr, wr):
                return fg

        # 2) Try window under the center point of work area
        cx = (wr[0] + wr[2]) // 2
        cy = (wr[1] + wr[3]) // 2
        atpt = _get_top_level_at_point(cx, cy)
        if atpt and atpt not in excluded_hwnds and IsWindowVisible(atpt):
            rr = WindowCapture.get_window_rect(atpt)
            if _intersect_rects(rr, wr):
                return atpt

        # 3) Enumerate top-level windows from front to back
        found = 0
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum_cb(hwnd, lParam):
            nonlocal found
            if found:
                return False
            if hwnd in excluded_hwnds:
                return True
            if not IsWindowVisible(hwnd):
                return True
            rr = WindowCapture.get_window_rect(hwnd)
            if _intersect_rects(rr, wr):
                found = hwnd
                return False
            return True

        EnumWindows(_enum_cb, 0)
        return found
    
    @staticmethod
    def capture_hwnd_to_qimage(hwnd: int) -> Optional['QtGui.QImage']:
        """Capture a window handle to QImage using PrintWindow/BitBlt."""
        try:
            # Get rect
            l, t, r, b = WindowCapture.get_window_rect(hwnd)
            w, h = r - l, b - t
            if w <= 0 or h <= 0:
                logger.warning(f"Invalid window dimensions: {w}x{h}")
                return None

            # Create a compatible DC + bitmap
            hdcWindow = user32.GetWindowDC(hwnd)
            hdcMemDC = gdi32.CreateCompatibleDC(hdcWindow)
            hbm = gdi32.CreateCompatibleBitmap(hdcWindow, w, h)
            gdi32.SelectObject(hdcMemDC, hbm)

            # Try PrintWindow (renders offscreen content for some apps)
            ok = PrintWindow(hwnd, hdcMemDC, PW_RENDERFULLCONTENT)

            if not ok:
                # Fallback: BitBlt what's on screen
                gdi32.BitBlt(hdcMemDC, 0, 0, w, h, hdcWindow, 0, 0, 0x00CC0020)  # SRCCOPY

            # Extract bitmap bits into QImage
            # BITMAPINFOHEADER
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_uint32),
                    ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16),
                    ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)
                ]
            
            class BITMAPINFO(ctypes.Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                            ("bmiColors", ctypes.c_uint32 * 3)]

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = w
            bmi.bmiHeader.biHeight = -h  # top-down
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = BitmapInfo.BIT_COUNT_32
            bmi.bmiHeader.biCompression = BitmapInfo.RGB
            buf_size = w * h * 4
            pixel_data = (ctypes.c_ubyte * buf_size)()

            gdi32.GetDIBits(hdcMemDC, hbm, 0, h, ctypes.byref(pixel_data), ctypes.byref(bmi), 0)

            # Cleanup GDI
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdcMemDC)
            user32.ReleaseDC(hwnd, hdcWindow)

            # Convert to QImage (Format_ARGB32)
            from PySide6.QtGui import QImage
            img = QImage(bytes(pixel_data), w, h, QImage.Format.Format_ARGB32)
            return img.copy()  # detach from buffer
        
        except Exception as e:
            logger.error(f"Failed to capture window {hwnd}: {e}")
            return None

# ---------------- Qt window that registers as AppBar ----------------

class AppBarWidget(QWidget):
    """Main widget for the ChatGPT sidebar application."""
    
    def __init__(
        self, 
        desired_width: int = AppConstants.DEFAULT_WIDTH, 
        edge: int = AppBarEdge.LEFT, 
        title: str = AppConstants.DEFAULT_TITLE, 
        url_string: Optional[str] = None, 
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # Load user preferences with proper defaults
        self.settings = QtCore.QSettings("ChatGPTSidebar", "App")
        self.desired_width = self.settings.value("width", desired_width, type=int)
        self.edge = self.settings.value("edge", edge, type=int)
        self.is_docked = self.settings.value("is_docked", True, type=bool)
        
        # Initialize state
        self._registered = False
        self._callback_msg = RegisterWindowMessageW("APPBARMSG_CHATGPT_SIDEBAR")
        self.native_app_mode = False  # Will be set by main()
        self.chatgpt_hwnd = None  # Will store ChatGPT window handle in native app mode
        
        # Theme and colors
        self.colors = ThemeManager.detect_theme_colors()
        self.icons = ThemeManager.get_control_icons(self.colors)

        # Basic chrome
        self.setWindowFlags(self.windowFlags()
                            | QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowStaysOnTopHint)  # stays above desktop
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)

        # Simple drag area
        self._drag = False
        self._drag_pos = QtCore.QPoint()

        # Layout placeholder; child content added outside
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0,0,0,0)
        self.v.setSpacing(0)

        # Create top control bar with icons first
        self._create_control_bar()

        # Create secure web profile for session persistence
        if url_string:
            self._create_web_profile()
            self.web = QWebEngineView(self)
            page = QWebEnginePage(self.profile, self.web)
            self.web.setPage(page)
            self.web.setUrl(QtCore.QUrl(url_string))
            self.v.addWidget(self.web, 1)  # webview fills remainder
        
        # Connect button signals
        self.btnShot.clicked.connect(self.on_screenshot_to_chat)
        self.btnSide.clicked.connect(self.on_toggle_side)
        self.btnDock.clicked.connect(self.on_toggle_dock)
        self.btnExit.clicked.connect(self.on_exit)
        
        # Store webview availability for screenshot functionality
        self.has_webview = url_string is not None
        
        # Store native ChatGPT window handle for exclusion
        self._native_chatgpt_hwnd = None

        # Initialize toast system
        self._toast_label = None
        self._toast_timer = QtCore.QTimer()
        self._toast_timer.timeout.connect(self._hide_toast)
        self._toast_timer.setSingleShot(True)

        # Register after shown (so we have a real HWND)
        if self.is_docked:
            QtCore.QTimer.singleShot(0, self._register_appbar)
        else:
            # Start undocked if that was the last state
            QtCore.QTimer.singleShot(0, self._start_undocked)
    
    def _create_web_profile(self) -> None:
        """Create secure web profile for session persistence."""
        try:
            appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
            profile_dir = pathlib.Path(appdata) / "ChatGPTSidebar" / "Profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            self.profile = QWebEngineProfile(str(profile_dir), self)
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
            self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
            
            # Set cache and storage paths using the correct API
            cache_dir = profile_dir / "http_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            storage_dir = profile_dir / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Use the correct method names for the current PySide6 version
            if hasattr(self.profile, 'setHttpCachePath'):
                self.profile.setHttpCachePath(str(cache_dir))
            if hasattr(self.profile, 'setPersistentStoragePath'):
                self.profile.setPersistentStoragePath(str(storage_dir))
            
            logger.info(f"Created web profile at {profile_dir}")
        except Exception as e:
            logger.error(f"Failed to create web profile: {e}")
            raise
    
    def _create_control_bar(self):
        """Create themed control bar with icons"""
        self.controls = QFrame(self)
        self.controls.setFrameShape(QFrame.NoFrame)
        self.controls.setFixedHeight(40)
        self.controls.setStyleSheet(ThemeManager.create_control_bar_stylesheet(self.colors))
        
        # Control bar layout
        controls_layout = QHBoxLayout(self.controls)
        controls_layout.setContentsMargins(8, 6, 8, 6)
        controls_layout.setSpacing(6)
        
        # Create icon buttons
        self.btnShot = QPushButton()
        self.btnSide = QPushButton()
        self.btnDock = QPushButton()
        self.btnExit = QPushButton()
        
        # Set icons and tooltips
        self._update_button_icons_and_tooltips()
        
        # Add buttons with proper layout: screenshot on left, others on right
        controls_layout.addWidget(self.btnShot)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btnSide)
        controls_layout.addWidget(self.btnDock)
        controls_layout.addWidget(self.btnExit)
        
        # Add control bar to main layout at the top
        self.v.addWidget(self.controls)
    
    def _update_button_icons_and_tooltips(self):
        """Update button icons and tooltips based on current state"""
        # Screenshot button
        self.btnShot.setIcon(self.icons['camera'])
        self.btnShot.setToolTip("Attach a screenshot to the current chat")
        self.btnShot.setAccessibleName("Screenshot")
        
        # Side toggle button
        if self.edge == AppBarEdge.LEFT:
            self.btnSide.setIcon(self.icons['right'])
            self.btnSide.setToolTip("Switch to right")
        else:
            self.btnSide.setIcon(self.icons['left'])
            self.btnSide.setToolTip("Switch to left")
        
        # Dock/undock button
        if self.is_docked:
            self.btnDock.setIcon(self.icons['undock'])
            self.btnDock.setToolTip("Pop out")
        else:
            self.btnDock.setIcon(self.icons['dock'])
            self.btnDock.setToolTip("Dock")
        
        # Exit button
        self.btnExit.setIcon(self.icons['exit'])
        self.btnExit.setToolTip("Exit")
    
    def _start_undocked(self) -> None:
        """Start in undocked mode with restored geometry."""
        # Set normal window flags
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Restore geometry if available
        geometry = self.settings.value("undocked_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size and center - adapt to screen size
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width = min(900, int(screen.width() * 0.8))
            height = min(1000, int(screen.height() * 0.9))
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_button_icons_and_tooltips()

    # ----- Toast notification system -----
    def _show_toast(self, message: str, duration_ms: int = AppConstants.TOAST_DURATION) -> None:
        """Show a non-intrusive toast message"""
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
        
        # Position near the control bar
        x = self.controls.x() + 10
        y = self.controls.y() + self.controls.height() + 5
        self._toast_label.move(x, y)
        self._toast_label.show()
        self._toast_label.raise_()
        
        # Auto-hide after duration
        self._toast_timer.start(duration_ms)
    
    def _hide_toast(self) -> None:
        """Hide the toast message."""
        if self._toast_label:
            self._toast_label.deleteLater()
            self._toast_label = None
    
    def _other_work_area_rect(self) -> Tuple[int, int, int, int]:
        """Compute the opposite work area rectangle from our AppBar.
        
        Returns:
            Tuple[int, int, int, int]: Rectangle coordinates (left, top, right, bottom)
        """
        # Get monitor rect using Windows API for accuracy
        mon_rect = self._monitor_rect()
        monitor = (mon_rect.left, mon_rect.top, mon_rect.right, mon_rect.bottom)
        
        # Our AppBar rect after docking:
        hwnd = int(self.winId())
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        appbar = (r.left, r.top, r.right, r.bottom)
        
        # Return the remaining area on the opposite side
        if self.edge == AppBarEdge.LEFT:
            # right side
            return (appbar[2], monitor[1], monitor[2], monitor[3])
        else:
            # left side
            return (monitor[0], monitor[1], appbar[0], monitor[3])
    
    def _find_excluded_hwnds(self) -> set:
        """Get set of HWNDs to exclude from capture."""
        return WindowCapture.find_excluded_hwnds(
            int(self.winId()), 
            getattr(self, '_native_chatgpt_hwnd', None)
        )

    # ----- Mouse drag (for moving when not docked) -----
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse press events for dragging."""
        # Only allow dragging when undocked
        if e.button() == QtCore.Qt.LeftButton and not self.is_docked:
            self._drag = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse move events for dragging."""
        # Only allow dragging when undocked
        if self._drag and not self.is_docked:
            self.move((e.globalPosition().toPoint() - self._drag_pos))
            e.accept()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse release events."""
        self._drag = False

    # ----- Native event hook (to catch ABN_POSCHANGED) -----
    def nativeEvent(self, eventType: bytes, message: int) -> Tuple[bool, int]:
        """Handle native Windows events for AppBar notifications.
        
        Args:
            eventType: The type of native event
            message: The message pointer
            
        Returns:
            Tuple[bool, int]: Whether the event was handled and result code
        """
        # Only handle AppBar events when docked
        if not self.is_docked:
            return False, 0
            
        # message is MSG* on Windows
        if eventType == "windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self._callback_msg and msg.wParam == AppBarNotification.POSCHANGED:
                self._dock()
        return False, 0

    def _register_appbar(self) -> None:
        """Register this window as an AppBar with the system."""
        hwnd = int(self.winId())
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = hwnd
        abd.uCallbackMessage = self._callback_msg
        SHAppBarMessage(AppBarMessage.NEW, abd)
        self._registered = True
        self._dock()

    def _monitor_rect(self) -> RECT:
        """Get the monitor rectangle for AppBar positioning.
        
        Returns:
            RECT: The monitor rectangle coordinates
        """
        # Use Windows API to get accurate monitor info
        hwnd = int(self.winId())
        
        # Get the monitor this window is on (MONITOR_DEFAULTTONEAREST = 2)
        hMonitor = MonitorFromWindow(hwnd, 2)
        
        if hMonitor:
            # Get monitor info
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            
            if GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                # Use rcMonitor for full screen dimensions (not rcWork which excludes taskbar)
                logger.info(f"Monitor rect: left={mi.rcMonitor.left}, top={mi.rcMonitor.top}, "
                           f"right={mi.rcMonitor.right}, bottom={mi.rcMonitor.bottom}")
                return mi.rcMonitor
        
        # Fallback to Qt if Windows API fails
        try:
            screen = self.screen()
            if screen is None:
                screen = QGuiApplication.primaryScreen()
        except:
            screen = QGuiApplication.primaryScreen()
        
        geometry = screen.geometry()
        logger.info(f"Fallback Qt geometry: {geometry.left()}, {geometry.top()}, "
                   f"{geometry.right()}, {geometry.bottom()}")
        return RECT(geometry.left(), geometry.top(), geometry.right(), geometry.bottom())

    def _dock(self) -> None:
        """Dock the AppBar to the specified edge with the desired width."""
        hwnd = int(self.winId())
        rect = self._monitor_rect()
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = hwnd
        abd.uEdge = self.edge
        abd.rc = rect

        # Store the original screen bounds
        screen_left = rect.left
        screen_top = rect.top
        screen_right = rect.right
        screen_bottom = rect.bottom

        # Propose width from saved desired_width, keep full height
        if self.edge == AppBarEdge.LEFT:
            abd.rc.left = screen_left
            abd.rc.right = screen_left + int(self.desired_width)
        else:  # RIGHT
            abd.rc.left = screen_right - int(self.desired_width)
            abd.rc.right = screen_right
        
        # Always use full screen height
        abd.rc.top = screen_top
        abd.rc.bottom = screen_bottom

        SHAppBarMessage(AppBarMessage.QUERYPOS, abd)

        # Enforce final width again after QUERYPOS, maintaining screen edges and full height
        if self.edge == AppBarEdge.LEFT:
            abd.rc.left = screen_left
            abd.rc.right = screen_left + int(self.desired_width)
        else:  # RIGHT
            abd.rc.left = screen_right - int(self.desired_width)
            abd.rc.right = screen_right
        
        # Re-enforce full height from screen bounds
        abd.rc.top = screen_top
        abd.rc.bottom = screen_bottom

        SHAppBarMessage(AppBarMessage.SETPOS, abd)

        # Apply to our window
        x, y = abd.rc.left, abd.rc.top
        w, h = abd.rc.right - abd.rc.left, abd.rc.bottom - abd.rc.top
        user32.MoveWindow(hwnd, x, y, w, h, True)

    # ----- Button slot methods -----
    def on_toggle_side(self) -> None:
        """Toggle between left and right docking."""
        if self.edge == AppBarEdge.LEFT:
            self.edge = AppBarEdge.RIGHT
        else:
            self.edge = AppBarEdge.LEFT
        
        # Save preference
        self.settings.setValue("edge", self.edge)
        
        # Update icon and tooltip
        self._update_button_icons_and_tooltips()
        
        # If docked, re-dock to new side
        if self.is_docked:
            self._dock()
    
    def on_toggle_dock(self) -> None:
        """Toggle between docked and undocked state."""
        if self.is_docked:
            self._undock_to_normal_window()
        else:
            self._redock_appbar()
    
    def on_exit(self) -> None:
        """Close the application."""
        self._save_preferences()
        self.close()
        QApplication.quit()
    
    def on_screenshot_to_chat(self) -> None:
        """Capture screenshot of other window and paste into chat."""
        logger.info("Screenshot button clicked - starting capture process")
        try:
            # Check if we have a webview (not available in native-app mode without webview)
            if not self.has_webview:
                logger.warning("Screenshot requested but no webview available")
                self._show_toast("Screenshot-to-chat is only available in WebView mode.")
                return
            
            # 0) Determine the opposite work area rectangle
            wr = self._other_work_area_rect()

            # 1) Resolve the target HWND in that rect (exclude ourselves and native ChatGPT if present)
            excluded_hwnds = self._find_excluded_hwnds()
            hwnd_target = WindowCapture.visible_top_window_in_rect(wr, excluded_hwnds)
            if not hwnd_target:
                logger.warning("No window found to capture in work area")
                self._show_toast("No window to capture in the work area.")
                return
            
            # 2) Temporarily hide our bar to avoid bleed-in (it's on the edge, but just in case)
            ShowWindow(int(self.winId()), SW.HIDE)
            try:
                img = WindowCapture.capture_hwnd_to_qimage(hwnd_target)
            finally:
                ShowWindow(int(self.winId()), SW.SHOW)

            if img is None or img.isNull():
                logger.error("Failed to capture window image")
                self._show_toast("Couldn't capture that window.")
                return

            # 3) Encode PNG to base64 (in-memory)
            ba = QtCore.QByteArray()
            buf = QBuffer(ba)
            buf.open(QtCore.QIODevice.WriteOnly)
            img.save(buf, "PNG")
            b64 = base64.b64encode(bytes(ba)).decode("ascii")

            # 4) Always paste via synthetic DataTransfer
            js = _build_paste_js(b64)
            self.web.page().runJavaScript(js, lambda ok: self._after_paste_result(ok))
        except Exception as e:
            logger.error(f"Screenshot to chat failed: {e}")
            self._show_toast("Screenshot failed. Please try again.")
    
    def _after_paste_result(self, ok: bool) -> None:
        """Handle result of paste injection.
        
        Args:
            ok: Whether the paste operation was successful
        """
        if not ok:
            self._show_toast("Couldn't paste into the chat. Click the message box and retry.")
        else:
            self._show_toast("Screenshot attached.", duration_ms=AppConstants.SCREENSHOT_TOAST_DURATION)
    
    def _save_preferences(self) -> None:
        """Save current preferences to QSettings."""
        self.settings.setValue("edge", self.edge)
        self.settings.setValue("width", self.desired_width)
        self.settings.setValue("is_docked", self.is_docked)
    
    def _undock_to_normal_window(self) -> None:
        """Convert from docked AppBar to normal window."""
        # Unregister AppBar if currently registered
        if self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(self.winId())
            SHAppBarMessage(AppBarMessage.REMOVE, abd)
            self._registered = False
        
        # Update state (keep desired_width unchanged)
        self.is_docked = False
        
        # Set normal window flags
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Restore previous undocked geometry if available
        geometry = self.settings.value("undocked_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size and center for first time undocking - adapt to screen size
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width = min(900, int(screen.width() * 0.8))
            height = min(1000, int(screen.height() * 0.9))
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_button_icons_and_tooltips()
        
        # Save undocked geometry and state
        self.settings.setValue("undocked_geometry", self.saveGeometry())
        self.settings.setValue("is_docked", self.is_docked)
    
    def _redock_appbar(self) -> None:
        """Convert from normal window back to docked AppBar."""
        # Save current undocked geometry before switching
        self.settings.setValue("undocked_geometry", self.saveGeometry())
        
        # Go frameless/topmost as sidebar
        self.setWindowFlags(self.windowFlags()
                           | QtCore.Qt.FramelessWindowHint
                           | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        self.show()
        
        # Register and dock using saved desired_width
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = int(self.winId())
        abd.uCallbackMessage = self._callback_msg
        SHAppBarMessage(AppBarMessage.NEW, abd)
        self._registered = True
        self.is_docked = True
        
        # Dock using the saved desired_width
        self._dock()
        
        # Update UI and save preferences
        self._update_button_icons_and_tooltips()
        self.settings.setValue("is_docked", self.is_docked)
        
        # In native app mode, re-dock the ChatGPT app after AppBar is registered
        if hasattr(self, 'native_app_mode') and self.native_app_mode:
            QtCore.QTimer.singleShot(100, self._redock_native_app)
    
    def _redock_native_app(self) -> None:
        """Re-dock the native ChatGPT app to the AppBar rect."""
        if self.chatgpt_hwnd:
            rect = self.frameGeometry()
            set_window_rect(self.chatgpt_hwnd, rect.x(), rect.y(), rect.width(), rect.height())
        else:
            # Try to find ChatGPT app again
            hwnd_target = find_chatgpt_hwnd()
            if hwnd_target:
                self.chatgpt_hwnd = hwnd_target
                self._native_chatgpt_hwnd = hwnd_target  # Store for exclusion from screenshots
                rect = self.frameGeometry()
                set_window_rect(hwnd_target, rect.x(), rect.y(), rect.width(), rect.height())

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        """Handle application close event.
        
        Args:
            e: The close event
        """
        # Save preferences before closing
        self._save_preferences()
        
        # Unregister AppBar if currently registered
        if self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(self.winId())
            SHAppBarMessage(AppBarMessage.REMOVE, abd)
        
        super().closeEvent(e)
        QApplication.quit()

# ---------------- Helper: find & dock the existing ChatGPT app window ----------------

def find_chatgpt_hwnd() -> int:
    """
    Try to find the ChatGPT window handle using common patterns.
    
    Returns:
        int: Window handle if found, 0 otherwise
    """
    for cls, title in AppConstants.CHATGPT_CLASSES:
        hwnd = FindWindowW(cls or None, title or None)
        if hwnd:
            return hwnd
    return 0

def set_window_rect(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """Set the position and size of a window."""
    SetWindowPos(
        hwnd, 
        HWND_TOP, 
        x, 
        y, 
        w, 
        h, 
        WindowPos.NOACTIVATE | WindowPos.SHOWWINDOW | WindowPos.NOZORDER
    )

# ---------------- Main ----------------

def main() -> None:
    """Main entry point for the ChatGPT Sidebar application."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--width", 
        type=int, 
        default=AppConstants.DEFAULT_WIDTH, 
        help="Sidebar width in pixels"
    )
    parser.add_argument(
        "--native-app", 
        action="store_true", 
        help="Dock the installed ChatGPT app instead of using embedded webview"
    )
    parser.add_argument(
        "--url", 
        default=AppConstants.DEFAULT_URL, 
        help="URL to load in embedded webview"
    )
    parser.add_argument(
        "--dock-title", 
        default="ChatGPT", 
        help="Window title to look for when docking the installed app"
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        app.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.native_app:
            # Native app mode: create AppBar without webview, then dock ChatGPT app
            bar = AppBarWidget(desired_width=args.width)
            bar.native_app_mode = True  # Flag to track native app mode
            
            # Only show and dock if starting in docked mode
            if bar.is_docked:
                bar.show()
                
                # Try to find and dock the installed ChatGPT app
                def dock_existing():
                    hwnd_target = find_chatgpt_hwnd()
                    if hwnd_target:
                        rect = bar.frameGeometry()
                        set_window_rect(hwnd_target, rect.x(), rect.y(), rect.width(), rect.height())
                        bar.chatgpt_hwnd = hwnd_target  # Store hwnd for later use
                        bar._native_chatgpt_hwnd = hwnd_target  # Store for exclusion from screenshots
                    else:
                        # Retry a few times in case user opens it late
                        QtCore.QTimer.singleShot(1500, dock_existing)
                QtCore.QTimer.singleShot(500, dock_existing)
            else:
                # Start undocked - already handled by _start_undocked()
                pass
        else:
            # Default mode: embedded webview
            try:
                bar = AppBarWidget(desired_width=args.width, url_string=args.url)
                bar.native_app_mode = False
                
                # Only show if starting in docked mode (undocked mode handled by _start_undocked)
                if bar.is_docked:
                    bar.show()
            except Exception as e:
                logger.error(f"Failed to create webview: {e}")
                QtWidgets.QMessageBox.critical(None, "Missing dependency",
                    f"QtWebEngine is not available. Please install PySide6 with WebEngine support.\nError: {e}")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        QtWidgets.QMessageBox.critical(None, "Startup Error",
            f"Failed to start ChatGPT Sidebar:\n{e}")
        sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script requires Windows.")
        sys.exit(1)
    main()
