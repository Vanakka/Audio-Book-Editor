"""Left panel: book table with search and filtering."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTableView,
    QPushButton, QLabel, QAbstractItemView, QMenu, QHeaderView,
)
from PySide6.QtCore import (
    Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression,
)

SORT_ROLE = Qt.UserRole + 1
from PySide6.QtGui import QColor, QAction

from core.models import AudioBook

COLUMNS = ["Title", "Author", "Series", "#", "Status"]
COL_TITLE = 0
COL_AUTHOR = 1
COL_SERIES = 2
COL_NUMBER = 3
COL_STATUS = 4


class BookTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._books: list[AudioBook] = []
        self.show_book_number_in_title = True

    def set_books(self, books: list[AudioBook]):
        self.beginResetModel()
        self._books = books
        self.endResetModel()

    def get_book(self, row: int) -> AudioBook | None:
        if 0 <= row < len(self._books):
            return self._books[row]
        return None

    def get_all_books(self) -> list[AudioBook]:
        return self._books

    def rowCount(self, parent=QModelIndex()):
        return len(self._books)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        book = self._books[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == COL_TITLE:
                title = book.display_title
                if self.show_book_number_in_title and book.series_number and book.series:
                    # Avoid duplicating if title already contains "Book N"
                    import re
                    if not re.search(r'Book\s*' + re.escape(book.series_number) + r'\b', title):
                        title = f"{title} (Book {book.series_number})"
                return title
            elif col == COL_AUTHOR:
                return book.author
            elif col == COL_SERIES:
                return book.series
            elif col == COL_NUMBER:
                return book.series_number
            elif col == COL_STATUS:
                if book.is_modified:
                    return "Modified"
                elif book.title:
                    return "OK"
                else:
                    return "No Tags"

        elif role == Qt.ForegroundRole:
            if col == COL_STATUS:
                if book.is_modified:
                    return QColor("#B8860B")  # Dark gold
                elif book.title:
                    return QColor("#2E7D32")  # Dark green
                else:
                    return QColor("#C62828")  # Dark red

        elif role == Qt.ToolTipRole:
            return f"{book.file_path}\nIdentifier: {book.identifier} ({book.identifier_type})"

        elif role == SORT_ROLE:
            if col == COL_NUMBER:
                try:
                    return float(book.series_number) if book.series_number else 99999
                except ValueError:
                    return 99999
            return self.data(index, Qt.DisplayRole)

        return None

    def refresh_row(self, row: int):
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, len(COLUMNS) - 1),
        )


class LibraryPanel(QWidget):
    book_selected = Signal(object)  # AudioBook
    books_selected = Signal(list)  # list[AudioBook] for multi-select
    fetch_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 4, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("Library")
        header.setObjectName("sectionHeader")
        layout.addWidget(header)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search books...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table
        self.model = BookTableModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # Search all columns
        self.proxy_model.setSortRole(SORT_ROLE)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        # Column widths
        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(COL_TITLE, QHeaderView.Interactive)
        header_view.setSectionResizeMode(COL_AUTHOR, QHeaderView.Interactive)
        header_view.setSectionResizeMode(COL_SERIES, QHeaderView.Interactive)
        header_view.setSectionResizeMode(COL_NUMBER, QHeaderView.Interactive)
        header_view.setSectionResizeMode(COL_STATUS, QHeaderView.Interactive)

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        # Default sort by # column, low to high
        self.table.sortByColumn(COL_NUMBER, Qt.AscendingOrder)
        layout.addWidget(self.table)

        # Info bar
        self.info_label = QLabel("No books loaded")
        self.info_label.setStyleSheet("font-size: 11px; color: palette(dark);")
        layout.addWidget(self.info_label)

    def set_books(self, books: list[AudioBook]):
        self.model.set_books(books)
        self._update_column_widths()
        self._update_info()

    def _update_column_widths(self):
        self.table.resizeColumnsToContents()
        # Ensure minimum widths
        if self.table.columnWidth(COL_AUTHOR) < 80:
            self.table.setColumnWidth(COL_AUTHOR, 80)
        self.table.setColumnWidth(COL_SERIES, 65)
        self.table.setColumnWidth(COL_NUMBER, 35)
        self.table.setColumnWidth(COL_STATUS, 55)

    def _update_info(self):
        total = self.model.rowCount()
        modified = sum(1 for b in self.model.get_all_books() if b.is_modified)
        shown = self.proxy_model.rowCount()
        parts = [f"{total} books"]
        if shown != total:
            parts.append(f"{shown} shown")
        if modified:
            parts.append(f"{modified} modified")
        self.info_label.setText(" | ".join(parts))

    def _on_search(self, text: str):
        self.proxy_model.setFilterFixedString(text)
        self._update_info()

    def _on_selection_changed(self, selected, deselected):
        indexes = self.table.selectionModel().selectedRows()
        if len(indexes) == 1:
            source_idx = self.proxy_model.mapToSource(indexes[0])
            book = self.model.get_book(source_idx.row())
            if book:
                self.book_selected.emit(book)
        elif len(indexes) > 1:
            books = []
            for idx in indexes:
                source_idx = self.proxy_model.mapToSource(idx)
                book = self.model.get_book(source_idx.row())
                if book:
                    books.append(book)
            self.books_selected.emit(books)

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        fetch_action = QAction("Fetch Metadata", self)
        open_folder_action = QAction("Open Folder", self)
        menu.addAction(fetch_action)
        menu.addAction(open_folder_action)

        fetch_action.triggered.connect(lambda: self._context_fetch())
        open_folder_action.triggered.connect(lambda: self._context_open_folder())

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _context_fetch(self):
        books = self.get_selected_books()
        if books:
            self.fetch_requested.emit(books)

    def _context_open_folder(self):
        import subprocess
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            source_idx = self.proxy_model.mapToSource(indexes[0])
            book = self.model.get_book(source_idx.row())
            if book:
                subprocess.Popen(["explorer", book.folder_path])

    def get_selected_books(self) -> list[AudioBook]:
        books = []
        for idx in self.table.selectionModel().selectedRows():
            source_idx = self.proxy_model.mapToSource(idx)
            book = self.model.get_book(source_idx.row())
            if book:
                books.append(book)
        return books

    def refresh_current(self):
        """Refresh the display for the currently selected book."""
        for idx in self.table.selectionModel().selectedRows():
            source_idx = self.proxy_model.mapToSource(idx)
            self.model.refresh_row(source_idx.row())
        self._update_info()
