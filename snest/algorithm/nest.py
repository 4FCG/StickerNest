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

from typing import Self
import copy
from itertools import count
from multiprocessing.pool import Pool
from shapely import (Polygon, affinity, MultiLineString,
                     MultiPolygon, GeometryCollection)
import numpy as np
from snest.algorithm.minkowski import minkowski_diff_nfp, rectangle_ifp

TOL = 10**-9


def almost_equal(a, b, tolerance=TOL):
    return abs(a - b) < tolerance


class FitPoly:
    """Helper class for each polygon that must be fit.
        Keeps track of the original polygon,
        and all the transformation applied to it."""

    id_iter = count(1)

    def __init__(
        self, polygon: Polygon, rotation: float = 0,
        polygon_id: int | None = None
    ):
        self.polygon_id = polygon_id
        self.id = next(FitPoly.id_iter)
        self.original_polygon = polygon
        # Keeps track of total degrees rotated for nfp caching purposes
        self.rotation = rotation
        # This one will be moved around and rotated
        self.polygon = copy.deepcopy(polygon)

        # Defaults
        self.fit = False  # Flag representing if it has been placed or not
        self.bin_n = 0  # If placed, this represents what bin it is placed in
        # Keeps track of all transforms applied,
        # which is used later to get the images to their final fit position
        self.transformation = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def rotate(self, rotation: float) -> Self:
        """Function to apply rotation to the polygon."""
        if rotation == 0:
            return self

        self.rotation += rotation

        self.transformation = copy.copy(self.transformation)

        # Change rotation do rad for calculation purposes
        rotation = np.deg2rad(rotation)

        # Build rotation matrix with rotation centered
        # on the centroid of the polygon
        center = self.polygon.exterior.centroid.coords[0]
        x_off = (center[0] - center[0] * np.cos(rotation)
                 + center[1] * np.sin(rotation))
        y_off = (center[1] - center[0] * np.sin(rotation)
                 - center[1] * np.cos(rotation))

        rotation_matrix = np.array(
            [
                [np.cos(rotation), -np.sin(rotation), x_off],
                [np.sin(rotation), np.cos(rotation), y_off],
                [0, 0, 1],
            ]
        )

        # Add rotation to the transformation
        self.transformation = np.matmul(rotation_matrix, self.transformation)
        # Apply the rotation
        self.polygon = affinity.affine_transform(
            self.polygon,
            [
                np.cos(rotation),
                -np.sin(rotation),
                np.sin(rotation),
                np.cos(rotation),
                x_off,
                y_off,
            ],
        )
        return self

    def translate(self, translation: tuple[float, float]) -> Self:
        """Function to apply translation to the polygon."""
        # Add translation to the transformation
        self.transformation = np.matmul(
            np.array([
                [1, 0, translation[0]],
                [0, 1, translation[1]],
                [0, 0, 1]
            ]),
            self.transformation,
        )
        # Apply the translation
        self.polygon = affinity.translate(
            self.polygon, xoff=translation[0], yoff=translation[1]
        )
        return self


# Place where bounding box smallest using brute force
# Uses min bounding box as heuristic with double weight to the width
def place_poly(
    valid_nfp, placed: list[FitPoly], current_poly: FitPoly
) -> tuple[float, float] | None:
    """Returns the position of all valid_nfp positions where the polygon
        can be placed that adds the least amount of bin area used."""
    current_poly = copy.deepcopy(current_poly)

    # Check what kind of nfp we have
    if not valid_nfp:
        return None  # No valid points
    if isinstance(valid_nfp, MultiLineString) or isinstance(
        valid_nfp, GeometryCollection
    ):
        valid_coords = []
        for line in valid_nfp.geoms:
            valid_coords += line.coords
    else:
        valid_coords = list(valid_nfp.coords)

    minarea = None
    position = None
    minx = None

    placed_polys = [fitpoly.polygon for fitpoly in placed]

    # Brute force try every valid point along valid_nfp
    # Place the polygon there and calculate the area used
    for nfp_coord in valid_coords:
        shift_vector = (
            nfp_coord[0] - current_poly.polygon.exterior.coords[0][0],
            nfp_coord[1] - current_poly.polygon.exterior.coords[0][1],
        )

        translated_poly = affinity.translate(
            current_poly.polygon, xoff=shift_vector[0], yoff=shift_vector[1]
        )

        allpoints = MultiPolygon(placed_polys + [translated_poly])
        bounds = allpoints.bounds

        # weigh width more, to help compress in direction of gravity
        area = (bounds[2] - bounds[0]) * 2 + (bounds[3] - bounds[1])

        if (
            minarea is None
            or area < minarea
            or (
                almost_equal(minarea, area)
                and (minx is None or shift_vector[0] < minx)
            )
        ):
            minarea = area
            position = shift_vector
            minx = shift_vector[0]

    return position


