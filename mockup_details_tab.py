"""Mockup of the Details tab layout with parchment styling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QPlainTextEdit, QWidget, QGroupBox,
    QFormLayout, QScrollArea, QFrame, QTabWidget,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPalette, QBrush
import requests

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
PAPER_PATH = os.path.join(RES, "paper_bg.jpg")

GROUP_STYLE = """
    QGroupBox {
        border: 1px solid #8B6538; border-radius: 8px;
        margin-top: 10px; padding: 6px 8px 6px 8px; font-weight: 700; color: #3B2010;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #6B4520; }
"""


class MockupDetailsTab(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioBook Manager - Mockup")
        self.setMinimumSize(900, 750)

        if os.path.exists(PAPER_PATH):
            palette = self.palette()
            palette.setBrush(QPalette.Window, QBrush(QPixmap(PAPER_PATH)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        self._setup_ui()

    def _make_edit(self, text, max_width=None):
        edit = QLineEdit(text)
        if max_width:
            edit.setMaximumWidth(max_width)
        return edit

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Tab widget
        tabs = QTabWidget()

        # ===== DETAILS TAB =====
        details_widget = QWidget()
        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.NoFrame)

        details_content = QWidget()
        details_layout = QVBoxLayout(details_content)
        details_layout.setSpacing(12)
        details_layout.setContentsMargins(12, 12, 12, 12)

        # --- Book Info group ---
        info_group = QGroupBox("Book Information")
        info_group.setStyleSheet(GROUP_STYLE)
        info_form = QFormLayout()
        info_form.setSpacing(10)
        info_form.setLabelAlignment(Qt.AlignRight)
        info_form.setContentsMargins(12, 8, 12, 8)

        fields = {
            "Title": "Nova Terra: Titan and Greymane",
            "Author": "Seth Ring",
            "Narrator": "Eric Jason Martin",
            "Series": "Titan",
            "Book #": "1-2",
            "Subtitle": "The Titan Series, Books 1-2",
            "Publisher": "Podium Audio",
        }
        for label, value in fields.items():
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #3B2010;")
            edit = QLineEdit(value)
            info_form.addRow(lbl, edit)

        info_group.setLayout(info_form)
        details_layout.addWidget(info_group)

        # --- Additional Info group ---
        extra_group = QGroupBox("Additional Information")
        extra_group.setStyleSheet(GROUP_STYLE)
        extra_form = QVBoxLayout()
        extra_form.setSpacing(8)
        extra_form.setContentsMargins(12, 8, 12, 8)

        extra_fields = QFormLayout()
        extra_fields.setSpacing(10)
        extra_fields.setLabelAlignment(Qt.AlignRight)
        extra_fields.setContentsMargins(0, 0, 0, 0)

        def make_label(text):
            l = QLabel(text)
            l.setStyleSheet("font-weight: 700; font-size: 13px; color: #3B2010;")
            return l

        # Year + Language on one line
        year_lang_row = QHBoxLayout()
        year_lang_row.setSpacing(8)
        year_edit = QLineEdit("2021")
        year_edit.setMaximumWidth(100)
        year_lang_row.addWidget(year_edit)
        year_lang_row.addWidget(make_label("Language"))
        lang_edit = QLineEdit("English")
        lang_edit.setMaximumWidth(150)
        year_lang_row.addWidget(lang_edit)
        year_lang_row.addStretch()
        extra_fields.addRow(make_label("Year"), year_lang_row)

        # ASIN + Search + CDEK on one line
        asin_row = QHBoxLayout()
        asin_row.setSpacing(8)
        asin_edit = QLineEdit("1774246910")
        asin_edit.setMaximumWidth(150)
        asin_row.addWidget(asin_edit)
        search_btn = QPushButton("Search")
        search_btn.setObjectName("primaryButton")
        search_btn.setFixedHeight(28)
        search_btn.setMinimumWidth(70)
        asin_row.addWidget(search_btn)
        asin_row.addWidget(make_label("CDEK"))
        cdek_edit = QLineEdit("1774246910")
        cdek_edit.setMaximumWidth(150)
        asin_row.addWidget(cdek_edit)
        asin_row.addStretch()
        extra_fields.addRow(make_label("ASIN"), asin_row)

        # Genre row
        extra_fields.addRow(make_label("Genre"), QLineEdit("Audiobook"))

        extra_form.addLayout(extra_fields)
        extra_group.setLayout(extra_form)
        details_layout.addWidget(extra_group)

        # --- Description group ---
        desc_group = QGroupBox("Description")
        desc_group.setStyleSheet(GROUP_STYLE)
        desc_layout = QVBoxLayout()
        desc_layout.setContentsMargins(12, 8, 12, 8)

        desc_edit = QPlainTextEdit()
        desc_edit.setPlainText(
            "Contains books one and two of the The Titan series, a litRPG gamelit adventure. "
            "Nova Terra: Titan - Thorn had been in virtual reality his whole life. "
            "Born and raised in a shark tank full of other children where your teeth and "
            "claws were all you could count on, he learned fast, ate well, and grew up to "
            "be a monster of a man..."
        )
        desc_edit.setMinimumHeight(120)
        desc_layout.addWidget(desc_edit)
        desc_group.setLayout(desc_layout)
        details_layout.addWidget(desc_group)

        details_layout.addStretch()
        details_scroll.setWidget(details_content)

        tab_layout = QVBoxLayout(details_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(details_scroll)

        tabs.addTab(details_widget, "Details")
        tabs.addTab(QWidget(), "Cover")
        tabs.addTab(QWidget(), "Files")
        tabs.addTab(QWidget(), "Chapters")

        layout.addWidget(tabs)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        fetch_btn = QPushButton("Fetch Metadata")
        fetch_btn.setObjectName("primaryButton")
        save_btn = QPushButton("Save Tags")
        undo_btn = QPushButton("Undo Changes")

        btn_layout.addWidget(fetch_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(undo_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    paper_url = PAPER_PATH.replace("\\", "/")
    bg = f"url({paper_url})"
    app.setStyleSheet(
        f"QDialog {{ background-image: {bg}; color: #3B2010; }}"
        f" QWidget {{ color: #3B2010; font-family: 'Segoe UI'; font-size: 13px; }}"
        f" QTabWidget::pane {{ background-image: {bg}; border: 1px solid #8B6538; border-radius: 6px; }}"
        f" QScrollArea {{ background-image: {bg}; border: none; }}"
        f" QScrollArea > QWidget > QWidget {{ background-image: {bg}; }}"
        f" QGroupBox {{ background-image: {bg}; }}"
        " QTabBar::tab { background-color: #C4B08A; color: #3B2010; border: 1px solid #8B6538;"
        "   padding: 8px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }"
        " QTabBar::tab:selected { background-color: #D4C4A0; color: #6B4520; border-bottom-color: #D4C4A0; }"
        " QTabBar::tab:hover:!selected { background-color: #B8A078; }"
        " QPushButton { background-color: #B8A078; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 16px; font-weight: 600; }"
        " QPushButton:hover { background-color: #A8906A; }"
        " QPushButton#primaryButton { background-color: #6B4520; color: #F5E6D0; border: none; }"
        " QPushButton#primaryButton:hover { background-color: #8B5A3C; }"
        " QLineEdit { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 10px; }"
        " QLineEdit:focus { border-color: #6B4520; border-width: 2px; }"
        " QPlainTextEdit { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px; }"
        " QPlainTextEdit:focus { border-color: #6B4520; border-width: 2px; }"
        " QScrollBar:vertical { background-color: transparent; width: 12px; }"
        " QScrollBar::handle:vertical { background-color: #8B6538; border: 1px solid #6B4520; border-radius: 5px; min-height: 40px; }"
        " QScrollBar::handle:vertical:hover { background-color: #D4A76A; }"
        " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        " QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
    )
    dlg = MockupDetailsTab()
    dlg.show()
    sys.exit(app.exec())
