# graphics/automaton.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Automaton visualization generation using Graphviz for state diagrams
# and GIF animation creation from SVG outputs.

import os
import glob
from typing import List, Tuple

import cairosvg
from graphviz import Digraph
from PIL import Image

from model.state import State


class Automaton:
    """Handles automaton visualization and animation generation."""

    __COUNTER = 1

    @staticmethod
    def create_automaton(
        i_states: List[State], i_transitions: List[Tuple[str, str, str]]
    ) -> None:
        """Create automaton visualization from states and transitions."""
        automaton = Digraph(comment="Automaton", format="svg")

        propositions_index = Automaton._build_propositions_index(i_states)
        Automaton._add_nodes_to_graph(automaton, i_states, propositions_index)
        Automaton._add_edges_to_graph(automaton, i_transitions)

        automaton.render(f"output/graph_{Automaton.__COUNTER}", view=False)
        Automaton.__COUNTER += 1

    @staticmethod
    def _build_propositions_index(states: List[State]) -> dict:
        """Build index mapping state names to their propositions."""
        index = {}
        for state in states:
            index[state.name] = state.propositions
        return index

    @staticmethod
    def _add_nodes_to_graph(
        automaton: Digraph, states: List[State], propositions_index: dict
    ) -> None:
        """Add state nodes to the automaton graph."""
        for state in states:
            bgcolor, table_bgcolor = Automaton._get_node_colors(state)
            label = Automaton._create_node_label(
                state, propositions_index, table_bgcolor
            )

            automaton.node(
                state.name, label, style="filled", fillcolor=bgcolor, shape="rectangle"
            )

    @staticmethod
    def _get_node_colors(state: State) -> Tuple[str, str]:
        """Get background colors for state node based on its value."""
        if state.value:
            return "lightblue", "#ADD8E6"
        else:
            return "lightgrey", "#D3D3D3"

    @staticmethod
    def _create_node_label(
        state: State, propositions_index: dict, table_bgcolor: str
    ) -> str:
        """Create HTML label for state node."""
        propositions = ", ".join(propositions_index[state.name])

        if propositions:
            return f"""<<table border="0" cellborder="0" cellspacing="0" style="rounded" bgcolor="{table_bgcolor}">
                <tr><td border="0"><font color="black" point-size="12">{state.name}</font></td></tr>
                <hr/>
                <tr><td border="0"><font color="black" point-size="8">{propositions}</font></td></tr>
                </table>>"""
        else:
            return f"""<<table border="0" cellborder="0" cellspacing="0" style="rounded" bgcolor="{table_bgcolor}">
                <tr><td border="0"><font color="black" point-size="12">{state.name}</font></td></tr>
                </table>>"""

    @staticmethod
    def _add_edges_to_graph(
        automaton: Digraph, transitions: List[Tuple[str, str, str]]
    ) -> None:
        """Add transition edges to the automaton graph."""
        for start, end, label in transitions:
            automaton.edge(end, start, label=label, fontsize="9")

    @staticmethod
    def make_gif(frame_folder: str) -> None:
        """Create animated GIF from SVG files in the specified folder."""
        svg_files = Automaton._get_sorted_svg_files(frame_folder)

        if not svg_files:
            return

        png_files = Automaton._convert_svg_to_png(svg_files)
        frames = Automaton._load_image_frames(png_files)
        resized_frames = Automaton._resize_frames_to_max_size(frames)
        Automaton._save_gif(resized_frames, frame_folder)
        Automaton._cleanup_png_files(png_files)

    @staticmethod
    def _get_sorted_svg_files(frame_folder: str) -> List[str]:
        """Get sorted list of SVG files from the frame folder."""
        svg_files = glob.glob(f"{frame_folder}{os.sep}*.svg")
        svg_files.sort()
        return svg_files

    @staticmethod
    def _convert_svg_to_png(svg_files: List[str]) -> List[str]:
        """Convert SVG files to PNG format."""
        png_files = []
        for svg_file in svg_files:
            png_file = os.path.splitext(svg_file)[0] + ".png"
            cairosvg.svg2png(url=svg_file, write_to=png_file)
            png_files.append(png_file)
        return png_files

    @staticmethod
    def _load_image_frames(png_files: List[str]) -> List[Image.Image]:
        """Load PNG files as image frames."""
        return [Image.open(image) for image in png_files]

    @staticmethod
    def _resize_frames_to_max_size(frames: List[Image.Image]) -> List[Image.Image]:
        """Resize all frames to the maximum dimensions."""
        max_width, max_height = Automaton._get_max_dimensions(frames)

        resized_frames = []
        for frame in frames:
            resized_frame = Automaton._create_resized_frame(
                frame, max_width, max_height
            )
            resized_frames.append(resized_frame)

        return resized_frames

    @staticmethod
    def _get_max_dimensions(frames: List[Image.Image]) -> Tuple[int, int]:
        """Get maximum width and height among all frames."""
        max_width = max(frame.width for frame in frames)
        max_height = max(frame.height for frame in frames)
        return max_width, max_height

    @staticmethod
    def _create_resized_frame(
        frame: Image.Image, max_width: int, max_height: int
    ) -> Image.Image:
        """Create resized frame centered in maximum dimensions."""
        resized_frame = Image.new("RGBA", (max_width, max_height), (255, 255, 255, 0))
        x_offset = (max_width - frame.width) // 2
        y_offset = (max_height - frame.height) // 2
        resized_frame.paste(frame, (x_offset, y_offset))
        return resized_frame

    @staticmethod
    def _save_gif(resized_frames: List[Image.Image], frame_folder: str) -> None:
        """Save resized frames as animated GIF."""
        output_path = os.path.join(frame_folder, "graph.gif")
        resized_frames[0].save(
            output_path,
            format="GIF",
            append_images=resized_frames[1:],
            save_all=True,
            duration=1000,
            loop=1,
            disposal=2,
        )

    @staticmethod
    def _cleanup_png_files(png_files: List[str]) -> None:
        """Remove temporary PNG files."""
        for png_file in png_files:
            os.remove(png_file)
