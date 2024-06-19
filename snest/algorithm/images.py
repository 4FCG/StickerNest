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

def load_image(path, margin):
    image = Image.open(path).transpose(method=Image.FLIP_TOP_BOTTOM)
    img_array = np.asarray(image)

    if img_array.shape[2] < 4: # Image does not have an alpha channel
        # Return a bounding box + margin instead
        bounding_box = Polygon([(0, 0), (img_array.shape[1], 0), (img_array.shape[1], img_array.shape[0]), (0 , img_array.shape[0])])
        buffered = buffer(bounding_box, margin)
        return buffered

    mask = img_array[:,:,3]!=0 # transparent pixels = False rest = True
    
    polygons = []

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE) # Convert mask to blackwhite image and finds contours

    # Turn all contours into polygons
    for contour in contours:
        if contour.shape[0] > 2: # skip if not at least 3 points, must be some floating pixels
            polygons.append(Polygon(contour[:,0,:]))

    # Unary union to remove overlaps
    # Concave hull to join separate parts
    hull = concave_hull(unary_union(polygons)).simplify(2)
    
    # Add margin as buffer
    buffered = buffer(hull, margin)
    return buffered
