"""Application settings dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QDoubleSpinBox,
    QFileDialog, QGroupBox, QComboBox,
)
from PySide6.QtCore import Qt

from core.config import Config


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Paths group
        paths_group = QGroupBox("Paths")
        paths_layout = QFormLayout()

        # Default folder
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        folder_browse = QPushButton("Browse")
        folder_browse.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(folder_browse)
        paths_layout.addRow("Default Folder:", folder_layout)

        # Libation export
        libation_layout = QHBoxLayout()
        self.libation_edit = QLineEdit()
        libation_browse = QPushButton("Browse")
        libation_browse.clicked.connect(self._browse_libation)
        libation_layout.addWidget(self.libation_edit, 1)
        libation_layout.addWidget(libation_browse)
        paths_layout.addRow("Libation Export:", libation_layout)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        chapter_group = QGroupBox("Chapter tools")
        chapter_layout = QFormLayout()

        ffprobe_row = QHBoxLayout()
        self.ffprobe_edit = QLineEdit()
        self.ffprobe_edit.setPlaceholderText("Auto-detect from PATH or WinGet FFmpeg")
        ffprobe_browse = QPushButton("Browse")
        ffprobe_browse.clicked.connect(lambda: self._browse_tool(self.ffprobe_edit))
        ffprobe_row.addWidget(self.ffprobe_edit, 1)
        ffprobe_row.addWidget(ffprobe_browse)
        chapter_layout.addRow("ffprobe:", ffprobe_row)

        ffmpeg_row = QHBoxLayout()
        self.ffmpeg_edit = QLineEdit()
        self.ffmpeg_edit.setPlaceholderText("Auto-detect from PATH or WinGet FFmpeg")
        ffmpeg_browse = QPushButton("Browse")
        ffmpeg_browse.clicked.connect(lambda: self._browse_tool(self.ffmpeg_edit))
        ffmpeg_row.addWidget(self.ffmpeg_edit, 1)
        ffmpeg_row.addWidget(ffmpeg_browse)
        chapter_layout.addRow("ffmpeg:", ffmpeg_row)

        chapter_layout.addRow("", QLabel(
            "Required for the Chapters tab. Audiobook Shelf bundles these tools; "
            "this app uses your local FFmpeg install."
        ))
        chapter_group.setLayout(chapter_layout)
        layout.addWidget(chapter_group)

        # Scrapers group
        scrapers_group = QGroupBox("Metadata Sources")
        scrapers_layout = QVBoxLayout()

        self.cb_libation = QCheckBox("Libation Export (local, fastest)")
        self.cb_audible_api = QCheckBox("Audible API (recommended)")
        self.cb_audible = QCheckBox("Audible (web scraping - often blocked)")
        self.cb_google = QCheckBox("Google Books API")
        self.cb_openlibrary = QCheckBox("OpenLibrary API")
        self.cb_goodreads = QCheckBox("Goodreads (web scraping)")

        scrapers_layout.addWidget(self.cb_libation)
        scrapers_layout.addWidget(self.cb_audible_api)
        scrapers_layout.addWidget(self.cb_audible)
        scrapers_layout.addWidget(self.cb_google)
        scrapers_layout.addWidget(self.cb_openlibrary)
        scrapers_layout.addWidget(self.cb_goodreads)

        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Scraping delay (seconds):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.5, 10.0)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setDecimals(1)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        scrapers_layout.addLayout(delay_layout)

        scrapers_group.setLayout(scrapers_layout)
        layout.addWidget(scrapers_group)

        # Display group
        display_group = QGroupBox("Display")
        display_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Parchment"])
        display_layout.addRow("Theme:", self.theme_combo)

        self.cb_book_number_in_title = QCheckBox(
            "Show book number in title (e.g. \"The Healer's Way (Book 4)\")"
        )
        display_layout.addRow("", self.cb_book_number_in_title)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Rename group
        rename_group = QGroupBox("Renaming")
        rename_layout = QFormLayout()

        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText("{series}, Book {number}")
        rename_layout.addRow("Folder Template:", self.template_edit)

        self.cb_rename_file = QCheckBox("Rename file on save")
        rename_layout.addRow("", self.cb_rename_file)

        self.file_template_edit = QLineEdit()
        self.file_template_edit.setPlaceholderText("{series}, Book {number} [{identifier}]")
        rename_layout.addRow("File Template:", self.file_template_edit)

        rename_layout.addRow("", QLabel(
            "Available: {title} {author} {narrator} {series} {number} {year} {identifier}"
        ))
        rename_group.setLayout(rename_layout)
        layout.addWidget(rename_group)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        self.folder_edit.setText(self.config.get("last_root_folder", ""))
        self.libation_edit.setText(self.config.get("libation_export_path", ""))
        self.ffprobe_edit.setText(self.config.get("ffprobe_path", ""))
        self.ffmpeg_edit.setText(self.config.get("ffmpeg_path", ""))
        self.template_edit.setText(self.config.get("rename_template", "{series}, Book {number}"))
        self.delay_spin.setValue(self.config.get("scraping_delay", 1.5))

        scrapers = self.config.get("scrapers_enabled", {})
        self.cb_libation.setChecked(scrapers.get("libation", True))
        self.cb_audible_api.setChecked(scrapers.get("audible_api", True))
        self.cb_audible.setChecked(scrapers.get("audible", True))
        self.cb_google.setChecked(scrapers.get("google_books", True))
        self.cb_openlibrary.setChecked(scrapers.get("openlibrary", True))
        self.cb_goodreads.setChecked(scrapers.get("goodreads", True))

        theme = self.config.get("theme", "Parchment")
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        self.cb_book_number_in_title.setChecked(self.config.get("show_book_number_in_title", True))

        self.cb_rename_file.setChecked(self.config.get("rename_file_on_save", False))
        self.file_template_edit.setText(self.config.get("file_rename_template", "{series}, Book {number} [{identifier}]"))

    def _on_save(self):
        self.config.set("last_root_folder", self.folder_edit.text().strip())
        self.config.set("libation_export_path", self.libation_edit.text().strip())
        self.config.set("ffprobe_path", self.ffprobe_edit.text().strip())
        self.config.set("ffmpeg_path", self.ffmpeg_edit.text().strip())
        self.config.set("rename_template", self.template_edit.text().strip())
        self.config.set("scraping_delay", self.delay_spin.value())
        self.config.set("scrapers_enabled", {
            "libation": self.cb_libation.isChecked(),
            "audible_api": self.cb_audible_api.isChecked(),
            "audible": self.cb_audible.isChecked(),
            "google_books": self.cb_google.isChecked(),
            "openlibrary": self.cb_openlibrary.isChecked(),
            "goodreads": self.cb_goodreads.isChecked(),
        })
        self.config.set("theme", self.theme_combo.currentText())
        self.config.set("show_book_number_in_title", self.cb_book_number_in_title.isChecked())
        self.config.set("rename_file_on_save", self.cb_rename_file.isChecked())
        self.config.set("file_rename_template", self.file_template_edit.text().strip())
        self.config.save()
        self.accept()

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Audio Books Folder")
        if path:
            self.folder_edit.setText(path)

    def _browse_libation(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Libation Export", "", "Excel Files (*.xlsx)"
        )
        if path:
            self.libation_edit.setText(path)

    def _browse_tool(self, target: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*)"
        )
        if path:
            target.setText(path)
