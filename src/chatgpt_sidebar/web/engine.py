"""Web engine interface protocol."""

from typing import Protocol, Callable, Optional, Any, Dict


class Engine(Protocol):
    """Protocol for web engine implementations.
    
    This protocol defines the interface that all web engine implementations
    must follow. It enables swapping different web engines (QtWebEngine,
    pywebview, etc.) without changing the rest of the application.
    """
    
    def __init__(self, parent=None, colors: Optional[Dict[str, str]] = None) -> None:
        """Initialize the engine with optional theme colors."""
        ...
    
    def navigate(self, url: str) -> None:
        """Navigate to a URL.
        
        Args:
            url: URL to navigate to
        """
        ...
    
    def evaluate_js(self, js: str, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Evaluate JavaScript code.
        
        Args:
            js: JavaScript code to evaluate
            callback: Optional callback to receive result (True/False for success)
        """
        ...
    
    def set_zoom(self, factor: float) -> None:
        """Set the zoom factor.
        
        Args:
            factor: Zoom factor (1.0 = 100%)
        """
        ...
    
    def get_widget(self) -> Any:
        """Get the underlying widget for embedding.
        
        Returns:
            Any: The widget that can be added to layouts (QWidget or compatible)
        """
        ...

