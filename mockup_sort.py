"""Mockup of Sort Library to Disk dialog."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QWidget, QGroupBox, QStackedWidget,
    QFileDialog,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPalette, QBrush, QColor

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
PAPER_PATH = os.path.join(RES, "paper_bg.jpg")

# Sample data
SERIES_DATA = [
    ("A Song of Ice and Fire", 5, "Complete"),
    ("Dark Matter Ascension", 2, "Ongoing"),
    ("Emerilia", 11, "Complete"),
    ("Healer's Way", 13, "Ongoing"),
    ("Nova Terra", 9, "Complete"),
    ("The Dark Healer", 9, "Ongoing"),
    ("The Infinite World", 3, "Complete"),
    ("Dungeon Crawler Carl", 6, "Ongoing"),
]

STANDALONE_DATA = [
    ("12 Rules for Life", "Jordan B. Peterson", "Psychology, Ethics"),
    ("A Han Yang Omnibus", "Han Yang", "Action & Adventure"),
    ("Project Hail Mary", "Andy Weir", "Science Fiction"),
]

GROUP_STYLE = """
    QGroupBox {
        border: 1px solid #8B6538; border-radius: 8px;
        margin-top: 10px; padding: 6px 8px 6px 8px;
        font-weight: 700; color: #3B2010;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 12px;
        padding: 0 6px; color: #6B4520;
    }
