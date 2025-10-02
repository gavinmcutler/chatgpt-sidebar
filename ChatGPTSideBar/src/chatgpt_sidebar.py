# chatgpt_sidebar.py
# Windows-only. Creates a left-docked AppBar with an embedded webview by default.
# Optionally docks the installed ChatGPT app with --native-app.
#
# Usage:
# pip install PySide6
# python chatgpt_sidebar.py                # embedded webview (default)
# python chatgpt_sidebar.py --native-app   # dock installed ChatGPT window instead
# python chatgpt_sidebar.py --width 480 --url https://chat.openai.com/

import sys
import ctypes
from ctypes import wintypes
import argparse
import time

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtGui import QGuiApplication, QPalette, QIcon
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import QBuffer
import os
import pathlib
import base64
import json

# ---------------- Win32 AppBar interop ----------------

ABM_NEW        = 0x00000000
ABM_REMOVE     = 0x00000001
ABM_QUERYPOS   = 0x00000002
ABM_SETPOS     = 0x00000003
ABM_GETTASKBARPOS = 0x00000005

ABN_POSCHANGED = 0x00000001

ABE_LEFT   = 0
ABE_TOP    = 1
ABE_RIGHT  = 2
ABE_BOTTOM = 3

SWP_NOZORDER   = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

HWND_TOP = 0

user32   = ctypes.windll.user32
shell32  = ctypes.windll.shell32
gdi32    = ctypes.windll.gdi32

RegisterWindowMessageW = user32.RegisterWindowMessageW
FindWindowW            = user32.FindWindowW
SetWindowPos           = user32.SetWindowPos

# Additional Win32 functions for window capture
GetForegroundWindow = user32.GetForegroundWindow
WindowFromPoint     = user32.WindowFromPoint
GetAncestor         = user32.GetAncestor
GA_ROOT = 2
IsWindowVisible     = user32.IsWindowVisible
GetWindowRect       = user32.GetWindowRect
EnumWindows         = user32.EnumWindows
GetDesktopWindow    = user32.GetDesktopWindow
ShowWindow          = user32.ShowWindow
SW_HIDE = 0
SW_SHOW = 5

# Optional PrintWindow (may fail for some UWP/accelerated apps)
PrintWindow = user32.PrintWindow
PW_RENDERFULLCONTENT = 0x00000002

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

def SHAppBarMessage(msg, data):
    return shell32.SHAppBarMessage(ctypes.c_uint(msg), ctypes.byref(data))

# Helper functions for window capture
def _rect_to_tuple(rect):
    r = RECT()
    GetWindowRect(rect, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

def _get_top_level_at_point(x, y):
    hwnd = WindowFromPoint(POINT(x, y))
    if not hwnd:
        return 0
    return GetAncestor(hwnd, GA_ROOT)

def _intersect_rects(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1, y1 = max(ax1, bx1), max(ay1, by1)
    x2, y2 = min(ax2, bx2), min(ay2, by2)
    if x2 > x1 and y2 > y1:
        return (x1, y1, x2, y2)
    return None

# ---------------- Theme and Styling ----------------

def detect_theme_colors():
    """Detect system theme and return color palette"""
    app = QApplication.instance()
    if app is None:
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
    except:
        is_dark = False
    
    if is_dark:
        return {
            'bg': '#1a1a1a',        # Dark background
            'panel': '#2d2d2d',     # Control panel background
            'fg': '#ffffff',        # Text/icons
            'border': '#404040',    # Borders
            'hover': '#404040',     # Hover state
            'pressed': '#505050',   # Pressed state
            'accent': '#0078d4'     # Windows accent color
        }
    else:
        return {
            'bg': '#ffffff',        # Light background
            'panel': '#f8f8f8',     # Control panel background
            'fg': '#323130',        # Text/icons
            'border': '#d1d1d1',    # Borders
            'hover': '#f3f2f1',     # Hover state
            'pressed': '#e1dfdd',   # Pressed state
            'accent': '#0078d4'     # Windows accent color
        }

def create_control_bar_stylesheet(colors):
    """Create stylesheet for control bar based on theme colors"""
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

def create_icon(theme_name, fallback_svg, colors):
    """Create icon with theme fallback"""
    # Try system theme first
    icon = QIcon.fromTheme(theme_name)
    if not icon.isNull():
        return icon
    
    # Fallback to SVG with theme colors
    # For now, use simple text-based icons as fallback
    # In a full implementation, you'd load SVG files and recolor them
    return create_text_icon(fallback_svg, colors)

def create_text_icon(text, colors):
    """Create a simple text-based icon as fallback"""
    # Create a pixmap with text
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtCore.Qt.transparent)
    
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    
    # Set font and color
    font = painter.font()
    font.setPixelSize(16)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QtGui.QColor(colors['fg']))
    
    # Draw text centered
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, text)
    painter.end()
    
    return QIcon(pixmap)

