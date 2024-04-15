import os.path
from typing import List, Tuple

import cairosvg as cairosvg
from graphviz import Digraph
import glob
from PIL import Image

from model.state import State


class Automaton:

    __COUNTER = 1

    @staticmethod
    def create_automaton(i_states: List[State], i_transitions: List[Tuple[str, str, str]]):
        automaton = Digraph(comment='Automaton', format='svg')

        # Create index of propositions
        index = {}
        for s in i_states:
            index[s.name] = s.propositions

        # Create nodes for states
        for s in i_states:
            if s.value:
                bgcolor = 'lightblue'
                table_bgcolor = '#ADD8E6'
            else:
                bgcolor = 'lightgrey'
                table_bgcolor = '#D3D3D3'

            # Customizing label with HTML-like syntax for different font sizes and colors
            propositions = ', '.join(index[s.name])
            if propositions:
                label = f'''<<table border="0" cellborder="0" cellspacing="0" style="rounded" bgcolor="{table_bgcolor}">
                                <tr><td border="0"><font color="black" point-size="12">{s.name}</font></td></tr>
                                <hr/>
                                <tr><td border="0"><font color="black" point-size="8">{propositions}</font></td></tr>
                            </table>>'''
            else:
                label = f'''<<table border="0" cellborder="0" cellspacing="0" style="rounded" bgcolor="{table_bgcolor}">
                                <tr><td border="0"><font color="black" point-size="12">{s.name}</font></td></tr>
                            </table>>'''

            automaton.node(s.name, label, style='filled', fillcolor=bgcolor, shape='rectangle')

        # Create edges for transitions
        for start, end, label in i_transitions:
            automaton.edge(end, start, label=label, fontsize='9')

        automaton.render(f'output/graph_{Automaton.__COUNTER}', view=False)
        Automaton.__COUNTER += 1

    @staticmethod
    def make_gif(frame_folder):
        # Get a list of SVG files in the output folder
        svg_files = [image for image in glob.glob(f"{frame_folder}{os.sep}*.svg")]

        # Sort the SVG files based on their names
        svg_files.sort()

        # Convert SVG files to PNG format
        png_files = []
        for svg_file in svg_files:
            png_file = os.path.splitext(svg_file)[0] + ".png"
            cairosvg.svg2png(url=svg_file, write_to=png_file)
            png_files.append(png_file)

        # Open the PNG files as image frames
        frames = [Image.open(image) for image in png_files]

        # Determine the maximum width and height among all frames
        max_width = max(frame.width for frame in frames)
        max_height = max(frame.height for frame in frames)

        # Create a new list to store the resized frames
        resized_frames = []

        # Resize each frame to the maximum size
        for frame in frames:
            resized_frame = Image.new('RGBA', (max_width, max_height), (255, 255, 255, 0))
            resized_frame.paste(frame, ((max_width - frame.width) // 2, (max_height - frame.height) // 2))
            resized_frames.append(resized_frame)

        # Save the resized frames as a GIF
        resized_frames[0].save(
            f"{os.path.join(frame_folder, 'graph.gif')}",
            format="GIF",
            append_images=resized_frames[1:],
            save_all=True,
            duration=1000,
            loop=1,
            disposal=2
        )

        # Clean up the temporary PNG files
        for png_file in png_files:
            os.remove(png_file)
