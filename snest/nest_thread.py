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

from PySide6.QtCore import QThread, Signal
from snest.algorithm.GA import Fitter_GA, load_file
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import multiprocessing as mp
from tqdm import tqdm
from PIL import Image
from shapely import buffer
import textwrap

mpl.use('agg')

MM = 1/25.4  # mm to inch

class NestThread(QThread):
    completed = Signal()
    update_progress = Signal(int)
    new_loading = Signal(tuple)

    def __init__(self, images, output_dir, n_sets, config, parent=None):
        super().__init__(parent)

        self.images = images
        self.output_dir = output_dir
        self.config = config
        self.n_sets = n_sets

    def run(self):
        bin_width = self.config['mm_width'] * MM * self.config['dpi']
        bin_height = self.config['mm_height'] * MM * self.config['dpi']
        
        pool = mp.Pool(self.config['n_processes'])

        self.new_loading.emit((0, len(self.images), 'Loading Images'))

        # Create a list of loading tasks to be done in parallel
        load_tasks = []

        for image in self.images:
            if os.path.isfile(image):
                # Add margin + padding, then later we remove the margin
                load_tasks.append((image, self.config['padding'] + self.config['margin']))

        # Load images in parallel
        files = []

        for i, file in enumerate(tqdm(pool.imap_unordered(load_file, load_tasks), total=len(self.images), desc='Loading images')):
            files.append(file)
            self.update_progress.emit(i)

        pool.close()

        self.new_loading.emit((0, self.config['num_generations'], 'Running Optimizer'))
        # Prepare the fitter with all the configuration settings
        fitter = Fitter_GA(
            bin_width, bin_height, self.config['num_generations'], self.config['population_size'],
            self.config['mutation_rate'], self.config['n_processes'], self.config['rotations'], callback=self.update_progress.emit
        )
        
        polygons = []
        image_paths = []

        for file in files:
            polygons.append(file[0])
            image_paths.append(file[1])
        # Send the polygons to the fitter
        fitter.set_polygons(polygons, self.n_sets)
        # Bind polygon ID to image path so we can later get the image for each fitted polygon
        image_binds = {i: image_paths[i - 1] for i in range(1, len(polygons) + 1)}
        # Run GA
        with fitter as ga:
            best = ga.calculate_fit()

        self.new_loading.emit((0, len(best.fitted), 'Exporting Results'))
        # Loop through all the bins of the resulting best fit
        for i, page in enumerate(best.fitted):
            
            # Create plot of correct size
            fig, ax = plt.subplots(figsize=(self.config['mm_width'] * MM, self.config['mm_height'] * MM), dpi=self.config['dpi'])
            ax.margins(x=0, y=0)
            # Add the bin to the SVG file, so that it can easily be overlapped with the images
            cutlines = [fitter.bin.polygon]

            for poly in page:
                if poly.fit:
                    # Remove the margin from the polygon, leaving it padding distance away from the image
                    cutlines.append(buffer(poly.polygon, -self.config['margin'])) # TODO Due to simplification, this may cause slight overlaps with the image if the padding is 0
                    # Fetch the image that belongs to the polygon and flip its y axis to fit the way we fit polygons
                    image = Image.open(image_binds[poly.polygon_id]).transpose(method=Image.FLIP_TOP_BOTTOM)
                    # Apply the FitPoly transformation to the image, moving it to its fitted position
                    transform = mpl.transforms.Affine2D(poly.transformation)

                    imgplot = ax.imshow(image)
                    imgplot.set_transform(transform + ax.transData)

            ax.invert_yaxis()
            # Plot the bin, so the image is sized correctly
            ax.plot(*fitter.bin.polygon.exterior.xy, color='black', alpha=0.0)
            plt.axis('off')
            # Ensure the plot is the full image
            plt.tight_layout(pad=0, w_pad=0, h_pad=0)
            png_output = os.path.join(self.output_dir, f'export{i}.png')
            plt.savefig(png_output, dpi=self.config['dpi'])
            plt.close()
            
            print(f'Created export file {i} at {png_output}')

            bbox = fitter.bin.polygon.bounds
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            # Prepare svg file props
            props = {
                'version': '1.1',
                'baseProfile': 'full',
                'width': f'{self.config["mm_width"]}mm',
                'height': f'{self.config["mm_height"]}mm',
                'viewBox': '%.1f,%.1f,%.1f,%.1f' % (bbox[0], bbox[1], width, height),
                'xmlns': 'http://www.w3.org/2000/svg',
                'xmlns:ev': 'http://www.w3.org/2001/xml-events',
                'xmlns:xlink': 'http://www.w3.org/1999/xlink'
            }

            # Turn the polygons into svg strings
            data = ''
            for svg in cutlines:
                data += svg.exterior.svg(1.0, opacity=1.0) + '\n'

            # This flips the y axis
            flip_y = f'<g transform="translate(0,{height})">\n<g transform="scale(1,-1)">\n'

            # Format and write the svg file
            svg_output = os.path.join(self.output_dir, f'export{i}.svg')

            with open(svg_output, 'w') as f:
                f.write(textwrap.dedent(r'''
                    <?xml version="1.0" encoding="utf-8" ?>
                    <svg {attrs:s}>
                    {flip:s}
                    {data:s}
                    </g>
                    </g>
                    </svg>
                ''').format(
                    attrs = ' '.join(['{key:s}="{val:s}"'.format(key = key, val = props[key]) for key in props]),
                    data = data,
                    flip = flip_y
                ).strip())

            print(f'Created cut line file {i} at {svg_output}')
            self.update_progress.emit(i)

        print('Algorithm finished')
        self.completed.emit()