def get_control_icons(colors):
    """Get all control icons with theme adaptation"""
    return {
        'left': create_icon('go-previous', '◀', colors),
        'right': create_icon('go-next', '▶', colors),
        'dock': create_icon('view-fullscreen', '⊞', colors),
        'undock': create_icon('view-restore', '⊡', colors),
        'exit': create_icon('window-close', '✕', colors),
        'camera': create_icon('camera-photo', '📷', colors)
    }

# ---------------- JavaScript helpers for screenshot functionality ----------------

def _build_check_generating_js():
    """JavaScript to detect if ChatGPT is currently generating"""
    return r"""(function(){
      const stopBtn = document.querySelector('button[aria-label*="Stop"], button[data-testid="stop-button"]');
      const busyComposer = document.querySelector('[data-testid="composer"]:is([aria-busy="true"], .is-generating)');
      return !!(stopBtn || busyComposer);
    })();"""

def _build_paste_js(b64):
    """JavaScript to inject image via synthetic paste event"""
    b64q = json.dumps(b64)  # safe string literal
    return f"""
    (function(){{
      const composer = document.querySelector('[data-testid="composer"] textarea, [contenteditable="true"][data-testid="textbox"], div[contenteditable="true"]');
      if (!composer) return false;
      function base64ToUint8Array(b64){{
        const binary = atob(b64);
        const len = binary.length;
        const bytes = new Uint8Array(len);
        for (let i=0;i<len;i++) bytes[i] = binary.charCodeAt(i);
        return bytes;
      }}
      const bytes = base64ToUint8Array({b64q});
      const blob = new Blob([bytes], {{ type: 'image/png' }});
      const file = new File([blob], 'screenshot.png', {{ type: 'image/png' }});
      const dt = new DataTransfer();
      dt.items.add(file);
      let evt;
      try {{
        evt = new ClipboardEvent('paste', {{ clipboardData: dt, bubbles: true, cancelable: true }});
      }} catch (e) {{
        evt = new Event('paste', {{ bubbles: true, cancelable: true }});
        try {{ Object.defineProperty(evt, 'clipboardData', {{ value: dt }}); }} catch(e2) {{}}
      }}
      composer.focus();
      return composer.dispatchEvent(evt);
    }})();"""

# ---------------- Qt window that registers as AppBar ----------------

