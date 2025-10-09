"""QtWebEngine-based web engine implementation."""

from typing import Callable, Optional
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..utils.logging import get_logger
from ..utils.paths import get_profile_path, get_cache_path, get_storage_path


logger = get_logger(__name__)


class QtWebEngine:
    """QtWebEngine-based web engine implementation."""
    
    def __init__(self, parent=None) -> None:
        """Initialize the web engine.
        
        Args:
            parent: Parent widget (optional)
        """
        self._parent = parent
        self._web_view: Optional[QWebEngineView] = None
        self._profile: Optional[QWebEngineProfile] = None
        self._create_web_view()
    
    def _create_web_view(self) -> None:
        """Create the web view with persistent profile."""
        try:
            # Create profile with persistent storage
            profile_dir = get_profile_path()
            self._profile = QWebEngineProfile(str(profile_dir), self._parent)
            self._profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
            self._profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
            
            # Set cache and storage paths
            cache_dir = get_cache_path()
            storage_dir = get_storage_path()
            
            if hasattr(self._profile, 'setHttpCachePath'):
                self._profile.setHttpCachePath(str(cache_dir))
            if hasattr(self._profile, 'setPersistentStoragePath'):
                self._profile.setPersistentStoragePath(str(storage_dir))
            
            logger.info(f"Created web profile at {profile_dir}")
            
            # Create web view with profile
            self._web_view = QWebEngineView(self._parent)
            page = QWebEnginePage(self._profile, self._web_view)
            self._web_view.setPage(page)
            
        except Exception as e:
            logger.error(f"Failed to create web view: {e}")
            raise
    
    def navigate(self, url: str) -> None:
        """Navigate to a URL.
        
        Args:
            url: URL to navigate to
        """
        if self._web_view:
            self._web_view.setUrl(QUrl(url))
            logger.info(f"Navigating to {url}")
    
    def evaluate_js(self, js: str, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Evaluate JavaScript code.
        
        Args:
            js: JavaScript code to evaluate
            callback: Optional callback to receive result
        """
        if self._web_view and self._web_view.page():
            if callback:
                self._web_view.page().runJavaScript(js, callback)
            else:
                self._web_view.page().runJavaScript(js)
    
    def set_zoom(self, factor: float) -> None:
        """Set the zoom factor.
        
        Args:
            factor: Zoom factor (1.0 = 100%)
        """
        if self._web_view:
            self._web_view.setZoomFactor(factor)
            logger.info(f"Zoom factor set to {factor}")
    
    def get_widget(self):
        """Get the underlying widget for embedding.
        
        Returns:
            QWebEngineView: The web view widget
        """
        return self._web_view
    
    def get_page(self) -> Optional[QWebEnginePage]:
        """Get the web engine page.
        
        Returns:
            Optional[QWebEnginePage]: The web page or None
        """
        if self._web_view:
            return self._web_view.page()
        return None

