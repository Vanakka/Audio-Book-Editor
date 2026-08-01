"""Theme stylesheets for the application."""

import os

from core.app_paths import resource_dir

PAPER_PATH = str(resource_dir() / "paper_bg.jpg").replace("\\", "/")

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}

QMenuBar::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}

QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    spacing: 6px;
    padding: 4px 8px;
}

QToolButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QToolButton:pressed {
    background-color: #585b70;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 28px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton#primaryButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #74c7ec;
}

QPushButton#dangerButton {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
}

QLineEdit, QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #89b4fa;
}

QPlainTextEdit, QTextEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QPlainTextEdit:focus, QTextEdit:focus {
    border-color: #89b4fa;
}

QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    selection-background-color: #45475a;
}

QTableView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
    alternate-background-color: #181825;
}

QTableView::item {
    padding: 4px 8px;
    border: none;
}

QTableView::item:selected {
    background-color: #45475a;
}

QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    border-bottom: 2px solid #313244;
    border-right: 1px solid #313244;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    background-color: #313244;
    color: #cdd6f4;
}

QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    min-width: 30px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QSplitter::handle {
    background-color: #313244;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #89b4fa;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
    padding: 2px 8px;
}

QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}

QLabel {
    color: #a6adc8;
    background-color: transparent;
}

QLabel#fieldLabel {
    font-weight: 600;
    font-size: 12px;
    color: #bac2de;
}

QLabel#modifiedLabel {
    font-weight: 600;
    color: #f9e2af;
}

QLabel#sectionHeader {
    font-size: 15px;
    font-weight: 700;
    color: #cdd6f4;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #89b4fa;
}

QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom-color: #1e1e2e;
}

QTabBar::tab:hover:!selected {
    background-color: #313244;
}

QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
"""

PARCHMENT_THEME = f"""
QMainWindow, QDialog {{
    background-image: url({PAPER_PATH});
    color: #2E1508;
}}

QWidget {{
    background-color: transparent;
    color: #2E1508;
    font-family: "Segoe UI", "Georgia", serif;
    font-size: 13px;
}}

QMenuBar {{
    background-color: #C4B08A;
    color: #2E1508;
    border-bottom: 2px solid #8B6538;
    padding: 2px;
}}

QMenuBar::item:selected {{
    background-color: #A8946E;
    border-radius: 4px;
}}

QMenu {{
    background-color: #D4C4A0;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item:selected {{
    background-color: #C4A878;
    border-radius: 4px;
}}

QToolBar {{
    background-color: #C4B08A;
    border-bottom: 2px solid #8B6538;
    spacing: 6px;
    padding: 4px 8px;
}}

QToolButton {{
    background-color: #B8A078;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}}

QToolButton:hover {{
    background-color: #A8906A;
    border-color: #6B4520;
}}

QToolButton:pressed {{
    background-color: #98804A;
}}

QPushButton {{
    background-color: #B8A078;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 28px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #A8906A;
    border-color: #6B4520;
}}

QPushButton:pressed {{
    background-color: #98804A;
}}

QPushButton#primaryButton {{
    background-color: #6B4520;
    color: #F5E6D0;
    border: none;
    font-weight: 700;
}}

QPushButton#primaryButton:hover {{
    background-color: #8B5A3C;
}}

QPushButton#dangerButton {{
    background-color: #8B3A2A;
    color: #F5E6D0;
    border: none;
}}

QLineEdit, QSpinBox {{
    background-color: #E8D8B8;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
    selection-background-color: #C49A6C;
    selection-color: #2E1508;
}}

QLineEdit:focus, QSpinBox:focus {{
    border-color: #6B4520;
    border-width: 2px;
}}

QPlainTextEdit, QTextEdit {{
    background-color: #E8D8B8;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #C49A6C;
    selection-color: #2E1508;
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: #6B4520;
    border-width: 2px;
}}

QComboBox {{
    background-color: #E8D8B8;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: #6B4520;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: #D4C4A0;
    color: #2E1508;
    border: 1px solid #8B6538;
    selection-background-color: #C49A6C;
}}

QTableView {{
    background-color: #E8D8B8;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    gridline-color: #C4A878;
    selection-background-color: #C49A6C;
    selection-color: #2E1508;
    alternate-background-color: #DED0B0;
}}

QTableView::item {{
    padding: 4px 8px;
    border: none;
}}

QTableView::item:selected {{
    background-color: #C49A6C;
}}

QHeaderView::section {{
    background-color: #C4B08A;
    color: #3B2010;
    border: none;
    border-bottom: 2px solid #8B6538;
    border-right: 1px solid #C4A878;
    padding: 6px 8px;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
}}

QHeaderView::section:hover {{
    background-color: #B8A078;
    color: #2E1508;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 12px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background-color: #8B6538;
    border: 1px solid #6B4520;
    min-height: 40px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #D4A76A;
    border-color: #8B6538;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 12px;
    margin: 2px 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: #8B6538;
    border: 1px solid #6B4520;
    min-width: 40px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #D4A76A;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

QSplitter::handle {{
    background-color: #8B6538;
    width: 2px;
}}

QSplitter::handle:hover {{
    background-color: #D4A76A;
}}

QStatusBar {{
    background-color: #C4B08A;
    color: #3B2010;
    border-top: 2px solid #8B6538;
    font-size: 12px;
    padding: 2px 8px;
}}

QProgressBar {{
    background-color: #C4B08A;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: #6B4520;
    border-radius: 6px;
}}

QLabel {{
    color: #3B2010;
    background-color: transparent;
}}

QLabel#fieldLabel {{
    font-weight: 700;
    font-size: 12px;
    color: #3B2010;
}}

QLabel#modifiedLabel {{
    font-weight: 600;
    color: #8B3A2A;
}}

QLabel#sectionHeader {{
    font-size: 15px;
    font-weight: 700;
    color: #2E1508;
}}

QGroupBox {{
    background: transparent;
    border: none;
    margin-top: 10px;
    padding: 6px 8px 6px 8px;
    font-weight: 600;
    color: #3B2010;
}}

QGroupBox::title {{
    color: transparent;
}}

QCheckBox {{
    spacing: 8px;
    color: #2E1508;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #8B6538;
    border-radius: 4px;
    background-color: #E8D8B8;
}}

QCheckBox::indicator:checked {{
    background-color: #6B4520;
    border-color: #6B4520;
}}

QTabWidget::pane {{
    border: 1px solid #8B6538;
    border-radius: 6px;
    background: transparent;
}}

QTabBar::tab {{
    background-color: #C4B08A;
    color: #3B2010;
    border: 1px solid #8B6538;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background: transparent;
    color: #6B4520;
    border-bottom-color: #D4C4A0;
}}

QTabBar::tab:hover:!selected {{
    background-color: #B8A078;
}}

QToolTip {{
    background-color: #D4C4A0;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 4px;
    padding: 4px 8px;
}}

QDoubleSpinBox {{
    background-color: #E8D8B8;
    color: #2E1508;
    border: 1px solid #8B6538;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}}

QDoubleSpinBox:focus {{
    border-color: #6B4520;
    border-width: 2px;
}}
"""

THEMES = {
    "Dark": DARK_THEME,
    "Parchment": PARCHMENT_THEME,
}
