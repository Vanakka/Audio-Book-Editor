"""Mockup of the Cover tab layout with real thumbnails."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QWidget, QGroupBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPalette, QBrush, QIcon
import requests

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
PAPER_PATH = os.path.join(RES, "paper_bg.jpg")


class MockupCoverTab(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cover Tab - Mockup")
        self.setMinimumSize(800, 700)

        if os.path.exists(PAPER_PATH):
            palette = self.palette()
            palette.setBrush(QPalette.Window, QBrush(QPixmap(PAPER_PATH)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        group_style = """
            QGroupBox {
                border: 1px solid #8B6538; border-radius: 8px;
                margin-top: 12px; padding-top: 16px; font-weight: 700; color: #3B2010;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #6B4520; }
        """

        # === Current Cover group ===
        cover_group = QGroupBox("Current Cover")
        cover_group.setStyleSheet(group_style)
        cover_group_layout = QHBoxLayout()
        cover_group_layout.setSpacing(16)

        # Cover image - load a real one
        cover_label = QLabel()
        cover_label.setFixedSize(250, 250)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet("""
            QLabel {
                background-color: #C4B08A; border-radius: 8px;
                border: 2px solid #8B6538; color: #6B4520;
            }
        """)

        # Try to load a real cover
        try:
            resp = requests.get(
                "https://api.audible.com/1.0/catalog/products/1774246910",
                params={"response_groups": "media"},
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            images = resp.json().get("product", {}).get("product_images", {})
            img_url = images.get("500", "")
            if img_url:
                img_resp = requests.get(img_url, timeout=10)
                px = QPixmap()
                px.loadFromData(img_resp.content)
                if not px.isNull():
                    scaled = px.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    cover_label.setPixmap(scaled)
        except Exception:
            cover_label.setText("No Cover")

        cover_group_layout.addWidget(cover_label, 0, Qt.AlignTop)

        # Actions
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.setAlignment(Qt.AlignTop)

        dim_label = QLabel("500x500px")
        dim_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #3B2010;")
        actions_layout.addWidget(dim_label)

        upload_btn = QPushButton("Upload from File")
        actions_layout.addWidget(upload_btn)

        url_layout = QHBoxLayout()
        url_layout.setSpacing(8)
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("Paste image URL here...")
        url_layout.addWidget(url_edit, 1)
        download_btn = QPushButton("Download")
        download_btn.setObjectName("primaryButton")
        url_layout.addWidget(download_btn)
        actions_layout.addLayout(url_layout)

        actions_layout.addStretch()
        cover_group_layout.addLayout(actions_layout, 1)
        cover_group.setLayout(cover_group_layout)
        layout.addWidget(cover_group)

        # === Search Cover Art group ===
        search_group = QGroupBox("Search Cover Art")
        search_group.setStyleSheet(group_style)
        search_group_layout = QVBoxLayout()
        search_group_layout.setSpacing(10)

        # Search fields
        fields_layout = QHBoxLayout()
        fields_layout.setSpacing(8)

        fields_layout.addWidget(QLabel("Provider:"))
        provider_combo = QComboBox()
        provider_combo.addItems(["Audible", "Goodreads"])
        provider_combo.setMinimumWidth(120)
        fields_layout.addWidget(provider_combo)

        fields_layout.addWidget(QLabel("Title or ASIN:"))
        title_edit = QLineEdit()
        title_edit.setText("Nova Terra")
        fields_layout.addWidget(title_edit, 1)

        fields_layout.addWidget(QLabel("Author:"))
        author_edit = QLineEdit()
        author_edit.setText("Seth Ring")
        fields_layout.addWidget(author_edit, 1)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("primaryButton")
        fields_layout.addWidget(search_btn)
        search_group_layout.addLayout(fields_layout)

        # Results with real thumbnails
        results = QListWidget()
        results.setIconSize(QSize(80, 80))
        results.setMinimumHeight(220)

        try:
            resp = requests.get(
                "https://api.audible.com/1.0/catalog/products",
                params={
                    "title": "Nova Terra",
                    "author": "Seth Ring",
                    "response_groups": "product_desc,media",
                    "num_results": 5,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])

            for p in products:
                title = p.get("title", "?")
                asin = p.get("asin", "")
                images = p.get("product_images", {})
                thumb_url = images.get("500") or images.get("252", "")

                item = QListWidgetItem(f"{title} ({asin})")

                if thumb_url:
                    try:
                        img_resp = requests.get(thumb_url, timeout=8)
                        img_resp.raise_for_status()
                        px = QPixmap()
                        px.loadFromData(img_resp.content)
                        if not px.isNull():
                            scaled = px.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            item.setIcon(QIcon(scaled))
                    except Exception:
                        pass

                results.addItem(item)
        except Exception as e:
            results.addItem(f"Error: {e}")

        search_group_layout.addWidget(results)

        hint = QLabel("Double-click a result to download and embed the cover art")
        hint.setStyleSheet("font-size: 11px; font-style: italic; color: #6B4520;")
        search_group_layout.addWidget(hint)

        search_group.setLayout(search_group_layout)
        layout.addWidget(search_group)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Apply parchment-like styling
    app.setStyleSheet("""
        QGroupBox { background-color: transparent; }
        QWidget { background-color: transparent; color: #3B2010; font-family: "Segoe UI"; font-size: 13px; }
        QPushButton { background-color: #B8A078; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 8px 16px; font-weight: 600; }
        QPushButton:hover { background-color: #A8906A; }
        QPushButton#primaryButton { background-color: #6B4520; color: #F5E6D0; border: none; }
        QPushButton#primaryButton:hover { background-color: #8B5A3C; }
        QLineEdit { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 10px; }
        QComboBox { background-color: #E8D8B8; color: #2E1508; border: 1px solid #8B6538; border-radius: 6px; padding: 6px 10px; }
        QListWidget { background-color: #E8D8B8; border: 1px solid #8B6538; border-radius: 6px; }
        QListWidget::item { padding: 6px; border-bottom: 1px solid #C4A878; }
        QListWidget::item:selected { background-color: #C49A6C; }
    """)
    dlg = MockupCoverTab()
    dlg.show()
    sys.exit(app.exec())
