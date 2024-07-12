# This file is part of StickerNest.
# Copyright (C) 2024 Eliza

# StickerNest is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# StickerNest is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QScrollArea,
    QLayout,
)


class AmountEditor(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.amount = 1

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        self.left_button = QToolButton(self)
        self.left_button.setArrowType(Qt.LeftArrow)
        self.left_button.clicked.connect(self.down_amount)
        layout.addWidget(self.left_button)

        self.amount_edit = QLineEdit(self)
        self.amount_edit.setValidator(QIntValidator(0, 99, self.amount_edit))
        self.amount_edit.setText("1")
        self.amount_edit.editingFinished.connect(self.update_amount)
        self.amount_edit.setFixedWidth(self.amount_edit.height())
        layout.addWidget(self.amount_edit)

        self.right_button = QToolButton(self)
        self.right_button.setArrowType(Qt.RightArrow)
        self.right_button.clicked.connect(self.up_amount)
        layout.addWidget(self.right_button)

        self.setLayout(layout)

    def update_amount(self):
        self.amount = int(self.amount_edit.text())

    def up_amount(self):
        self.amount = min(99, self.amount + 1)
        self.amount_edit.setText(str(self.amount))

    def down_amount(self):
        self.amount = max(0, self.amount - 1)
        self.amount_edit.setText(str(self.amount))


class AmountBar(QWidget):
    def __init__(self, file_path: str,
                 image_name: str, parent: QWidget) -> None:
        super().__init__(parent)

        self.file_path = file_path
        self.image_name = image_name

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.img_label = QLabel(self)
        self.img_label.setFixedWidth(50)
        self.img_label.setFixedHeight(50)
        pixmap = QPixmap(self.file_path)
        pixmap = pixmap.scaled(
            50, 50,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.img_label.setPixmap(pixmap)
        layout.addWidget(self.img_label)

        self.name_label = QLabel(self)
        layout.addWidget(self.name_label)

        self.amount_edit = AmountEditor(self)
        layout.addWidget(self.amount_edit)

        space = 120
        metrics = self.name_label.fontMetrics()
        elided = metrics.elidedText(self.image_name, Qt.ElideRight, space)
        self.name_label.setText(elided)

        self.setLayout(layout)

    @property
    def amount(self) -> int:
        return self.amount_edit.amount


class AmountsPage(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._files = []

        page_layout = QVBoxLayout()
        # page_layout.setSizeConstraint(QLayout.SetFixedSize)

        scroll_area = QScrollArea(self)
        scroll_area.horizontalScrollBar().setEnabled(False)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setWidgetResizable(True)
        # scroll_width = scroll_area.verticalScrollBar().sizeHint().width()

        page_layout.addWidget(scroll_area)

        self.list_box = QWidget(scroll_area)
        self.list_layout = QVBoxLayout()
        self.list_layout.setContentsMargins(5, 0, 0, 0)
        self.list_box.setLayout(self.list_layout)

        scroll_area.setWidget(self.list_box)

        self.back_button = QPushButton("Back", self)
        page_layout.addWidget(self.back_button)

        self.setLayout(page_layout)

    def _refresh_list(self):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().deleteLater()

        for file in self.files:
            amount_editor = AmountBar(
                file,
                os.path.basename(file),
                self.list_box
            )
            self.list_layout.addWidget(amount_editor)

    @property
    def files(self) -> list[str]:
        return self._files

    @files.setter
    def files(self, value) -> None:
        self._files = value
        self._refresh_list()

    @property
    def amounts(self) -> list[dict]:
        selected_amounts = []

        for i in range(self.list_layout.count()):
            amount_bar: AmountBar = self.list_layout.itemAt(i).widget()
            selected_amounts.append(
                {"path": amount_bar.file_path, "amount": amount_bar.amount}
            )

        return selected_amounts
