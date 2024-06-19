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
from shapely import Polygon
from tqdm import tqdm
import numpy as np
from snest.algorithm.nest import nest, FitPoly, calc_nfps
from snest.algorithm.images import load_image

class Solution():
    def __init__(self, polys, mutation_rate, bin: FitPoly, rotations = 4):
        self.polys = copy.deepcopy(polys)
        self.mutation_rate = mutation_rate
        self.bin = bin
        self.fitness = None
        self.fitted = None
        self.rotations = rotations

    def random_angle(self):
        angle = random.choice([i*(360/self.rotations) for i in range(self.rotations)])
        return angle

    def mutate(self):
        for i in range(len(self.polys)):
            # Order mutation: swap current with next poly
            if random.random() < 0.01 * self.mutation_rate and i + 1 < len(self.polys):
                self.polys[i], self.polys[i+1] = self.polys[i+1], self.polys[i]
            # Rotation mutation
            if random.random() < 0.01 * self.mutation_rate:
                self.polys[i].rotate(self.random_angle())

        return self
    
    def fit(self, cache):
        if not self.fitted:
            fitness, result = nest(self.bin.polygon, self.polys, cache)
            self.fitness = fitness
            self.fitted = result
        return self

def load_file(input):
    file, margin = input
    return (load_image(file, margin), file)

def run_fit(tasks, cache):
    return [solution.fit(cache) for solution in tasks]

class Fitter_GA():
    def __init__(self, bin_width, bin_height, num_generations, population_size, mutation_rate, n_processes, rotations, callback = None):
        
        # Prepare the bin
        bin_coords = ((0., 0.), (0., bin_height), (bin_width, bin_height), (bin_width, 0.))
        self.bin = FitPoly(Polygon(bin_coords), polygon_id=0)

        self.num_generations = num_generations
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.n_processes = n_processes
        self.rotations = rotations
        self.callback = callback
        self.pool = None

    def __enter__(self):
        # Set the worker pool
        self.pool = mp.Pool(self.n_processes)
        return self
    
    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.pool.close()

    def set_polygons(self, polygons: list[Polygon], iterations: int) -> list[FitPoly]:
        new_polygons = []
        # Repeat the polys n times for multiple sets, but repeats do not need their own ID
        for c in range(iterations):
            new_polygons += [FitPoly(polygon, polygon_id=i) for i, polygon in enumerate(polygons, 1)] # TODO BAD NEST LOOP
        self.polygons = new_polygons
    
    def __mate(self, male: Solution, female: Solution):
        cutoff_point = random.randint(1, len(male.polys) - 1)

        child_1 = male.polys[:cutoff_point]
        child_2 = female.polys[:cutoff_point]

        for poly in female.polys:
            if not any(x.id == poly.id for x in child_1):
                child_1.append(poly)

        for poly in male.polys:
            if not any(x.id == poly.id for x in child_2):
                child_2.append(poly)

        return [Solution(child_1, self.mutation_rate, self.bin, self.rotations), Solution(child_2, self.mutation_rate, self.bin, self.rotations)]

    def __new_generation(self, population: list[Solution]):
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
            if len(new_pop) < len(population):
                new_pop.append(children[1].mutate())

        return new_pop

    def calculate_fit(self):
        if self.pool is None:
            raise RuntimeError("Cannot fit before assigning the worker pool, use with statement.")

        self.cache = {}

        # Initial order heuristic is descending area size
        ordered_polygons = copy.copy(self.polygons)
        ordered_polygons.sort(key=lambda x: x.polygon.area, reverse=True)

        population = [Solution(ordered_polygons, self.mutation_rate, self.bin, self.rotations)]

        for i in range(self.population_size - 1):
            mutant = Solution(ordered_polygons, self.mutation_rate, self.bin, self.rotations).mutate()
            population.append(mutant)

        for i in tqdm(range(self.num_generations), desc = f'Running Fitting Algorithm', total = self.num_generations):
            calc_nfps(population, self.bin, self.cache, self.pool, self.n_processes)
            
            parts = np.array_split(population, min(self.n_processes, self.population_size//5))
            results = list(self.pool.starmap(run_fit, [(x, self.cache) for x in parts]))
                
            if i < self.num_generations - 1:
                population = self.__new_generation(sum(results, []))
            else:
                population = sum(results, [])

            if self.callback:
                self.callback(i)


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
