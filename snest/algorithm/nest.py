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

from shapely import Polygon, affinity, MultiLineString, MultiPolygon, GeometryCollection
from itertools import count
import copy
from snest.algorithm.minkowski import minkowski_diff_nfp, rectangle_ifp
import numpy as np

TOL = 10 ** -9

def almost_equal(a, b, tolerance=TOL):
    return abs(a - b) < tolerance

class FitPoly():
    id_iter = count(1)

    def __init__(self, polygon: Polygon, rotation = 0, polygon_id=None):
        self.polygon_id = polygon_id
        self.id = next(FitPoly.id_iter)
        self.original_polygon = polygon
        self.rotation = rotation
        self.polygon = copy.deepcopy(polygon)

        # Defaults
        self.fit = False
        self.bin_n = 0
        self.transformation = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) # Keeps track of all transforms applied

    def rotate(self, rotation):
        if rotation == 0:
            return self
        
        self.rotation += rotation

        self.transformation = copy.copy(self.transformation)

        rotation = np.deg2rad(rotation)

        center = self.polygon.exterior.centroid.coords[0]
        x_off = center[0] - center[0] * np.cos(rotation) + center[1] * np.sin(rotation)
        y_off = center[1] - center[0] * np.sin(rotation) - center[1] * np.cos(rotation)
        
        rotation_matrix = np.array([[np.cos(rotation), -np.sin(rotation), x_off], [np.sin(rotation), np.cos(rotation), y_off], [0, 0, 1]])

        self.transformation = np.matmul(rotation_matrix, self.transformation)
        self.polygon = affinity.affine_transform(self.polygon, [np.cos(rotation), -np.sin(rotation), np.sin(rotation), np.cos(rotation), x_off, y_off])
        return self
    
    def translate(self, translation):
        self.transformation = np.matmul(np.array([[1, 0, translation[0]], [0, 1, translation[1]], [0, 0, 1]]), self.transformation)
        self.polygon = affinity.translate(self.polygon, xoff=translation[0], yoff=translation[1])
        return self

# Place where bounding box smallest using brute force
# Uses min bounding box as heuristic with double weight to the width
def place_poly(valid_nfp, placed: list[FitPoly], current_poly: FitPoly, bin: Polygon):
    current_poly = copy.deepcopy(current_poly)

    if not valid_nfp:
        return None # No valid points
    if isinstance(valid_nfp, MultiLineString) or isinstance(valid_nfp, GeometryCollection):
        valid_coords = []
        for line in valid_nfp.geoms:
            valid_coords += line.coords
    else:
        valid_coords = list(valid_nfp.coords)
    
    minarea = None
    position = None
    minx = None

    placed_polys = [fitpoly.polygon for fitpoly in placed]
    
    for nfp_coord in valid_coords:
        shift_vector = {
            'x': nfp_coord[0] - current_poly.polygon.exterior.coords[0][0],
            'y': nfp_coord[1] - current_poly.polygon.exterior.coords[0][1],
        }

        translated_poly = affinity.translate(current_poly.polygon, xoff=shift_vector['x'], yoff=shift_vector['y'])

        allpoints = MultiPolygon(placed_polys + [translated_poly])
        bounds = allpoints.bounds

        # weigh width more, to help compress in direction of gravity
        area = (bounds[2] - bounds[0])*2 + (bounds[3] - bounds[1])

        if minarea is None or area < minarea or (almost_equal(minarea, area) and (minx is None or shift_vector['x'] < minx)):
            minarea = area
            position = shift_vector
            minx = shift_vector['x']

    if position:
        return (position['x'], position['y'])
    else:
        return None

def calc_nfp(tasks):
    new_cache = {}

    for task in tasks:
        key, A, B = task
        if A.polygon_id == 0: # Inside fit for bin
            # Bin is never rotated, no rotations need to be done
            nfp_poly = rectangle_ifp(A.polygon, B.polygon)
        else:
            rev_rotate = affinity.rotate(B.polygon, -A.rotation)
            nfp_poly = minkowski_diff_nfp(A.original_polygon, rev_rotate)

        new_cache[key] = nfp_poly

    return new_cache
        

