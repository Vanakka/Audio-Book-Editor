"""AudioBook Manager - Entry point."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.config import Config
from core.logging_config import setup_logging
from core.media_tools import auto_detect_tool_paths, set_tool_paths
from ui.main_window import MainWindow


def _configure_media_tools(config: Config) -> None:
    ffprobe_path = config.get("ffprobe_path", "")
    ffmpeg_path = config.get("ffmpeg_path", "")
    if not ffprobe_path or not ffmpeg_path:
        detected = auto_detect_tool_paths()
        if not ffprobe_path and detected.get("ffprobe_path"):
            config.set("ffprobe_path", detected["ffprobe_path"])
            ffprobe_path = detected["ffprobe_path"]
        if not ffmpeg_path and detected.get("ffmpeg_path"):
            config.set("ffmpeg_path", detected["ffmpeg_path"])
            ffmpeg_path = detected["ffmpeg_path"]
        if detected:
            config.save()
    set_tool_paths(ffprobe_path, ffmpeg_path)


def main():
    setup_logging()
    config = Config()
    _configure_media_tools(config)
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AudioBook Manager")
    app.setOrganizationName("ClaudeBookTool")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
