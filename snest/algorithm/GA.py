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

import multiprocessing as mp
import copy
import random
from typing import Self, Callable
from shapely import Polygon
from tqdm import tqdm
import numpy as np
from snest.algorithm.nest import nest, FitPoly, calc_nfps

class Solution():
    """Class representing 1 possible fit solution. With a unique order and rotations."""
    def __init__(self, polys: list[FitPoly], mutation_rate: int, bin: FitPoly, rotations: int):
        self.polys = copy.deepcopy(polys)
        self.mutation_rate = mutation_rate
        self.bin = bin
        self.fitness = None
        self.fitted = None
        self.rotations = rotations

    def random_angle(self) -> float:
        """Return a random angle from the allowed rotations."""
        angle = random.choice([i*(360/self.rotations) for i in range(self.rotations)])
        return angle

    def mutate(self) -> Self:
        """Randomly mutate this solution's order and rotations."""
        for i in range(len(self.polys)):
            # Order mutation: swap current with next poly
            if random.random() < 0.01 * self.mutation_rate and i + 1 < len(self.polys):
                self.polys[i], self.polys[i+1] = self.polys[i+1], self.polys[i]
            # Rotation mutation
            if random.random() < 0.01 * self.mutation_rate:
                self.polys[i].rotate(self.random_angle())

        return self
    
    def fit(self, cache: dict[str, Polygon]) -> Self:
        """Run the fitting algorithm on the solution, after which it's polys are arranged in a possible fit."""
        if not self.fitted:
            fitness, result = nest(self.bin.polygon, self.polys, cache)
            self.fitness = fitness
            self.fitted = result
        return self

def run_fit(tasks: list[Solution], cache: dict[str, Polygon]) -> list[Solution]:
    """Helper function to run fit with multiprocessing."""
    return [solution.fit(cache) for solution in tasks]

class Fitter_GA():
    """Class representing the genetic algorithm responsible for finding better fits."""
    def __init__(self, bin_width: float, bin_height: float, num_generations: int, population_size: int, mutation_rate: int, n_processes: int, rotations: int, callback: Callable = None):
        # Prepare the bin
        bin_coords = ((0., 0.), (0., bin_height), (bin_width, bin_height), (bin_width, 0.))
        self.bin = FitPoly(Polygon(bin_coords), polygon_id=0) # Bin is always ID 0, this assumption is used.
        # Save settings
        self.num_generations = num_generations
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.n_processes = n_processes
        self.rotations = rotations
        self.callback = callback
        self.pool = None

    def __enter__(self): # TODO Forcing use of With is not clean
        # Set the worker pool
        self.pool = mp.Pool(self.n_processes)
        return self
    
    def __exit__(self, exception_type, exception_value, exception_traceback):
        # Close pool on With exit
        self.pool.close()

    # TODO This function is probably best not kept here
    # as it serves only to ensure the polygon_id is the same as the image IDs as set in nest_thread
    def set_polygons(self, polygons: list[Polygon], iterations: int) -> list[FitPoly]:
        """Helper function to turn polygons into FitPolys n = iterations amount of times."""
        new_polygons = []
        # Repeat the polys n times for multiple sets, but repeats do not need their own ID
        for c in range(iterations):
            # This has to be repeated because polys are created with unique internal ID
            # The order is the same as the image order, later used to connect polygon back to image
            # Polygon_id is for linking to image, internal id is for fitting cache purposes
            new_polygons += [FitPoly(polygon, polygon_id=i) for i, polygon in enumerate(polygons, 1)]
        self.polygons = new_polygons
    
    def __mate(self, male: Solution, female: Solution) -> tuple[Solution, Solution]:
        """Function that applies single point crossover to two parent solutions, creating 2 new children."""
        # In the edge case that only 1 image is being fitted, skip the mate as it is useless
        if len(male.polys) == 1:
            # We want to return the same Solutions, but make sure to turn of the fit flag
            male.fitted = None
            female.fitted = None
            return (male, female)

        cutoff_point = random.randint(1, len(male.polys) - 1)

        child_1 = male.polys[:cutoff_point]
        child_2 = female.polys[:cutoff_point]

        # Every solution must contain each polygon
        # Append to the end of each child, from the other parent, the polys they are missing
        for poly in female.polys:
            if not any(x.id == poly.id for x in child_1):
                child_1.append(poly)

        for poly in male.polys:
            if not any(x.id == poly.id for x in child_2):
                child_2.append(poly)

        return (Solution(child_1, self.mutation_rate, self.bin, self.rotations), Solution(child_2, self.mutation_rate, self.bin, self.rotations))

    def __new_generation(self, population: list[Solution]) -> list[Solution]:
        """Function that creates a new generation by mating and mutating."""
        # Low to high fitness, lower is better
        population.sort(key=lambda x: x.fitness)

        # Keep the best
        new_pop = [population[0]] # Elitism

        while len(new_pop) < len(population):
            # Assign weights to each solution, with decreasing chances
            weights = [1/(idx+1) for idx in range(len(population))]
            sw = sum(weights)
            weights = [w/sw for w in weights] # Ensure weights sum to 1

            # Draw 2 at random (with weights), without replacing
            draw = np.random.choice(population, 2, p=weights, replace=False)

            children = self.__mate(draw[0], draw[1])
            # Mutate and add the children
            new_pop.append(children[0].mutate())
            # Skip second child if target size already met
            if len(new_pop) < len(population):
                new_pop.append(children[1].mutate())

        return new_pop

    def calculate_fit(self) -> Solution:
        """Function that starts the genetic algorithm, going through the set amount of generations and returning the best Solution."""
        if self.pool is None:
            raise RuntimeError("Cannot fit before assigning the worker pool, use with statement.")

        self.cache = {}

        # Initial order heuristic is descending area size
        ordered_polygons = copy.copy(self.polygons)
        ordered_polygons.sort(key=lambda x: x.polygon.area, reverse=True)

        # Start with an unmutated solution
        population = [Solution(ordered_polygons, self.mutation_rate, self.bin, self.rotations)]

        # Fill the generation to the desired size with mutated solutions
        for i in range(self.population_size - 1):
            mutant = Solution(ordered_polygons, self.mutation_rate, self.bin, self.rotations).mutate()
            population.append(mutant)

        for i in tqdm(range(self.num_generations), desc = f'Running Fitting Algorithm', total = self.num_generations):
            calc_nfps(population, self.bin, self.cache, self.pool, self.n_processes)
            
            # TODO currently this uses a heuristic to avoid splitting up small populations into really tiny splits
            # But is this the correct way to go about it.
            parts = np.array_split(population, min(self.n_processes, self.population_size//5))
            results = list(self.pool.starmap(run_fit, [(x, self.cache) for x in parts]))

            # If the algorithm is not finished, make a new generation, otherwise just merge results
            if i < self.num_generations - 1:
                population = self.__new_generation(sum(results, []))
            else:
                population = sum(results, [])

            if self.callback:
                self.callback(i)

        # Lowest fitness is best
        population.sort(key=lambda x: x.fitness)
        best = population[0]
        counter = 0

        for poly in best.polys:
            if poly.fit:
                counter += 1
            
        print(f'Fit a total of {counter} objects')
        print(f'Used a total of {len(best.fitted)} bins')
        print(f'Solution fitness score (lower is better): {best.fitness}')

        return best
