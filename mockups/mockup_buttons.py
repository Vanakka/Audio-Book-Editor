"""Button style comparison mockup."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor, QPen, QLinearGradient, QPainterPath

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
PAPER_PATH = os.path.join(RES, "paper_bg.jpg")


class PaperButton(QPushButton):
    """Button with paper texture and bronze frame."""
    _paper = None

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setMinimumWidth(180)
        if PaperButton._paper is None and os.path.exists(PAPER_PATH):
            PaperButton._paper = QPixmap(PAPER_PATH)
        self.setStyleSheet("background: transparent; border: none; color: #3B2010; font-size: 14px; font-weight: 700;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)
        radius = 10
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
        painter.setClipPath(path)
        if PaperButton._paper:
            scaled = PaperButton._paper.scaled(rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(rect, scaled)
        else:
            painter.fillRect(rect, QColor("#D4C4A0"))
        painter.setClipping(False)
        # Bronze border
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0.0, QColor("#D4A76A"))
        gradient.setColorAt(0.3, QColor("#8B6538"))
        gradient.setColorAt(0.5, QColor("#DDB880"))
        gradient.setColorAt(0.7, QColor("#7A5528"))
        gradient.setColorAt(1.0, QColor("#6B4520"))
        outer = self.rect().adjusted(1, 1, -1, -1)
        outer_path = QPainterPath()
        outer_path.addRoundedRect(outer.x(), outer.y(), outer.width(), outer.height(), radius + 2, radius + 2)
        border_path = outer_path - path
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(border_path)
        # Text
        painter.setPen(QColor("#3B2010"))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())
        painter.end()


class LeatherButton(QPushButton):
    """Dark embossed leather button."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setMinimumWidth(180)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 10
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
        # Dark leather fill
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0.0, QColor("#5C3820"))
        gradient.setColorAt(0.3, QColor("#3A2010"))
        gradient.setColorAt(0.7, QColor("#2E1808"))
        gradient.setColorAt(1.0, QColor("#1C0E04"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
        # Inner highlight (top edge)
        inner_top = QPainterPath()
        inner_rect = rect.adjusted(2, 2, -2, int(-rect.height() * 0.6))
        inner_top.addRoundedRect(inner_rect.x(), inner_rect.y(), inner_rect.width(), inner_rect.height(), radius - 2, radius - 2)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawPath(inner_top)
        # Outer dark edge (pressed in)
        pen = QPen(QColor(10, 5, 2, 200), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        # Inner edge highlight
        pen = QPen(QColor(120, 80, 40, 60), 0.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius - 2, radius - 2)
        # Text
        painter.setPen(QColor("#D4A76A"))
        font = self.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())
        painter.end()


class GoldButton(QPushButton):
    """Gold plaque button."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setMinimumWidth(180)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 10
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
        # Gold gradient fill
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0.0, QColor("#F0D080"))
        gradient.setColorAt(0.15, QColor("#E8C468"))
        gradient.setColorAt(0.35, QColor("#C8A048"))
        gradient.setColorAt(0.5, QColor("#F0D888"))
        gradient.setColorAt(0.65, QColor("#C8A048"))
        gradient.setColorAt(0.85, QColor("#A88030"))
        gradient.setColorAt(1.0, QColor("#886820"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
        # Dark outer edge
        pen = QPen(QColor(60, 40, 10, 200), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        # Inner bright edge
        pen = QPen(QColor(255, 240, 180, 100), 0.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius - 2, radius - 2)
        # Text (engraved look - dark with slight light offset)
        font = self.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        # Light shadow
        painter.setPen(QColor(255, 240, 200, 80))
        painter.drawText(rect.adjusted(1, 1, 1, 1), Qt.AlignCenter, self.text())
        # Dark text
        painter.setPen(QColor("#3A2008"))
        painter.drawText(rect, Qt.AlignCenter, self.text())
        painter.end()


class ButtonMockup(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Button Styles Comparison")
        self.setMinimumSize(700, 300)

        if os.path.exists(PAPER_PATH):
            palette = self.palette()
            pixmap = QPixmap(PAPER_PATH)
            palette.setBrush(QPalette.Window, QBrush(pixmap))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)

        # Option 1: Paper + Bronze
        row1 = QHBoxLayout()
        lbl1 = QLabel("1. Paper + Bronze")
        lbl1.setStyleSheet("font-size: 16px; font-weight: 700; color: #3B2010;")
        row1.addWidget(lbl1)
        row1.addStretch()
        row1.addWidget(PaperButton("Apply Selected"))
        row1.addWidget(PaperButton("Cancel"))
        layout.addLayout(row1)

        # Option 2: Embossed Leather
        row2 = QHBoxLayout()
        lbl2 = QLabel("2. Embossed Leather")
        lbl2.setStyleSheet("font-size: 16px; font-weight: 700; color: #3B2010;")
        row2.addWidget(lbl2)
        row2.addStretch()
        row2.addWidget(LeatherButton("Apply Selected"))
        row2.addWidget(LeatherButton("Cancel"))
        layout.addLayout(row2)

        # Option 3: Gold Plaque
        row3 = QHBoxLayout()
        lbl3 = QLabel("3. Gold Plaque")
        lbl3.setStyleSheet("font-size: 16px; font-weight: 700; color: #3B2010;")
        row3.addWidget(lbl3)
        row3.addStretch()
        row3.addWidget(GoldButton("Apply Selected"))
        row3.addWidget(GoldButton("Cancel"))
        layout.addLayout(row3)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = ButtonMockup()
    dlg.show()
    sys.exit(app.exec())
