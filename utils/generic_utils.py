# utils/generic_utils.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Generic utility functions for file I/O operations including JSON parsing
# and property file reading for configuration and trace data.

import json
from typing import Any, Dict


class GenericUtils:
    """Generic utility functions for file operations."""

    @staticmethod
    def read_json(json_file: str) -> Dict[str, Any]:
        """Read and parse JSON file."""
        with open(json_file, "r") as file:
            data = json.load(file)
        return data

    @staticmethod
    def read_property(property_file: str) -> str:
        """Read property file content as string."""
        with open(property_file, "r") as file:
            content = file.read()
        return content
