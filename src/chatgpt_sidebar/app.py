"""Application bootstrap and main entry point."""

import sys
import signal
import argparse
from PySide6.QtWidgets import QApplication, QMessageBox

from .main_window import MainWindow, DEFAULT_WIDTH, DEFAULT_URL
from .utils.logging import setup_logging, get_logger


logger = get_logger(__name__)


def main() -> None:
    """Main entry point for the ChatGPT Sidebar application."""
    # Check platform
    if sys.platform != "win32":
        print("This application requires Windows.")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ChatGPT Sidebar - Windows sidebar for ChatGPT")
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Sidebar width in pixels (default: 420)"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="URL to load in embedded webview (default: https://chat.openai.com/)"
    )
    parser.add_argument(
        "--enable-logging",
        action="store_true",
        help="Enable logging to console and file (disabled by default)"
    )
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.enable_logging)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        app.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create main window
        window = MainWindow(
            desired_width=args.width,
            url=args.url
        )
        
        # Show if starting in docked mode (undocked mode handles its own show)
        if window.is_docked:
            window.show()
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to start ChatGPT Sidebar:\n{e}"
        )
        sys.exit(1)
    
    # Run application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