def calc_nfps(population, bin, cache, worker_pool, n_processes):
    tasks = {}

    for solution in population:
        polygons = solution.polys
        for i in range(0, len(polygons)):
            B_rotation = polygons[i].rotation - 360 * (polygons[i].rotation//360)

            cache_key = f'{bin.polygon_id},{polygons[i].polygon_id}-{B_rotation}'
            if (cache_key not in cache) and (cache_key not in tasks):
                tasks[cache_key] = (bin, polygons[i])

            for previous_poly in polygons[:i]:
                A_rotation = previous_poly.rotation - 360 * (previous_poly.rotation//360)
                cache_key = f'{previous_poly.polygon_id},{polygons[i].polygon_id}-{B_rotation - A_rotation}'
                if (cache_key not in cache) and (cache_key not in tasks):
                    tasks[cache_key] = (previous_poly, polygons[i])

    task_list = [(x[0], x[1][0], x[1][1]) for x in tasks.items()]

    parts = np.array_split(task_list, n_processes)

    results = list(worker_pool.starmap(calc_nfp, [(x,) for x in parts]))

    for result in results:
        cache.update(result)


def nest(bin: Polygon, polygons: list[FitPoly], cache, bin_limit: int = 0): # TODO implement bin limit feature
    for poly in polygons:
        poly.fit = False
    
    fitness = 0

    to_place = copy.copy(polygons)
    bin_n = 0
    result = []

    while len(to_place) > 0:
        placed = []

        polygon_nfp = None

        while polygon_nfp is None and len(to_place) > 0: # Skip until a polygon that fits the bin is found
            B_rotation = to_place[0].rotation - 360 * (to_place[0].rotation//360)
            ifp = cache[f'0,{to_place[0].polygon_id}-{B_rotation}']
            if ifp:
                polygon_nfp = ifp
            else:
                to_place.pop(0) # remove from list as it cant be placed anyways

        if polygon_nfp:
            # The first placement is just the bottom left of the bin
            position = None # position is the offset to be applied to the polygon
            for i in range(len(polygon_nfp.exterior.coords) - 1):
                if position is None or polygon_nfp.exterior.coords[i][0] - to_place[0].polygon.exterior.coords[0][0] < position[0]:
                    position = (
                        polygon_nfp.exterior.coords[i][0] - to_place[0].polygon.exterior.coords[0][0],
                        polygon_nfp.exterior.coords[i][1] - to_place[0].polygon.exterior.coords[0][1]
                    )
            
            first = to_place[0].translate((position[0], position[1]))

            placed.append(first)
            first.bin_n = bin_n
            first.fit = True

        for i in range(1, len(to_place)):
            B_rotation = to_place[i].rotation - 360 * (to_place[i].rotation//360)
            
            # Get the inner fit of the polygon with the bin
            inner_poly = cache[f'0,{to_place[i].polygon_id}-{B_rotation}']

            if not inner_poly:
                continue # It doesn't fit the bin

            full_nfp = None
            for placed_poly in placed:

                A_rotation = placed_poly.rotation - 360 * (placed_poly.rotation//360)
                
                cache_key = f'{placed_poly.polygon_id},{to_place[i].polygon_id}-{B_rotation - A_rotation}'
                
                # Get cached nfp and translate + rotate it to the current position
                nfp_poly = cache[cache_key]
                nfp_poly = affinity.affine_transform(nfp_poly, [placed_poly.transformation[0][0], placed_poly.transformation[0][1], placed_poly.transformation[1][0], placed_poly.transformation[1][1], placed_poly.transformation[0][2], placed_poly.transformation[1][2]])

                # Join the new nfp with the previous ones
                if full_nfp is None:
                    full_nfp = nfp_poly
                else:
                    full_nfp = full_nfp.union(nfp_poly) # TODO This can fail with invalid geom
            
            # Calculate the valid placements by intersecting the nfp with the ifp
            # If the nfp consists of disconnected points or lines, intersect each with the ifp and merge the results
            if isinstance(full_nfp, GeometryCollection) or isinstance(full_nfp, MultiPolygon):
                valid = None
                for geom in full_nfp.geoms:
                    line = geom
                    if isinstance(geom, Polygon):
                        line = geom.exterior
                    if valid:
                        valid = valid.union(line.intersection(inner_poly))
                    else:
                        valid = line.intersection(inner_poly)
            else:
                valid = full_nfp.exterior.intersection(inner_poly)
            
            # Find the best placement for the polygon in all the valid placements
            placement = place_poly(valid, placed, to_place[i], bin)
            if placement:
                # Apply the translation and place the polygon, if a placement was found
                to_place[i].translate(placement)
                placed.append(to_place[i])
                to_place[i].fit = True
                to_place[i].bin_n = bin_n

        for poly in placed:
            to_place.pop(to_place.index(poly))

        if len(placed) > 0:
            allpoints = MultiPolygon([fitpoly.polygon for fitpoly in placed])
            bounds = allpoints.bounds
            width = (bounds[2] - bounds[0])
            fitness += width/bin.area # Small punishment for width used, to incentivize better fits

        bin_n += 1
        result.append(placed)

    placed_count = sum([1 for poly in polygons if poly.fit])

    # Lower is better
    fitness += (len(polygons) - placed_count) * 2 # Punish for each polygon that could not be fit
    fitness += bin_n # Punish for each extra bin required

    return fitness, result
