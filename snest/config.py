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
from PySide6.QtCore import QLocale
from PySide6.QtGui import QDoubleValidator, QIntValidator, QFont
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QHBoxLayout, QScrollArea

A4_width = 210
A4_height = 297

class ConfigPage(QScrollArea):
    def __init__(self, parent = None, height = 300, width = 250, application_path = os.path.dirname(os.path.abspath(__file__))) -> None:
        super().__init__(parent)

        self.config_file = os.path.join(application_path, 'config.json')

        self.defaults = {
            'num_generations' : 50, # Number of generations.
            'population_size' : 20, # Number of solutions in the population.
            'mutation_rate' : 10,
            'rotations': 8, # 360/n angles to consider

            'n_processes' : multiprocessing.cpu_count(),

            'mm_width' : A4_width,
            'mm_height' : A4_height,
            'dpi' : 300,
            'margin' : 0, # margin to be added around the outside of each sticker's cut line
            'padding' : 0 # padding to be added to the inside of each sticker's cut line
        }

        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.setWidgetResizable(True)
        
        layout = QVBoxLayout()

        validator = QDoubleValidator(1.0, 99999.0, 2)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        validator.setLocale(QLocale("en_US"))

        # Output settings

        output_label = QLabel(self)
        output_label.setText('Output settings')
        output_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(output_label)

        layout.addSpacing(5)

        width_label = QLabel(self)
        width_label.setText('Output width (millimeter)')
        layout.addWidget(width_label)
        self.width_box = QLineEdit(self)
        self.width_box.setValidator(validator)
        self.width_box.setMinimumHeight(20)
        layout.addWidget(self.width_box)

        height_label = QLabel(self)
        height_label.setText('Output height (millimeter)')
        layout.addWidget(height_label)
        self.height_box = QLineEdit(self)
        self.height_box.setValidator(validator)
        self.height_box.setMinimumHeight(20)
        layout.addWidget(self.height_box)

        dpi_label = QLabel(self)
        dpi_label.setText('Output dpi')
        layout.addWidget(dpi_label)
        self.dpi_box = QLineEdit(self)
        self.dpi_box.setValidator(validator)
        self.dpi_box.setMinimumHeight(20)
        layout.addWidget(self.dpi_box)

        margin_label = QLabel(self)
        margin_label.setText('Sticker margin')
        layout.addWidget(margin_label)
        self.margin_box = QLineEdit(self)
        self.margin_box.setValidator(QIntValidator(0, 999))
        self.margin_box.setMinimumHeight(20)
        self.margin_box.setToolTip('Space between the cutting line and other lines.')
        layout.addWidget(self.margin_box)

        padding_label = QLabel(self)
        padding_label.setText('Sticker padding')
        layout.addWidget(padding_label)
        self.padding_box = QLineEdit(self)
        self.padding_box.setValidator(QIntValidator(0, 999))
        self.padding_box.setMinimumHeight(20)
        self.padding_box.setToolTip('Space between the sticker and its cutting line.')
        layout.addWidget(self.padding_box)

        layout.addSpacing(20)

        # Algorithm settings

        algo_label = QLabel(self)
        algo_label.setText('Algorithm settings')
        algo_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(algo_label)

        layout.addSpacing(5)

        gen_label = QLabel(self)
        gen_label.setText('Number of generations')
        layout.addWidget(gen_label)
        self.gen_box = QLineEdit(self)
        self.gen_box.setValidator(QIntValidator(1, 999))
        self.gen_box.setMinimumHeight(20)
        self.gen_box.setToolTip('The total amount of generations the optimizer does.')
        layout.addWidget(self.gen_box)

        pop_label = QLabel(self)
        pop_label.setText('Population size')
        layout.addWidget(pop_label)
        self.pop_box = QLineEdit(self)
        self.pop_box.setValidator(QIntValidator(2, 999))
        self.pop_box.setMinimumHeight(20)
        self.pop_box.setToolTip('The amount of random solutions created for each generation.')
        layout.addWidget(self.pop_box)

        mut_label = QLabel(self)
        mut_label.setText('Mutation rate')
        layout.addWidget(mut_label)
        self.mut_box = QLineEdit(self)
        self.mut_box.setValidator(QIntValidator(1, 100))
        self.mut_box.setMinimumHeight(20)
        self.mut_box.setToolTip('The percentage rate at which changes are randomly added.')
        layout.addWidget(self.mut_box)

        rot_label = QLabel(self)
        rot_label.setText('Rotations')
        layout.addWidget(rot_label)
        self.rot_box = QLineEdit(self)
        self.rot_box.setValidator(QIntValidator(1, 360))
        self.rot_box.setMinimumHeight(20)
        self.rot_box.setToolTip('The amount of different rotations to try, 1 for none, 4 for 90 degree angles, etc..')
        layout.addWidget(self.rot_box)

        # Save button

        button_layout = QHBoxLayout()
        button_box = QWidget(self)
        button_box.setLayout(button_layout)
        layout.addWidget(button_box)

        self.back_button = QPushButton("Back", self)
        button_layout.addWidget(self.back_button)

        self.save_button = QPushButton("Save Config", self)
        self.save_button.clicked.connect(self._set_config)
        button_layout.addWidget(self.save_button)

        config_widget = QWidget(self)
        config_widget.setLayout(layout)
        self.setWidget(config_widget)

        self._reload_config()

    def init_config(self):
        with open(self.config_file, "w") as file: 
            json.dump(self.defaults, file, indent=4)
        print(f'Created config.json at {self.config_file}')

    def load_config(self):
        if not os.path.isfile(self.config_file):
            self.init_config()

        with open(self.config_file, "r") as file:
            config = json.load(file)

        return config

    def save_config(self, changes):
        config = self.load_config()

        config.update(changes)

        with open(self.config_file, "w") as file:
            json.dump(config, file, indent=4)

        print(f'Saved changes to config.json at {self.config_file}')
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
        self.config = {
            'mm_width' : float(self.width_box.text()),
            'mm_height' : float(self.height_box.text()),
            'dpi' : float(self.dpi_box.text()),
            'margin' : int(self.margin_box.text()),
            'padding' : int(self.padding_box.text()),
            'num_generations': int(self.gen_box.text()),
            'population_size': int(self.pop_box.text()),
            'mutation_rate': int(self.mut_box.text()),
            'rotations': int(self.rot_box.text())
        }

        self.config = self.save_config(self.config)

    def showEvent(self, event):
        self._reload_config()
        event.accept()