"""


class MockupSortDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sort Library to Disk")
        self.setMinimumSize(950, 700)

        if os.path.exists(PAPER_PATH):
            palette = self.palette()
            palette.setBrush(QPalette.Window, QBrush(QPixmap(PAPER_PATH)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Sort Library to Disk")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #3B2010;")
        layout.addWidget(title)

        subtitle = QLabel("Organize your audiobooks into series folders automatically")
        subtitle.setStyleSheet("font-size: 12px; color: #6B4520; font-style: italic;")
        layout.addWidget(subtitle)

        # Destination
        dest_group = QGroupBox("Destination")
        dest_group.setStyleSheet(GROUP_STYLE)
        dest_layout = QHBoxLayout()
        dest_layout.setContentsMargins(12, 8, 12, 8)
        dest_layout.addWidget(QLabel("Root Folder:"))
        dest_edit = QLineEdit("D:\\Audio-Books")
        dest_layout.addWidget(dest_edit, 1)
        browse_btn = QPushButton("Browse")
        dest_layout.addWidget(browse_btn)
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)

        # Series table
        series_group = QGroupBox(f"Series ({len(SERIES_DATA)} found)")
        series_group.setStyleSheet(GROUP_STYLE)
        series_layout = QVBoxLayout()
        series_layout.setContentsMargins(12, 8, 12, 8)

        # Bulk actions
        bulk_layout = QHBoxLayout()
        bulk_layout.setSpacing(8)
        set_all_label = QLabel("Set all to:")
        set_all_label.setStyleSheet("font-weight: 600; color: #3B2010;")
        bulk_layout.addWidget(set_all_label)
        for status in ["Ongoing", "Complete", "Skip"]:
            btn = QPushButton(status)
            btn.setFixedHeight(26)
            btn.setStyleSheet("padding: 2px 12px; font-size: 11px;")
            bulk_layout.addWidget(btn)
        bulk_layout.addStretch()
        series_layout.addLayout(bulk_layout)

        series_table = QTableWidget()
        series_table.setColumnCount(4)
        series_table.setHorizontalHeaderLabels(["Series Name", "Books", "Current Folder", "Status"])
        series_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        series_table.verticalHeader().setVisible(False)
        series_table.setRowCount(len(SERIES_DATA))

        header = series_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        series_table.setColumnWidth(3, 110)

        for row, (name, count, status) in enumerate(SERIES_DATA):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            series_table.setItem(row, 0, name_item)

            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            series_table.setItem(row, 1, count_item)

            folder_item = QTableWidgetItem(f"{name} {status}")
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemIsEditable)
            folder_item.setForeground(QColor("#6B4520"))
            series_table.setItem(row, 2, folder_item)

            combo = QComboBox()
            combo.addItems(["Ongoing", "Complete", "Skip"])
            combo.setCurrentText(status)
            series_table.setCellWidget(row, 3, combo)

        series_layout.addWidget(series_table)
        series_group.setLayout(series_layout)
        layout.addWidget(series_group)

        # Standalone books
        standalone_group = QGroupBox(f"Books Without Series ({len(STANDALONE_DATA)})")
        standalone_group.setStyleSheet(GROUP_STYLE)
        standalone_layout = QVBoxLayout()
        standalone_layout.setContentsMargins(12, 8, 12, 8)

        standalone_table = QTableWidget()
        standalone_table.setColumnCount(4)
        standalone_table.setHorizontalHeaderLabels(["Title", "Author", "Genre", "Sort To"])
        standalone_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        standalone_table.verticalHeader().setVisible(False)
        standalone_table.setRowCount(len(STANDALONE_DATA))

        header2 = standalone_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.Stretch)
        header2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for row, (title, author, genre) in enumerate(STANDALONE_DATA):
            title_item = QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            standalone_table.setItem(row, 0, title_item)

            author_item = QTableWidgetItem(author)
            author_item.setFlags(author_item.flags() & ~Qt.ItemIsEditable)
            standalone_table.setItem(row, 1, author_item)

            genre_item = QTableWidgetItem(genre.split(",")[0].strip())
            genre_item.setFlags(genre_item.flags() & ~Qt.ItemIsEditable)
            standalone_table.setItem(row, 2, genre_item)

            combo = QComboBox()
            combo.addItems(["Skip", "Standalone"])
            if genre:
                for g in genre.split(",")[:3]:
                    combo.addItem(f"Genre: {g.strip()}")
            standalone_table.setCellWidget(row, 3, combo)

        standalone_layout.addWidget(standalone_table)
        standalone_group.setLayout(standalone_layout)
        layout.addWidget(standalone_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        preview_btn = QPushButton("Preview Changes")
        preview_btn.setObjectName("primaryButton")

        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        # Stats
        stats = QLabel(f"{sum(c for _, c, _ in SERIES_DATA)} books in series | {len(STANDALONE_DATA)} standalone")
        stats.setStyleSheet("font-size: 11px; color: #6B4520; font-style: italic;")
        btn_layout.addWidget(stats)
        btn_layout.addStretch()

        btn_layout.addWidget(preview_btn)
        layout.addLayout(btn_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    paper_url = PAPER_PATH.replace("\\", "/")
    app.setStyleSheet(
        f"QDialog {{ background-image: url({paper_url}); }}"
        " QWidget { color: #3B2010; font-family: 'Segoe UI'; font-size: 13px; background: transparent; }"
        " QPushButton { background-color: #B8A078; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 16px; font-weight: 600; }"
        " QPushButton:hover { background-color: #A8906A; }"
        " QPushButton#primaryButton { background-color: #6B4520; color: #F5E6D0; border: none; }"
        " QPushButton#primaryButton:hover { background-color: #8B5A3C; }"
        " QLineEdit { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 10px; }"
        " QComboBox { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 4px 8px; }"
        " QTableWidget { background-color: #E8D8B8; border: 1px solid #8B6538; border-radius: 6px; gridline-color: #C4A878; }"
        " QTableWidget::item { padding: 4px 8px; }"
        " QTableWidget::item:selected { background-color: #C49A6C; }"
        " QHeaderView::section { background-color: #C4B08A; color: #3B2010; border: none; border-bottom: 2px solid #8B6538; border-right: 1px solid #C4A878; padding: 6px 8px; font-weight: 700; font-size: 12px; }"
        " QScrollBar:vertical { background-color: transparent; width: 12px; }"
        " QScrollBar::handle:vertical { background-color: #8B6538; border: 1px solid #6B4520; border-radius: 5px; min-height: 40px; }"
        " QScrollBar::handle:vertical:hover { background-color: #D4A76A; }"
        " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        " QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
    )
    dlg = MockupSortDialog()
    dlg.show()
    sys.exit(app.exec())
