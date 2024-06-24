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
import sys
import multiprocessing as mp
from PySide6.QtWidgets import QApplication
from snest import UI

if __name__ == "__main__":
    mp.set_start_method("spawn")
    mp.freeze_support()  # needed for Windows
    app = QApplication([])

    if getattr(sys, "frozen", False):
        # Path to the exe itself
        application_path = os.path.dirname(sys.executable)
        # Path to the folder containing all the backend files for the exe
        internal_dir = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        internal_dir = application_path

    window = UI.UIWrapper(application_path, internal_dir, app)
    window.show()

    sys.exit(app.exec())
