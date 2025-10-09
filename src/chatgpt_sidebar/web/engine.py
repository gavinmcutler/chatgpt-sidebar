"""Web engine interface protocol."""

from typing import Protocol, Callable, Optional


class Engine(Protocol):
    """Protocol for web engine implementations."""
    
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
    
    def get_widget(self):
        """Get the underlying widget for embedding.
        
        Returns:
            The widget that can be added to layouts
        """
        ...

