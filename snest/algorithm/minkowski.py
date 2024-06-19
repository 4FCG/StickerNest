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

from shapely import Polygon, affinity, MultiPoint
import numpy as np

def minkowski_diff_nfp(A, B):

    A_inv = affinity.scale(A, -1, -1, origin=(0, 0))
    new_points = []
    for i in range(2):
        coord_A = A_inv.exterior.xy[i]
        coord_B = B.exterior.xy[i]
        new_coords = np.add(*np.meshgrid(coord_A, coord_B)).reshape(-1)
        new_points.append(new_coords)

    hull = MultiPoint(np.stack(new_points, 1)).convex_hull

    ref_point = B.exterior.coords[0]

    nfp = affinity.affine_transform(hull, [-1, 0, 0, -1, ref_point[0], ref_point[1]])
    return nfp

def rectangle_ifp(rect, poly):

    rect_width = rect.bounds[2] - rect.bounds[0]
    rect_height = rect.bounds[3] - rect.bounds[1]

    poly_width = poly.bounds[2] - poly.bounds[0]
    poly_height = poly.bounds[3] - poly.bounds[1]

    if poly_width > rect_width or poly_height > rect_height: # Ensure it can actually fit inside the rect
        return None

    ref_point = poly.exterior.coords[0]
    offsets = np.array([ref_point[0] - poly.bounds[0], ref_point[1] - poly.bounds[1], ref_point[0] - poly.bounds[2], ref_point[1] - poly.bounds[3]])
    bounds = rect.bounds + offsets

    new_square = [(bounds[0], bounds[1]), (bounds[0], bounds[3]), (bounds[2], bounds[3]), (bounds[2], bounds[1])]

    ifp = Polygon(new_square)
    
    return ifp