class AppBarWidget(QWidget):
    def __init__(self, desired_width=500, edge=ABE_LEFT, title="ChatGPT Sidebar", url_string=None, parent=None):
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
        self.colors = detect_theme_colors()
        self.icons = get_control_icons(self.colors)

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

        # Register after shown (so we have a real HWND)
        if self.is_docked:
            QtCore.QTimer.singleShot(0, self._register_appbar)
        else:
            # Start undocked if that was the last state
            QtCore.QTimer.singleShot(0, self._start_undocked)
    
    def _create_web_profile(self):
        """Create secure web profile for session persistence"""
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
    
    def _create_control_bar(self):
        """Create themed control bar with icons"""
        self.controls = QFrame(self)
        self.controls.setFrameShape(QFrame.NoFrame)
        self.controls.setFixedHeight(40)
        self.controls.setStyleSheet(create_control_bar_stylesheet(self.colors))
        
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
        self.btnShot.setToolTip("Screenshot to chat")
        self.btnShot.setAccessibleName("Screenshot")
        
        # Side toggle button
        if self.edge == ABE_LEFT:
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
    
    def _start_undocked(self):
        """Start in undocked mode with restored geometry"""
        # Set normal window flags
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        
        # Restore geometry if available
        geometry = self.settings.value("undocked_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size and center
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width, height = 900, 1000
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_button_icons_and_tooltips()
        
        # Initialize toast system
        self._toast_label = None
        self._toast_timer = QtCore.QTimer()
        self._toast_timer.timeout.connect(self._hide_toast)
        self._toast_timer.setSingleShot(True)

    # ----- Toast notification system -----
    def _show_toast(self, message, duration_ms=3000):
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
    
    def _hide_toast(self):
        """Hide the toast message"""
        if self._toast_label:
            self._toast_label.deleteLater()
            self._toast_label = None
    
    def _other_work_area_rect(self):
        """Compute the opposite work area rectangle from our AppBar"""
        mon = QGuiApplication.primaryScreen().geometry()
        # Our AppBar rect after docking:
        hwnd = int(self.winId())
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        appbar = (r.left, r.top, r.right, r.bottom)
        monitor = (mon.left(), mon.top(), mon.right(), mon.bottom())
        # Return the remaining area on the opposite side
        if self.edge == ABE_LEFT:
            # right side
            return (appbar[2], monitor[1], monitor[2], monitor[3])
        else:
            # left side
            return (monitor[0], monitor[1], appbar[0], monitor[3])
    
    def _find_excluded_hwnds(self):
        """Get set of HWNDs to exclude from capture"""
        excluded = {int(self.winId())}
        # If native-app mode, exclude docked ChatGPT app window
        if hasattr(self, '_native_chatgpt_hwnd') and self._native_chatgpt_hwnd:
            excluded.add(self._native_chatgpt_hwnd)
        return excluded
    
    def _hwnd_rect(self, hwnd):
        """Get rectangle of a window handle"""
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        return (r.left, r.top, r.right, r.bottom)
    
    def _visible_top_window_in_rect(self, wr):
        """Find the top-most visible window in the given rectangle"""
        # 1) Try foreground window if it intersects and is not excluded
        excluded = self._find_excluded_hwnds()
        fg = GetForegroundWindow()
        if fg and fg not in excluded and IsWindowVisible(fg):
            rr = self._hwnd_rect(fg)
            if _intersect_rects(rr, wr):
                return fg

        # 2) Try window under the center point of work area
        cx = (wr[0] + wr[2]) // 2
        cy = (wr[1] + wr[3]) // 2
        atpt = _get_top_level_at_point(cx, cy)
        if atpt and atpt not in excluded and IsWindowVisible(atpt):
            rr = self._hwnd_rect(atpt)
            if _intersect_rects(rr, wr):
                return atpt

        # 3) Enumerate top-level windows from front to back
        found = 0
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum_cb(hwnd, lParam):
            nonlocal found
            if found:
                return False
            if hwnd in excluded:
                return True
            if not IsWindowVisible(hwnd):
                return True
            rr = self._hwnd_rect(hwnd)
            if _intersect_rects(rr, wr):
                found = hwnd
                return False
            return True

        EnumWindows(_enum_cb, 0)
        return found
    
    def _capture_hwnd_to_qimage(self, hwnd):
        """Capture a window handle to QImage using PrintWindow/BitBlt"""
        # Get rect
        l, t, r, b = self._hwnd_rect(hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
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
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0  # BI_RGB
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

    # ----- Mouse drag (for moving when not docked) -----
    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag:
            self.move((e.globalPosition().toPoint() - self._drag_pos))
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag = False

    # ----- Native event hook (to catch ABN_POSCHANGED) -----
    def nativeEvent(self, eventType, message):
        # Only handle AppBar events when docked
        if not self.is_docked:
            return False, 0
            
        # message is MSG* on Windows
        if eventType == "windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self._callback_msg and msg.wParam == ABN_POSCHANGED:
                self._dock()
        return False, 0

    def _register_appbar(self):
        hwnd = int(self.winId())
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = hwnd
        abd.uCallbackMessage = self._callback_msg
        SHAppBarMessage(ABM_NEW, abd)
        self._registered = True
        self._dock()

    def _monitor_rect(self):
        # Use full geometry for AppBar - the system will handle taskbar exclusion
        screen = QGuiApplication.primaryScreen().geometry()
        return RECT(screen.left(), screen.top(), screen.right(), screen.bottom())

    def _dock(self):
        hwnd = int(self.winId())
        rect = self._monitor_rect()
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = hwnd
        abd.uEdge = self.edge
        abd.rc = rect

        # Propose width from saved desired_width, keep full height
        if self.edge == ABE_LEFT:
            abd.rc.right = abd.rc.left + int(self.desired_width)
        else:
            abd.rc.left = abd.rc.right - int(self.desired_width)
        # Ensure full height is maintained
        abd.rc.top = rect.top
        abd.rc.bottom = rect.bottom

        SHAppBarMessage(ABM_QUERYPOS, abd)

        # Enforce final width again before setpos, ensure full height
        if self.edge == ABE_LEFT:
            abd.rc.right = abd.rc.left + int(self.desired_width)
        else:
            abd.rc.left = abd.rc.right - int(self.desired_width)
        # Re-enforce full height after query
        abd.rc.top = rect.top
        abd.rc.bottom = rect.bottom

        SHAppBarMessage(ABM_SETPOS, abd)

        # Apply to our window
        x, y = abd.rc.left, abd.rc.top
        w, h = abd.rc.right - abd.rc.left, abd.rc.bottom - abd.rc.top
        user32.MoveWindow(hwnd, x, y, w, h, True)

    # ----- Button slot methods -----
    def on_toggle_side(self):
        """Toggle between left and right docking"""
        if self.edge == ABE_LEFT:
            self.edge = ABE_RIGHT
        else:
            self.edge = ABE_LEFT
        
        # Save preference
        self.settings.setValue("edge", self.edge)
        
        # Update icon and tooltip
        self._update_button_icons_and_tooltips()
        
        # If docked, re-dock to new side
        if self.is_docked:
            self._dock()
    
    def on_toggle_dock(self):
        """Toggle between docked and undocked state"""
        if self.is_docked:
            self._undock_to_normal_window()
        else:
            self._redock_appbar()
    
    def on_exit(self):
        """Close the application"""
        self._save_preferences()
        self.close()
    
    def on_screenshot_to_chat(self):
        """Capture screenshot of other window and paste into chat"""
        # Check if we have a webview (not available in native-app mode without webview)
        if not self.has_webview:
            self._show_toast("Screenshot-to-chat is only available in WebView mode.")
            return
        
        # 0) Determine the opposite work area rectangle
        wr = self._other_work_area_rect()

        # 1) Resolve the target HWND in that rect (exclude ourselves and native ChatGPT if present)
        hwnd_target = self._visible_top_window_in_rect(wr)
        if not hwnd_target:
            self._show_toast("No window to capture in the work area.")
            return

        # 2) Temporarily hide our bar to avoid bleed-in (it's on the edge, but just in case)
        ShowWindow(int(self.winId()), SW_HIDE)
        try:
            img = self._capture_hwnd_to_qimage(hwnd_target)
        finally:
            ShowWindow(int(self.winId()), SW_SHOW)

        if img is None or img.isNull():
            self._show_toast("Couldn't capture that window.")
            return

        # 3) Encode PNG to base64 (in-memory)
        ba = QtCore.QByteArray()
        buf = QBuffer(ba)
        buf.open(QtCore.QIODevice.WriteOnly)
        img.save(buf, "PNG")
        b64 = base64.b64encode(bytes(ba)).decode("ascii")

        # 4) Block if generating, otherwise paste via synthetic DataTransfer (existing logic)
        self.web.page().runJavaScript(_build_check_generating_js(),
            lambda is_busy: self._after_check_and_paste(is_busy, b64))
    
    def _after_check_and_paste(self, is_busy, b64):
        """Handle result of generation check and proceed with paste if not busy"""
        if is_busy:
            self._show_toast("Can't attach while generating.")
            return
        
        # Proceed with paste injection
        js = _build_paste_js(b64)
        self.web.page().runJavaScript(js, lambda ok: self._after_paste_result(ok))
    
    def _after_paste_result(self, ok):
        """Handle result of paste injection"""
        if not ok:
            self._show_toast("Couldn't paste into the chat. Click the message box and retry.")
        else:
            self._show_toast("Screenshot attached.", duration_ms=1500)
    
    def _save_preferences(self):
        """Save current preferences to QSettings"""
        self.settings.setValue("edge", self.edge)
        self.settings.setValue("width", self.desired_width)
        self.settings.setValue("is_docked", self.is_docked)
    
    def _undock_to_normal_window(self):
        """Convert from docked AppBar to normal window"""
        # Unregister AppBar if currently registered
        if self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(self.winId())
            SHAppBarMessage(ABM_REMOVE, abd)
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
            # Default size and center for first time undocking
            screen = QGuiApplication.primaryScreen().availableGeometry()
            width, height = 900, 1000
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.resize(width, height)
            self.move(x, y)
        
        self.show()
        self._update_button_icons_and_tooltips()
        
        # Save undocked geometry and state
        self.settings.setValue("undocked_geometry", self.saveGeometry())
        self.settings.setValue("is_docked", self.is_docked)
    
    def _redock_appbar(self):
        """Convert from normal window back to docked AppBar"""
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
        SHAppBarMessage(ABM_NEW, abd)
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
    
    def _redock_native_app(self):
        """Re-dock the native ChatGPT app to the AppBar rect"""
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

    def closeEvent(self, e):
        # Save preferences before closing
        self._save_preferences()
        
        # Unregister AppBar if currently registered
        if self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(self.winId())
            SHAppBarMessage(ABM_REMOVE, abd)
        super().closeEvent(e)

# ---------------- Helper: find & dock the existing ChatGPT app window ----------------

def find_chatgpt_hwnd():
    """
    Try a few likely patterns. You can refine with Spy++/Inspect.exe if needed.
    """
    candidates = [
        ("", "ChatGPT"),               # title match
        ("Chrome_WidgetWin_1", None),  # common Electron class
        ("Chrome_WidgetWin_0", None),
    ]
    for cls, title in candidates:
        hwnd = FindWindowW(cls or None, title or None)
        if hwnd:
            return hwnd
    return 0

def set_window_rect(hwnd, x, y, w, h):
    SetWindowPos(hwnd, HWND_TOP, x, y, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOZORDER)

# ---------------- Main ----------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=420, help="Sidebar width in pixels")
    parser.add_argument("--native-app", action="store_true", help="Dock the installed ChatGPT app instead of using embedded webview")
    parser.add_argument("--url", default="https://chat.openai.com/", help="URL to load in embedded webview")
    parser.add_argument("--dock-title", default="ChatGPT", help="Window title to look for when docking the installed app")
    args = parser.parse_args()

    app = QApplication(sys.argv)

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
            QtWidgets.QMessageBox.critical(None, "Missing dependency",
                f"QtWebEngine is not available. Please install PySide6 with WebEngine support.\nError: {e}")
            sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script requires Windows.")
        sys.exit(1)
    main()
