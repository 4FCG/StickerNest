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

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIntValidator, QIcon, QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QLabel,
    QProgressBar,
    QLineEdit,
    QGroupBox,
    QHBoxLayout,
    QStackedWidget
)
from snest.nest_thread import NestThread
from snest.config import ConfigPage
import os

VALID_TYPES = ["png", "webp", "tiff", "tif", "bmp"]
GITHUB_URL = QUrl("https://github.com/4FCG/StickerNest")


class MainPage(QWidget):
    def __init__(self, parent=None, height=300, width=250) -> None:
        super().__init__(parent)

        self._queue = []

        self.setFixedWidth(width)
        self.setMaximumHeight(height)

        layout = QVBoxLayout()

        # Sticker selection

        input_layout = QHBoxLayout()

        self._select_label = QLabel(self)
        self._select_label.setText("0 images selected")
        input_layout.addWidget(self._select_label)

        self._select_button = QPushButton("Select Images", self)
        self._select_button.clicked.connect(self._select_images)
        input_layout.addWidget(self._select_button)

        self._input_group = QWidget()
        layout.addWidget(self._input_group)
        self._input_group.setLayout(input_layout)

        # Output Selection

        output_label = QLabel(self)
        output_label.setText("Output directory")
        layout.addWidget(output_label)

        self._output_group = QWidget()
        layout.addWidget(self._output_group)

        output_layout = QHBoxLayout()
        self._output_group.setLayout(output_layout)

        self._output_textbox = QLineEdit("", self)
        self._output_textbox.textEdited.connect(self._update_output_path)
        output_layout.addWidget(self._output_textbox)

        self._output_button = QPushButton("Browse", self)
        self._output_button.clicked.connect(self._select_output_dir)
        output_layout.addWidget(self._output_button)

        n_sets_label = QLabel(self)
        n_sets_label.setText("Number of sets")
        layout.addWidget(n_sets_label)
        self.n_sets_box = QLineEdit(self)
        self.n_sets_box.setText("1")
        self.n_sets_box.setValidator(QIntValidator(1, 99))
        self.n_sets_box.setToolTip("Repeats the selected images N times")
        self.n_sets_box.textEdited.connect(self._ready_for_nest)
        layout.addWidget(self.n_sets_box)

        self._nest_button = QPushButton("Nest Stickers", self)
        self._nest_button.setMinimumWidth(120)
        self._nest_button.setEnabled(False)
        layout.addWidget(self._nest_button, alignment=Qt.AlignCenter)

        # Status window

        self._status_box = QGroupBox(self)
        status_layout = QVBoxLayout()
        self._status_box.setLayout(status_layout)
        layout.addWidget(self._status_box)

        self._status_label = QLabel(self)
        self._status_label.setMinimumHeight(80)
        status_layout.addWidget(self._status_label)

        # Progress bar

        progress_layout = QVBoxLayout()
        self._progress_box = QWidget(self)
        self._progress_box.setLayout(progress_layout)
        self._progress_box.setVisible(False)
        status_layout.addWidget(self._progress_box)

        self._progress_label = QLabel(self)
        self._progress_label.setText("")
        progress_layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        button_layout = QHBoxLayout()
        button_box = QWidget(self)
        button_box.setLayout(button_layout)
        layout.addWidget(button_box)

        self.github_button = QPushButton("Github", self)
        button_layout.addWidget(self.github_button)

        self.settings_button = QPushButton("Settings", self)
        button_layout.addWidget(self.settings_button)

        self.setLayout(layout)

        # Set default path
        self.output_path = os.getcwd()

    @property
    def output_path(self):
        return self._output_path

    @output_path.setter
    def output_path(self, value):
        self._output_textbox.setText(value)
        self._output_path = value
        self._ready_for_nest()

    def _update_output_path(self, value):
        self.output_path = value

    # Check for input error before enabling nest button
    def _ready_for_nest(self):
        error = ""

        if not os.path.isdir(self.output_path):
            error += "Output dir is invalid.\n"
        if len(self._queue) <= 0:
            error += "Please select images.\n"
        if not self.n_sets_box.hasAcceptableInput():
            error += "Select a valid number of sets.\n"
        for file in self._queue:
            if file.lower().split(".")[-1] not in VALID_TYPES:
                error += "Please select valid image files (png, webp).\n"
                break

        if error == "":
            self._nest_button.setEnabled(True)
            self._status_label.setVisible(False)
        else:
            self._nest_button.setEnabled(False)
            self._status_label.setText(error)
            self._status_label.setVisible(True)

    def _select_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select images",
            "",
            "Images (*.png *.webp *.tiff *.tif *.bmp);; All Files (*.*)",
        )

        self._select_label.setText(f"{len(file_paths)} images selected")
        self._nest_button.setEnabled(True)
        file_paths = [os.path.abspath(file) for file in file_paths]
        self._queue = file_paths
        self._ready_for_nest()

    def _select_output_dir(self):
        dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            "", QFileDialog.Option.ShowDirsOnly
        )

        self.output_path = os.path.abspath(dir)


