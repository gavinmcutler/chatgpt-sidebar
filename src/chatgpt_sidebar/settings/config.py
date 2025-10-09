"""Configuration management using QSettings."""

from typing import Any, Optional
from PySide6.QtCore import QSettings


class Config:
    """Wrapper around QSettings for managing application configuration."""
    
    def __init__(self, organization: str = "ChatGPTSidebar", application: str = "App") -> None:
        """Initialize the configuration manager.
        
        Args:
            organization: Organization name for settings
            application: Application name for settings
        """
        self._settings = QSettings(organization, application)
    
    def get(self, key: str, default: Any = None, value_type: type = str) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            value_type: Type to cast the value to
            
        Returns:
            The configuration value
        """
        return self._settings.value(key, default, type=value_type)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._settings.setValue(key, value)
        self._settings.sync()  # Force immediate write to disk
    
    def get_edge(self) -> int:
        """Get the edge setting (left=0, right=2).
        
        Returns:
            int: Edge value
        """
        return self.get("edge", 0, int)
    
    def set_edge(self, edge: int) -> None:
        """Set the edge setting.
        
        Args:
            edge: Edge value (0=left, 2=right)
        """
        self.set("edge", edge)
    
    def get_width(self, default: int = 420) -> int:
        """Get the width setting.
        
        Args:
            default: Default width value
            
        Returns:
            int: Width value
        """
        return self.get("width", default, int)
    
    def set_width(self, width: int) -> None:
        """Set the width setting.
        
        Args:
            width: Width value
        """
        self.set("width", width)
    
    def get_width_percent(self, default: int = 20) -> int:
        """Get the width percentage setting.
        
        Args:
            default: Default width percentage
            
        Returns:
            int: Width percentage
        """
        return self.get("default_width_percent", default, int)
    
    def set_width_percent(self, percent: int) -> None:
        """Set the width percentage setting.
        
        Args:
            percent: Width percentage
        """
        self.set("default_width_percent", percent)
    
    def get_zoom(self, default: float = 1.0) -> float:
        """Get the zoom factor setting.
        
        Args:
            default: Default zoom factor
            
        Returns:
            float: Zoom factor
        """
        return self.get("zoom", default, float)
    
    def set_zoom(self, zoom: float) -> None:
        """Set the zoom factor setting.
        
        Args:
            zoom: Zoom factor
        """
        self.set("zoom", zoom)
    
    def is_docked(self, default: bool = True) -> bool:
        """Get the docked state.
        
        Args:
            default: Default docked state
            
        Returns:
            bool: Whether the sidebar is docked
        """
        return self.get("is_docked", default, bool)
    
    def set_docked(self, docked: bool) -> None:
        """Set the docked state.
        
        Args:
            docked: Whether the sidebar is docked
        """
        self.set("is_docked", docked)
    
    def get_autostart(self, default: bool = False) -> bool:
        """Get the autostart setting.
        
        Args:
            default: Default autostart state
            
        Returns:
            bool: Whether autostart is enabled
        """
        return self.get("launch_on_startup", default, bool)
    
    def set_autostart(self, autostart: bool) -> None:
        """Set the autostart setting.
        
        Args:
            autostart: Whether autostart is enabled
        """
        self.set("launch_on_startup", autostart)
    
    def get_always_on_top(self, default: bool = True) -> bool:
        """Get the always on top setting.
        
        Args:
            default: Default always on top state
            
        Returns:
            bool: Whether always on top is enabled
        """
        return self.get("always_on_top", default, bool)
    
    def set_always_on_top(self, always_on_top: bool) -> None:
        """Set the always on top setting.
        
        Args:
            always_on_top: Whether always on top is enabled
        """
        self.set("always_on_top", always_on_top)
    
    def get_undocked_geometry(self) -> Optional[bytes]:
        """Get the undocked window geometry.
        
        Returns:
            Optional[bytes]: Saved geometry or None
        """
        return self._settings.value("undocked_geometry")
    
    def set_undocked_geometry(self, geometry: bytes) -> None:
        """Set the undocked window geometry.
        
        Args:
            geometry: Window geometry to save
        """
        self.set("undocked_geometry", geometry)
    
    # -------------------------------------------------------------------------
    # Appearance settings
    # -------------------------------------------------------------------------
    
    def get_theme(self, default: str = "system") -> str:
        """Get the theme setting.
        
        Args:
            default: Default theme ("system", "light", or "dark")
            
        Returns:
            str: Theme setting
        """
        return self.get("theme", default, str)
    
    def set_theme(self, theme: str) -> None:
        """Set the theme setting.
        
        Args:
            theme: Theme to use ("system", "light", or "dark")
        """
        self.set("theme", theme)
    
    def get_opacity(self, default: float = 1.0) -> float:
        """Get the window opacity setting.
        
        Args:
            default: Default opacity (0.0 to 1.0)
            
        Returns:
            float: Opacity value
        """
        return self.get("opacity", default, float)
    
    def set_opacity(self, opacity: float) -> None:
        """Set the window opacity setting.
        
        Args:
            opacity: Opacity value (0.0 to 1.0)
        """
        self.set("opacity", opacity)
    
    def get_corner_radius(self, default: int = 0) -> int:
        """Get the corner radius setting.
        
        Args:
            default: Default corner radius in pixels
            
        Returns:
            int: Corner radius value
        """
        return self.get("corner_radius", default, int)
    
    def set_corner_radius(self, radius: int) -> None:
        """Set the corner radius setting.
        
        Args:
            radius: Corner radius in pixels
        """
        self.set("corner_radius", radius)
    
    def get_font_size(self, default: str = "medium") -> str:
        """Get the font size setting.
        
        Args:
            default: Default font size ("small", "medium", or "large")
            
        Returns:
            str: Font size setting
        """
        return self.get("font_size", default, str)
    
    def set_font_size(self, font_size: str) -> None:
        """Set the font size setting.
        
        Args:
            font_size: Font size ("small", "medium", or "large")
        """
        self.set("font_size", font_size)

