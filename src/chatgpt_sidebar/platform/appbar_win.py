"""Windows AppBar implementation for docking the sidebar."""

import ctypes
from ctypes import wintypes
from typing import Tuple
from PySide6.QtGui import QGuiApplication

from ..utils.logging import get_logger


logger = get_logger(__name__)


# Win32 API DLL bindings
user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32


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


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", ctypes.c_uint),
        ("uEdge", ctypes.c_uint),
        ("rc", RECT),
        ("lParam", ctypes.c_int)
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_uint32)
    ]


class AppBarWin:
    """Windows AppBar for docking a window to the edge of the screen."""
    
    def __init__(self, hwnd: int, callback_msg: int) -> None:
        """Initialize the AppBar.
        
        Args:
            hwnd: Window handle
            callback_msg: Callback message ID for AppBar notifications
        """
        self._hwnd = hwnd
        self._callback_msg = callback_msg
        self._registered = False
        self._edge = AppBarEdge.LEFT
        self._width = 420
    
    def is_docked(self) -> bool:
        """Check if the AppBar is currently docked.
        
        Returns:
            bool: True if docked, False otherwise
        """
        return self._registered
    
    def dock(self, edge: str, width: int) -> None:
        """Dock the AppBar to the specified edge.
        
        Args:
            edge: Edge to dock to ("left" or "right")
            width: Width of the docked AppBar
        """
        # Convert string edge to constant
        if edge.lower() == "left":
            self._edge = AppBarEdge.LEFT
        elif edge.lower() == "right":
            self._edge = AppBarEdge.RIGHT
        else:
            logger.warning(f"Invalid edge: {edge}, defaulting to left")
            self._edge = AppBarEdge.LEFT
        
        self._width = width
        
        # Register if not already registered
        if not self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = self._hwnd
            abd.uCallbackMessage = self._callback_msg
            shell32.SHAppBarMessage(ctypes.c_uint(AppBarMessage.NEW), ctypes.byref(abd))
            self._registered = True
            logger.info("AppBar registered")
        
        # Perform docking
        self._perform_dock()
    
    def undock(self) -> None:
        """Undock the AppBar."""
        if self._registered:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = self._hwnd
            shell32.SHAppBarMessage(ctypes.c_uint(AppBarMessage.REMOVE), ctypes.byref(abd))
            self._registered = False
            logger.info("AppBar unregistered")
    
    def reposition(self) -> None:
        """Reposition the AppBar (called when screen configuration changes)."""
        if self._registered:
            self._perform_dock()
    
    def _get_monitor_rect(self) -> RECT:
        """Get the monitor rectangle for the window.
        
        Returns:
            RECT: The monitor rectangle
        """
        # Get the monitor this window is on (MONITOR_DEFAULTTONEAREST = 2)
        hMonitor = user32.MonitorFromWindow(self._hwnd, 2)
        
        if hMonitor:
            # Get monitor info
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                logger.info(f"Monitor rect: left={mi.rcMonitor.left}, top={mi.rcMonitor.top}, "
                           f"right={mi.rcMonitor.right}, bottom={mi.rcMonitor.bottom}")
                return mi.rcMonitor
        
        # Fallback to Qt if Windows API fails
        try:
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry()
            logger.info(f"Fallback Qt geometry: {geometry.left()}, {geometry.top()}, "
                       f"{geometry.right()}, {geometry.bottom()}")
            return RECT(geometry.left(), geometry.top(), geometry.right(), geometry.bottom())
        except Exception as e:
            logger.error(f"Failed to get monitor rect: {e}")
            # Return a default rect
            return RECT(0, 0, 1920, 1080)
    
    def _perform_dock(self) -> None:
        """Perform the actual docking operation."""
        rect = self._get_monitor_rect()
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = self._hwnd
        abd.uEdge = self._edge
        abd.rc = rect
        
        # Store the original screen bounds
        screen_left = rect.left
        screen_top = rect.top
        screen_right = rect.right
        screen_bottom = rect.bottom
        
        # Propose width, keep full height
        if self._edge == AppBarEdge.LEFT:
            abd.rc.left = screen_left
            abd.rc.right = screen_left + int(self._width)
        else:  # RIGHT
            abd.rc.left = screen_right - int(self._width)
            abd.rc.right = screen_right
        
        # Always use full screen height
        abd.rc.top = screen_top
        abd.rc.bottom = screen_bottom
        
        # Query position
        shell32.SHAppBarMessage(ctypes.c_uint(AppBarMessage.QUERYPOS), ctypes.byref(abd))
        
        # Enforce final width again after QUERYPOS
        if self._edge == AppBarEdge.LEFT:
            abd.rc.left = screen_left
            abd.rc.right = screen_left + int(self._width)
        else:  # RIGHT
            abd.rc.left = screen_right - int(self._width)
            abd.rc.right = screen_right
        
        # Re-enforce full height
        abd.rc.top = screen_top
        abd.rc.bottom = screen_bottom
        
        # Set position
        shell32.SHAppBarMessage(ctypes.c_uint(AppBarMessage.SETPOS), ctypes.byref(abd))
        
        # Apply to window
        x, y = abd.rc.left, abd.rc.top
        w, h = abd.rc.right - abd.rc.left, abd.rc.bottom - abd.rc.top
        user32.MoveWindow(self._hwnd, x, y, w, h, True)
        
        logger.info(f"AppBar docked to edge {self._edge} at ({x}, {y}) with size {w}x{h}")
    
    def get_opposite_work_area(self) -> Tuple[int, int, int, int]:
        """Get the work area rectangle opposite to the docked AppBar.
        
        Returns:
            Tuple[int, int, int, int]: Rectangle (left, top, right, bottom)
        """
        # Get monitor rect
        mon_rect = self._get_monitor_rect()
        monitor = (mon_rect.left, mon_rect.top, mon_rect.right, mon_rect.bottom)
        
        # Get AppBar rect
        r = RECT()
        user32.GetWindowRect(self._hwnd, ctypes.byref(r))
        appbar = (r.left, r.top, r.right, r.bottom)
        
        # Return the remaining area on the opposite side
        if self._edge == AppBarEdge.LEFT:
            # Right side
            return (appbar[2], monitor[1], monitor[2], monitor[3])
        else:
            # Left side
            return (monitor[0], monitor[1], appbar[0], monitor[3])
    
    @property
    def callback_msg(self) -> int:
        """Get the callback message ID.
        
        Returns:
            int: Callback message ID
        """
        return self._callback_msg

