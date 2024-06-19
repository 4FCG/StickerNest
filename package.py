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

import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--onedir',
    '--name',
    'StickerNest',
    '--hiddenimport',
    'pkg_resources.extern', # https://github.com/pyinstaller/pyinstaller/issues/8554
    '--icon',
    'logo.ico',
    '--noconfirm',
    '--add-data',
    'logo.ico:.'
])