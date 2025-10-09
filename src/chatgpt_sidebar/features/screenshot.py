"""Screenshot capture functionality."""

import base64
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, Set
from PySide6.QtCore import QBuffer, QIODevice, QByteArray
from PySide6.QtGui import QImage

from ..utils.logging import get_logger


logger = get_logger(__name__)


# Win32 API DLL bindings
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


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


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


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
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", ctypes.c_uint32 * 3)
    ]


def _get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Get rectangle of a window handle.
    
    Args:
        hwnd: Window handle
        
    Returns:
        Tuple[int, int, int, int]: Window rectangle (left, top, right, bottom)
    """
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def _intersect_rects(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> Optional[Tuple[int, int, int, int]]:
    """Calculate the intersection of two rectangles.
    
    Args:
        a: First rectangle (left, top, right, bottom)
        b: Second rectangle (left, top, right, bottom)
        
    Returns:
        Optional[Tuple[int, int, int, int]]: Intersection rectangle or None
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1, y1 = max(ax1, bx1), max(ay1, by1)
    x2, y2 = min(ax2, bx2), min(ay2, by2)
    if x2 > x1 and y2 > y1:
        return (x1, y1, x2, y2)
    return None


def _get_top_level_at_point(x: int, y: int) -> int:
    """Get the top-level window at the specified point.
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        int: Window handle or 0 if none found
    """
    hwnd = user32.WindowFromPoint(POINT(x, y))
    if not hwnd:
        return 0
    return user32.GetAncestor(hwnd, GA_ROOT)


def find_visible_window_in_rect(work_rect: Tuple[int, int, int, int], excluded_hwnds: Set[int]) -> int:
    """Find the top-most visible window in the given rectangle.
    
    Args:
        work_rect: Work area rectangle (left, top, right, bottom)
        excluded_hwnds: Set of window handles to exclude
        
    Returns:
        int: Window handle or 0 if none found
    """
    # 1) Try foreground window if it intersects and is not excluded
    fg = user32.GetForegroundWindow()
    if fg and fg not in excluded_hwnds and user32.IsWindowVisible(fg):
        rr = _get_window_rect(fg)
        if _intersect_rects(rr, work_rect):
            return fg
    
    # 2) Try window under the center point of work area
    cx = (work_rect[0] + work_rect[2]) // 2
    cy = (work_rect[1] + work_rect[3]) // 2
    atpt = _get_top_level_at_point(cx, cy)
    if atpt and atpt not in excluded_hwnds and user32.IsWindowVisible(atpt):
        rr = _get_window_rect(atpt)
        if _intersect_rects(rr, work_rect):
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
        if not user32.IsWindowVisible(hwnd):
            return True
        rr = _get_window_rect(hwnd)
        if _intersect_rects(rr, work_rect):
            found = hwnd
            return False
        return True
    
    user32.EnumWindows(_enum_cb, 0)
    return found


def capture_window_to_qimage(hwnd: int) -> Optional[QImage]:
    """Capture a window handle to QImage using PrintWindow/BitBlt.
    
    Args:
        hwnd: Window handle to capture
        
    Returns:
        Optional[QImage]: Captured image or None on failure
    """
    try:
        # Get rect
        l, t, r, b = _get_window_rect(hwnd)
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
        ok = user32.PrintWindow(hwnd, hdcMemDC, PW_RENDERFULLCONTENT)
        
        if not ok:
            # Fallback: BitBlt what's on screen
            gdi32.BitBlt(hdcMemDC, 0, 0, w, h, hdcWindow, 0, 0, 0x00CC0020)  # SRCCOPY
        
        # Extract bitmap bits into QImage
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
        img = QImage(bytes(pixel_data), w, h, QImage.Format.Format_ARGB32)
        return img.copy()  # Detach from buffer
    
    except Exception as e:
        logger.error(f"Failed to capture window {hwnd}: {e}")
        return None


def qimage_to_png_base64(image: QImage) -> str:
    """Convert QImage to PNG format and encode as base64.
    
    Args:
        image: QImage to convert
        
    Returns:
        str: Base64-encoded PNG data
    """
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    return base64.b64encode(bytes(ba)).decode("ascii")


def hide_window(hwnd: int) -> None:
    """Hide a window.
    
    Args:
        hwnd: Window handle to hide
    """
    user32.ShowWindow(hwnd, SW.HIDE)


def show_window(hwnd: int) -> None:
    """Show a window.
    
    Args:
        hwnd: Window handle to show
    """
    user32.ShowWindow(hwnd, SW.SHOW)

