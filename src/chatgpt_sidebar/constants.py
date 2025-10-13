"""Application-wide constants."""

# Application defaults
DEFAULT_WIDTH = 420
DEFAULT_WIDTH_PERCENT = 20
DEFAULT_URL = "https://chat.openai.com/"
DEFAULT_TITLE = "ChatGPT Sidebar"
DEFAULT_ZOOM = 1.0
DEFAULT_OPACITY = 1.0

# UI timing constants (milliseconds)
WEB_ENGINE_INIT_DELAY_MS = 100  # Delay before initializing web engine to show UI first
TOAST_DURATION_MS = 3000  # Standard toast notification duration
SCREENSHOT_TOAST_DURATION_MS = 1500  # Quick toast for screenshot feedback
SETTINGS_SAVE_DELAY_MS = 500  # Debounce delay for auto-saving settings

# UI dimensions
TOPBAR_HEIGHT_PX = 34  # Height of the top control bar
BUTTON_SIZE_PX = 26  # Size of control buttons
BUTTON_PADDING_PX = 4  # Padding inside buttons
BUTTON_SPACING_PX = 4  # Spacing between buttons
LAYOUT_MARGIN_PX = 6  # Margin around layout

# Appearance defaults
THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"

FONT_SIZE_SMALL = "small"
FONT_SIZE_MEDIUM = "medium"
FONT_SIZE_LARGE = "large"

# Zoom levels
ZOOM_MIN = 0.5
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1

# Width constraints
WIDTH_PERCENT_MIN = 10
WIDTH_PERCENT_MAX = 50
WIDTH_PERCENT_STEP = 5

# Opacity constraints
OPACITY_MIN = 0.3
OPACITY_MAX = 1.0

# Application metadata
APP_ORGANIZATION = "ChatGPTSidebar"
APP_NAME = "App"
LOG_FILE_NAME = "chatgpt_sidebar.log"

