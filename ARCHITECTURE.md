# ChatGPT Sidebar - Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Entry                        │
│                         (app.py)                                │
│  - Parses command-line arguments                                │
│  - Sets up logging                                              │
│  - Creates QApplication                                         │
│  - Instantiates MainWindow                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Main Window                             │
│                      (main_window.py)                           │
│  - Composes all components                                      │
│  - Handles window lifecycle                                     │
│  - Manages docking/undocking state                              │
│  - Coordinates component interactions                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
       ┌──────────────┐  ┌─────────┐  ┌──────────┐
       │   TopBar     │  │ Sidebar │  │ AppBarWin│
       │ (topbar.py)  │  │(sidebar)│  │(appbar)  │
       └──────────────┘  └─────────┘  └──────────┘
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                  ┌─────────┐  ┌──────────┐
                  │ Engine  │  │ Settings │
                  │ (web)   │  │   View   │
                  └─────────┘  └──────────┘
```

## Module Organization

### Layer 1: Application Bootstrap
**Module:** `app.py`
- **Responsibility:** Application initialization and lifecycle
- **Dependencies:** main_window, utils.logging
- **Entry Point:** `main()` function

### Layer 2: Main Window Composition
**Module:** `main_window.py`
- **Responsibility:** Orchestrates all components
- **Dependencies:** ui, web, platform, features, settings
- **Key Features:**
  - Event handling
  - Signal routing
  - State management

### Layer 3: Component Modules

#### UI Components
```
ui/
├── theme.py       # Theme detection and styling
├── topbar.py      # Control bar with action buttons
└── sidebar.py     # Stacked widget (webview + settings)
```

- **theme.py**: System theme detection, icon generation, stylesheets
- **topbar.py**: Buttons for screenshot, settings, dock/undock, exit
- **sidebar.py**: Switches between webview and settings panel

#### Web Engine
```
web/
├── engine.py              # Protocol interface
└── engine_qtwebengine.py  # QtWebEngine implementation
```

- **engine.py**: Defines web engine contract (Protocol)
- **engine_qtwebengine.py**: Implements with QtWebEngine, manages profile

#### Platform Integration
```
platform/
└── appbar_win.py  # Windows AppBar implementation
```

- **appbar_win.py**: Win32 API wrapper for AppBar functionality

#### Features
```
features/
├── screenshot.py  # Window capture via Win32 API
└── paste_js.py    # JavaScript code generators
```

- **screenshot.py**: Captures windows, converts to PNG/Base64
- **paste_js.py**: Builds JS for synthetic paste events

#### Configuration
```
settings/
└── config.py  # QSettings wrapper
```

- **config.py**: Type-safe configuration management

#### Utilities
```
utils/
├── logging.py  # Logging setup
└── paths.py    # Path utilities
```

- **logging.py**: Configures application logging
- **paths.py**: Manages profile/cache/storage paths

## Component Interactions

### 1. Application Startup

```
app.py::main()
  │
  ├─> setup_logging()
  ├─> Create QApplication
  ├─> Create MainWindow
  │     │
  │     ├─> Load Config
  │     ├─> Detect Theme
  │     ├─> Create TopBar
  │     ├─> Create Engine
  │     ├─> Create Sidebar
  │     │     └─> Add Engine widget
  │     └─> Create AppBarWin
  │
  └─> app.exec()
```

### 2. Screenshot Flow

```
User clicks screenshot button
  │
  ▼
TopBar emits screenshot_clicked signal
  │
  ▼
MainWindow::on_screenshot_to_chat()
  │
  ├─> Get work area from AppBarWin
  ├─> Find target window (screenshot.py)
  ├─> Capture window to QImage (screenshot.py)
  ├─> Convert to PNG + Base64 (screenshot.py)
  ├─> Build paste JS (paste_js.py)
  └─> Evaluate JS in Engine
```

### 3. Dock/Undock Flow

```
User clicks dock/undock button
  │
  ▼
TopBar emits toggle_dock_clicked signal
  │
  ▼