class UIWrapper(QMainWindow):
    def __init__(self, application_path,
                 internal_dir, app: QApplication) -> None:
        super().__init__()

        self.app = app

        self.setWindowTitle("Sticker Nest")
        self.setWindowIcon(QIcon(os.path.join(internal_dir, "logo.ico")))
        self.setFixedWidth(300)
        self.setFixedHeight(350)

        # Main page

        self.main_page = MainPage(self, self.height(), self.width())
        self.main_page._nest_button.clicked.connect(self._nest_images)
        self.main_page.settings_button.clicked.connect(self._open_settings)
        self.main_page.github_button.clicked.connect(self._open_github)

        # Config Page

        self.config_page = ConfigPage(
            self, self.height(), self.width(), application_path
        )
        self.config_page.back_button.clicked.connect(self._back_button)

        # Main widget stack

        self.widgets = QStackedWidget(self)
        self.widgets.addWidget(self.main_page)
        self.widgets.addWidget(self.config_page)
        self.widgets.setCurrentWidget(self.main_page)
        self.setCentralWidget(self.widgets)

        # Defaults
        self.main_page._ready_for_nest()

    def _open_settings(self):
        self.widgets.setCurrentWidget(self.config_page)

    def _open_github(self):
        QDesktopServices.openUrl(GITHUB_URL)

    def _back_button(self):
        self.widgets.setCurrentWidget(self.main_page)

    def _nest_images(self):
        self.main_page._select_button.setEnabled(False)
        self.main_page._nest_button.setEnabled(False)
        self.main_page._output_button.setEnabled(False)
        self.main_page._output_textbox.setEnabled(False)
        self.main_page.settings_button.setEnabled(False)
        self.main_page.n_sets_box.setEnabled(False)
        self.main_page._progress_box.setVisible(True)

        self.app.setOverrideCursor(QCursor(Qt.WaitCursor))

        self._nest_thread = NestThread(
            self.main_page._queue,
            self.main_page.output_path,
            int(self.main_page.n_sets_box.text()),
            self.config_page.config,
            parent=self,
        )
        self._nest_thread.completed.connect(self._completed)
        self._nest_thread.update_progress.connect(self._update)
        self._nest_thread.new_loading.connect(self._new_loading)
        self._nest_thread.start()

    def _new_loading(self, args):
        initial, maximum, label = args
        self.main_page._progress_bar.setValue(initial)
        self.main_page._progress_bar.setMaximum(maximum)
        self.main_page._progress_label.setText(label)

    def _update(self, value):
        self.main_page._progress_bar.setValue(value + 1)

    def _completed(self):
        self.main_page._select_button.setEnabled(True)
        self.main_page._select_label.setText("0 images selected")
        self.main_page._queue = []
        self.main_page._output_button.setEnabled(True)
        self.main_page._output_textbox.setEnabled(True)
        self.main_page.settings_button.setEnabled(True)
        self.main_page.n_sets_box.setEnabled(True)
        self.main_page._progress_box.setVisible(False)

        self.app.restoreOverrideCursor()

        self.main_page._ready_for_nest()
