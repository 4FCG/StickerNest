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

from PIL import Image
from shapely import Polygon, buffer, concave_hull
from shapely.ops import unary_union
import numpy as np
import cv2

def load_image(path: str, margin: int) -> Polygon:
    """Loads image file and returns outline Polygon by removing transparent pixels."""
    # Flip y coordinates as they are inverted in images
    image = Image.open(path).transpose(method=Image.FLIP_TOP_BOTTOM).convert('RGBA') # TODO Can this be replaced by cv2?
    img_array = np.asarray(image)

    mask = img_array[:,:,3]!=0 # transparent pixels = False, everything else = True
    
    polygons = []

    # Convert mask to black-white image and finds contours
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # Turn all contours into polygons
    for contour in contours:
        # TODO Could skipping this cause issues?
        if contour.shape[0] > 2: # skip if not at least 3 points, likely some floating pixels
            # Apply 0 buffer to close any holes present
            polygons.append(buffer(Polygon(contour[:,0,:]), 0))

    # Unary union to remove overlaps
    # Concave hull to join separate parts
    hull = concave_hull(unary_union(polygons)).simplify(2)
    
    # Add margin as buffer
    buffered = buffer(hull, margin)
    return buffered
