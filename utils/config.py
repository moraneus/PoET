# utils/config.py
"""Configuration management for PoET monitor."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration class for PoET monitor settings."""

    property_file: str
    trace_file: str
    reduce_enabled: bool = False
    visual_enabled: bool = False
    output_level: str = 'default'

    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_output_levels = ['nothing', 'experiment', 'default', 'max_state', 'debug']
        if self.output_level not in valid_output_levels:
            raise ValueError(f"Invalid output level: {self.output_level}. Must be one of {valid_output_levels}")

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.output_level == 'debug'

    @property
    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self.output_level in ['nothing', 'experiment', 'max_state']

    @property
    def is_max_state(self) -> bool:
        """Check if max state tracking is enabled."""
        return self.output_level == 'max_state'

    @property
    def show_banner(self) -> bool:
        """Check if banner should be shown."""
        return self.output_level not in ['experiment', 'nothing']