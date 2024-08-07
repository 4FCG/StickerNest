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
import multiprocessing
import json
from typing import TypedDict
from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator, QFont
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QScrollArea,
)

A4_width = 210.0
A4_height = 297.0


class Config(TypedDict):
    num_generations: int  # Number of generations.
    population_size: int  # Number of solutions in the population.
    mutation_rate: int  # % chance of mutation between 1 - 100
    rotations: int  # 360/n angles to consider

    # Amount of processors assigned to pools
    n_processes: int

    mm_width: float  # Bin sizes
    mm_height: float
    dpi: float
    # margin to be added around the outside of each sticker's cut line
    margin: int
    # padding to be added to the inside of each sticker's cut line
    padding: int


class ConfigPage(QWidget):
    def __init__(
        self,
        parent: QWidget = None,
        application_path=os.path.dirname(os.path.abspath(__file__)),
    ) -> None:
        super().__init__(parent)

        self.config_file = os.path.join(application_path, "config.json")

        self.defaults = {
            "num_generations": 50,
            "population_size": 20,
            "mutation_rate": 10,
            "rotations": 8,
            "n_processes": multiprocessing.cpu_count(),
            "mm_width": A4_width,
            "mm_height": A4_height,
            "dpi": 300.0,
            "margin": 5,
            "padding": 5,
        }

        # self.setFixedWidth(width)
        # self.setFixedHeight(height)

        page_layout = QVBoxLayout()

        scroll_area = QScrollArea(self)
        scroll_area.horizontalScrollBar().setEnabled(False)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setWidgetResizable(True)

        page_layout.addWidget(scroll_area)

        layout = QVBoxLayout()
        config_widget = QWidget(self)
        config_widget.setLayout(layout)
        scroll_area.setWidget(config_widget)

        # Output settings

        output_label = QLabel(config_widget)
        output_label.setText("Output settings")
        output_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(output_label)

        layout.addSpacing(5)

        width_label = QLabel(config_widget)
        width_label.setText("Output width (millimeter)")
        layout.addWidget(width_label)
        self.width_box = QLineEdit(config_widget)
        width_validator = QDoubleValidator(1.0, 99999.0, 2, self.width_box)
        width_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        width_validator.setLocale(QLocale("en_US"))
        self.width_box.setValidator(width_validator)
        self.width_box.setMinimumHeight(20)
        layout.addWidget(self.width_box)

        notation = QDoubleValidator.Notation.StandardNotation

        height_label = QLabel(config_widget)
        height_label.setText("Output height (millimeter)")
        layout.addWidget(height_label)
        self.height_box = QLineEdit(config_widget)
        height_validator = QDoubleValidator(1.0, 99999.0, 2, self.height_box)
        height_validator.setNotation(notation)
        height_validator.setLocale(QLocale("en_US"))
        self.height_box.setValidator(height_validator)
        self.height_box.setMinimumHeight(20)
        layout.addWidget(self.height_box)

        dpi_label = QLabel(config_widget)
        dpi_label.setText("Output dpi")
        layout.addWidget(dpi_label)
        self.dpi_box = QLineEdit(config_widget)
        dpi_validator = QDoubleValidator(1.0, 99999.0, 2, self.dpi_box)
        dpi_validator.setNotation(notation)
        dpi_validator.setLocale(QLocale("en_US"))
        self.dpi_box.setValidator(dpi_validator)
        self.dpi_box.setMinimumHeight(20)
        layout.addWidget(self.dpi_box)

        margin_label = QLabel(config_widget)
        margin_label.setText("Sticker margin")
        layout.addWidget(margin_label)
        self.margin_box = QLineEdit(config_widget)
        self.margin_box.setValidator(QIntValidator(0, 99999, self.margin_box))
        self.margin_box.setMinimumHeight(20)
        self.margin_box.setToolTip(
            "Space between the cutting line and other lines."
        )
        layout.addWidget(self.margin_box)

        padding_label = QLabel(config_widget)
        padding_label.setText("Sticker padding")
        layout.addWidget(padding_label)
        self.padding_box = QLineEdit(config_widget)
        self.padding_box.setValidator(
            QIntValidator(0, 99999, self.padding_box)
        )
        self.padding_box.setMinimumHeight(20)
        self.padding_box.setToolTip(
            "Space between the sticker and its cutting line."
        )
        layout.addWidget(self.padding_box)

        layout.addSpacing(20)

        # Algorithm settings

        algo_label = QLabel(config_widget)
        algo_label.setText("Algorithm settings")
        algo_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(algo_label)

        layout.addSpacing(5)

        gen_label = QLabel(config_widget)
        gen_label.setText("Number of generations")
        layout.addWidget(gen_label)
        self.gen_box = QLineEdit(config_widget)
        self.gen_box.setValidator(QIntValidator(1, 999, self.gen_box))
        self.gen_box.setMinimumHeight(20)
        self.gen_box.setToolTip(
            "The total amount of generations the optimizer does."
        )
        layout.addWidget(self.gen_box)

        pop_label = QLabel(config_widget)
        pop_label.setText("Population size")
        layout.addWidget(pop_label)
        self.pop_box = QLineEdit(config_widget)
        self.pop_box.setValidator(QIntValidator(2, 999, self.pop_box))
        self.pop_box.setMinimumHeight(20)
        self.pop_box.setToolTip(
            "The amount of random solutions created for each generation."
        )
        layout.addWidget(self.pop_box)

        mut_label = QLabel(config_widget)
        mut_label.setText("Mutation rate")
        layout.addWidget(mut_label)
        self.mut_box = QLineEdit(config_widget)
        self.mut_box.setValidator(QIntValidator(1, 100, self.mut_box))
        self.mut_box.setMinimumHeight(20)
        self.mut_box.setToolTip(
            "The percentage rate (1-100) at which changes are randomly added."
        )
        layout.addWidget(self.mut_box)

        rot_label = QLabel(config_widget)
        rot_label.setText("Rotations")
        layout.addWidget(rot_label)
        self.rot_box = QLineEdit(config_widget)
        self.rot_box.setValidator(QIntValidator(1, 360, self.rot_box))
        self.rot_box.setMinimumHeight(20)
        self.rot_box.setToolTip(
            "The amount of different rotations to try, "
            "1 for none, 4 for 90 degree angles, etc.."
        )
        layout.addWidget(self.rot_box)

        # Save button

        button_layout = QHBoxLayout()
        button_box = QWidget(self)
        button_box.setLayout(button_layout)
        page_layout.addWidget(button_box)

        self.back_button = QPushButton("Back", button_box)
        button_layout.addWidget(self.back_button)

        self.save_button = QPushButton("Save Config", button_box)
        self.save_button.clicked.connect(self._set_config)
        button_layout.addWidget(self.save_button)

        self.setLayout(page_layout)

        self._reload_config()

    def init_config(self):
        with open(self.config_file, "w") as file:
            json.dump(self.defaults, file, indent=4)
        print(f"Created config.json at {self.config_file}")

    def load_config(self) -> Config:
        if not os.path.isfile(self.config_file):
            self.init_config()

        with open(self.config_file, "r") as file:
            config: Config = json.load(file)

        return config

    def save_config(self, changes: Config) -> Config:
        config = self.load_config()

        config.update(changes)

        with open(self.config_file, "w") as file:
            json.dump(config, file, indent=4)

        print(f"Saved changes to config.json at {self.config_file}")
        return config

    def _reload_config(self):
        self.config = self.load_config()

        self.width_box.setText(str(self.config["mm_width"]))
        self.height_box.setText(str(self.config["mm_height"]))
        self.dpi_box.setText(str(self.config["dpi"]))
        self.margin_box.setText(str(self.config["margin"]))
        self.padding_box.setText(str(self.config["padding"]))
        self.gen_box.setText(str(self.config["num_generations"]))
        self.pop_box.setText(str(self.config["population_size"]))
        self.mut_box.setText(str(self.config["mutation_rate"]))
        self.rot_box.setText(str(self.config["rotations"]))

    def _set_config(self):
        self.config: Config = {
            "mm_width": max(float(self.width_box.text()), 1.0),
            "mm_height": max(float(self.height_box.text()), 1.0),
            "dpi": max(float(self.dpi_box.text()), 1.0),
            "margin": int(self.margin_box.text()),
            "padding": int(self.padding_box.text()),
            "num_generations": max(int(self.gen_box.text()), 1),
            "population_size": max(int(self.pop_box.text()), 2),
            "mutation_rate": max(int(self.mut_box.text()), 1),
            "rotations": max(int(self.rot_box.text()), 1),
        }

        self.config = self.save_config(self.config)
        self._reload_config()

    def showEvent(self, event):
        self._reload_config()
        event.accept()