MainWindow::on_toggle_dock()
  │
  ├─ If docked:
  │   ├─> AppBarWin.undock()
  │   ├─> Change window flags
  │   ├─> Restore geometry
  │   └─> Save state to Config
  │
  └─ If undocked:
      ├─> Save geometry to Config
      ├─> Change window flags
      ├─> Create new AppBarWin
      ├─> AppBarWin.dock()
      └─> Save state to Config
```

### 4. Settings Flow

```
User clicks settings button
  │
  ▼
TopBar emits settings_clicked signal
  │
  ▼
MainWindow::on_show_settings()
  │
  ▼
Sidebar::show_settings()
  │
  ├─> Create settings view (if first time)
  │     │
  │     ├─> Load current config
  │     ├─> Create UI controls
  │     └─> Connect signals
  │
  └─> Switch to settings page (index 1)
```

## Design Patterns Used

### 1. Protocol Pattern
**Where:** `web/engine.py`
**Purpose:** Define interface for web engines without implementation
**Benefit:** Allows multiple engine implementations (QtWebEngine, pywebview, etc.)

### 2. Composition Pattern
**Where:** `main_window.py`
**Purpose:** Compose window from smaller components
**Benefit:** Each component is independently testable and reusable

### 3. Signal/Slot Pattern
**Where:** UI components (`topbar.py`, `sidebar.py`)
**Purpose:** Loose coupling between components
**Benefit:** Components don't need to know about each other

### 4. Facade Pattern
**Where:** `config.py`, `appbar_win.py`
**Purpose:** Simplify complex APIs (QSettings, Win32 API)
**Benefit:** Clean, easy-to-use interfaces

### 5. Factory Pattern
**Where:** `theme.py` icon creation
**Purpose:** Create icons with fallbacks
**Benefit:** Robust icon handling across different systems

## Data Flow

### Configuration Data
```
Config (QSettings)
  ↕
main_window.py
  ↕
UI Components
```

### User Actions
```
User Input
  ↓
TopBar/Sidebar (emits signals)
  ↓
MainWindow (handles signals)
  ↓
AppBarWin/Engine/Config (performs action)
```

### Window State
```
AppBarWin (Win32 state)
  ↕
MainWindow (coordinates)
  ↕
Config (persists state)
```

## Type System

All public interfaces use type hints:

```python
# Function signatures
def dock(self, edge: str, width: int) -> None:
    ...

# Protocol definitions
class Engine(Protocol):
    def navigate(self, url: str) -> None: ...
    def evaluate_js(self, js: str, callback: Optional[Callable[[bool], None]]) -> None: ...

# Configuration
def get_width(self, default: int = 420) -> int:
    ...
```

## Error Handling

- Logging at module level: `logger = get_logger(__name__)`
- Try-except blocks around platform-specific code
- Graceful fallbacks (theme detection, icon loading)
- User-facing error messages via toast notifications

## Testing Strategy (Future)

```
Unit Tests:
  ├── utils/*.py        # Pure functions
  ├── features/*.py     # Business logic
  ├── settings/config.py # Data layer
  └── platform/*.py     # Platform abstraction

Integration Tests:
  ├── UI components     # With mocked backend
  └── Full flow        # End-to-end

Mocking Strategy:
  ├── Mock AppBarWin for cross-platform testing
  ├── Mock Engine for UI testing
  └── Mock Config for state testing
```

## Performance Considerations

1. **Lazy Loading**: Settings view created on first access
2. **Efficient Rendering**: Web engine uses hardware acceleration
3. **Minimal Dependencies**: Only essential modules imported
4. **Resource Cleanup**: Proper cleanup in closeEvent

## Security Considerations

1. **Isolated Profile**: Web engine uses separate profile directory
2. **No Eval**: JavaScript is built securely with json.dumps()
3. **Win32 Safety**: Proper error handling for Win32 API calls
4. **Settings Validation**: Type-checked configuration values

## Future Enhancements

1. **Alternative Web Engines**: Add pywebview implementation
2. **Cross-Platform**: Abstract platform layer for Linux/macOS
3. **Plugin System**: Allow loading custom features
4. **Themes**: Custom theme support beyond auto-detection
5. **Tests**: Comprehensive test suite
6. **CI/CD**: Automated builds and releases