def calc_nfp(tasks) -> dict[str, Polygon]:
    """Helper function to calculate nfps
        for a list of polygon pairs with multiprocessing."""
    new_cache = {}

    for task in tasks:
        key, A, B = task
        if A.polygon_id == 0:  # Inside fit for bin
            # Bin is never rotated, no rotations need to be done
            nfp_poly = rectangle_ifp(A.polygon, B.polygon)
        else:
            # Account for A's rotation
            rev_rotate = affinity.rotate(B.polygon, -A.rotation)
            nfp_poly = minkowski_diff_nfp(A.original_polygon, rev_rotate)

        new_cache[key] = nfp_poly

    return new_cache


# TODO Should this function return the cache instead of writing straight to it?
def calc_nfps(
    population,
    bin: FitPoly,
    cache: dict[str, Polygon],
    worker_pool: Pool,
    n_processes: int,
):
    """Calculates all nfps not yet cached and add them to the cache."""
    tasks = {}

    # The cache key represents a unique combination between
    # polygon A, polygon B and its rotation
    # If this key is not in the cache, it must be calculated
    for solution in population:
        polygons = solution.polys
        for i in range(0, len(polygons)):
            # The rotations keep stacking, remove all unnecessary 360's
            B_rotation = (polygons[i].rotation - 360 *
                          (polygons[i].rotation // 360))

            # Every polygon will need to get an ifp with the bin
            cache_key = (
                f"{bin.polygon_id},"
                f"{polygons[i].polygon_id}-{B_rotation}"
            )
            if (cache_key not in cache) and (cache_key not in tasks):
                tasks[cache_key] = (bin, polygons[i])

            # Each polygon will need an nfp with those before it in the order
            for previous_poly in polygons[:i]:
                A_rotation = previous_poly.rotation - 360 * (
                    previous_poly.rotation // 360
                )
                cache_key = (
                    f"{previous_poly.polygon_id},"
                    f"{polygons[i].polygon_id}-{B_rotation - A_rotation}"
                )
                if (cache_key not in cache) and (cache_key not in tasks):
                    tasks[cache_key] = (previous_poly, polygons[i])

    task_list = [(x[0], x[1][0], x[1][1]) for x in tasks.items()]
    # Split the tasks and run them parallel
    parts = np.array_split(
        task_list, n_processes
    )  # TODO is this split worth it if the amount of work per split is small?

    results = list(worker_pool.starmap(calc_nfp, [(x,) for x in parts]))
    # Add the new keys from each parallel result to the main cache
    for result in results:
        cache.update(result)


# TODO implement bin limit feature
def nest(
    bin: Polygon, polygons: list[FitPoly],
    cache: dict[str, Polygon], bin_limit: int = 0
) -> tuple[float, list[list[FitPoly]]]:
    """Places the given polygons in the given order,
        adding new bins should a polygon not fit anymore.
        Returns the fitness score and a list of bins,
        each containing a list of polygons that are placed in said bin.
    """
    for poly in polygons:
        poly.fit = False

    fitness = 0

    to_place = copy.copy(polygons)
    bin_n = 0
    result = []

    # This outer loop represents adding bins
    while len(to_place) > 0:
        placed = []

        polygon_nfp = None

        while (
            polygon_nfp is None and len(to_place) > 0
        ):  # Skip until a polygon that fits the bin is found
            B_rotation = (to_place[0].rotation - 360 *
                          (to_place[0].rotation // 360))
            ifp = cache[f"0,{to_place[0].polygon_id}-{B_rotation}"]
            if ifp:
                polygon_nfp = ifp
            else:
                # remove from list as it cant be placed anyways
                to_place.pop(0)

        if polygon_nfp:
            # The first placement is just the bottom left of the bin
            # position is the offset to be applied to the polygon
            position = None
            for i in range(len(polygon_nfp.exterior.coords) - 1):
                if (
                    position is None
                    or polygon_nfp.exterior.coords[i][0]
                    - to_place[0].polygon.exterior.coords[0][0]
                    < position[0]
                ):
                    position = (
                        polygon_nfp.exterior.coords[i][0]
                        - to_place[0].polygon.exterior.coords[0][0],
                        polygon_nfp.exterior.coords[i][1]
                        - to_place[0].polygon.exterior.coords[0][1],
                    )

            first = to_place[0].translate((position[0], position[1]))

            placed.append(first)
            first.bin_n = bin_n
            first.fit = True

        # After the first placement we need to start taking into account
        # previously placed polygons
        for i in range(1, len(to_place)):
            B_rotation = (to_place[i].rotation - 360 *
                          (to_place[i].rotation // 360))

            # Get the inner fit of the polygon with the bin
            inner_poly = cache[f"0,{to_place[i].polygon_id}-{B_rotation}"]

            if not inner_poly:
                continue  # It doesn't fit the bin

            full_nfp = None
            # For all previously placed ones
            for placed_poly in placed:

                A_rotation = (placed_poly.rotation - 360 *
                              (placed_poly.rotation // 360))

                cache_key = (
                    f"{placed_poly.polygon_id},"
                    f"{to_place[i].polygon_id}-{B_rotation - A_rotation}"
                )

                # Get cached nfp and translate +
                # rotate it to the current position
                nfp_poly = cache[cache_key]
                nfp_poly = affinity.affine_transform(
                    nfp_poly,
                    [
                        placed_poly.transformation[0][0],
                        placed_poly.transformation[0][1],
                        placed_poly.transformation[1][0],
                        placed_poly.transformation[1][1],
                        placed_poly.transformation[0][2],
                        placed_poly.transformation[1][2],
                    ],
                )

                # Join the new nfp with the previous ones
                if full_nfp is None:
                    full_nfp = nfp_poly
                else:
                    full_nfp = full_nfp.union(
                        nfp_poly
                    )  # TODO This can fail with invalid geom

            # Calculate the valid placements by
            # intersecting the nfp with the ifp
            # If the nfp consists of disconnected points or lines,
            # intersect each with the ifp and merge the results
            if isinstance(full_nfp, GeometryCollection) or isinstance(
                full_nfp, MultiPolygon
            ):
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

            # Find the best placement for the polygon
            # in all the valid placements
            placement = place_poly(valid, placed, to_place[i])
            if placement:
                # Apply the translation and place the polygon,
                # if a placement was found
                to_place[i].translate(placement)
                placed.append(to_place[i])
                to_place[i].fit = True
                to_place[i].bin_n = bin_n

        for poly in placed:
            to_place.pop(to_place.index(poly))

        if len(placed) > 0:
            # merge all placed polygons to calculate space used
            allpoints = MultiPolygon([fitpoly.polygon for fitpoly in placed])
            bounds = allpoints.bounds
            width = bounds[2] - bounds[0]
            # Small punishment for width used, to incentivize better fits
            fitness += width / bin.area

        bin_n += 1
        result.append(placed)

    placed_count = sum([1 for poly in polygons if poly.fit])

    # Lower is better
    # Punish for each polygon that could not be fit
    fitness += (len(polygons) - placed_count) * 2
    # Punish for each extra bin required
    fitness += bin_n

    return (fitness, result)
