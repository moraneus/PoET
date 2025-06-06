# utils/config.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Configuration management for PoET monitor settings including output levels,
# logging configuration, and runtime behavior control.

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Config:
    """Configuration class for PoET monitor settings."""

    property_file: str
    trace_file: str
    reduce_enabled: bool = False
    visual_enabled: bool = False
    output_level: str = "default"
    log_file: Optional[str] = None
    log_categories: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_output_level()
        self._process_log_categories()

    def _validate_output_level(self) -> None:
        """Validate output level configuration."""
        valid_output_levels = ["nothing", "experiment", "default", "max_state", "debug"]
        if self.output_level not in valid_output_levels:
            raise ValueError(
                f"Invalid output level: {self.output_level}. Must be one of {valid_output_levels}"
            )

    def _process_log_categories(self) -> None:
        """Process log_categories if provided as string from command line."""
        if isinstance(self.log_categories, str):
            if self.log_categories.strip() == "":
                self.log_categories = []
            else:
                self.log_categories = [
                    cat.strip().upper()
                    for cat in self.log_categories.split(",")
                    if cat.strip()
                ]

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.output_level == "debug"

    @property
    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self.output_level in ["nothing", "experiment", "max_state"]

    @property
    def is_max_state(self) -> bool:
        """Check if max state tracking is enabled."""
        return self.output_level == "max_state"

    @property
    def show_banner(self) -> bool:
        """Check if banner should be shown."""
        return self.output_level not in ["experiment", "nothing", "max_state"]

    @property
    def log_level(self) -> str:
        """Convert PoET output level to logger level."""
        mapping = {
            "nothing": "nothing",
            "experiment": "warn",  # ← Changed from "info" to "warn"
            "default": "info",
            "max_state": "debug",
            "debug": "debug",
        }
        return mapping.get(self.output_level, "info")

    def should_log_category(self, category: str) -> bool:
        """Check if a specific log category should be logged."""
        if self.log_categories is None:
            return True
        if not self.log_categories:
            return False
        return category.upper() in self.log_categories

    def get_log_config(self) -> dict:
        """Get logging configuration as dictionary."""
        return {
            "level": self.log_level,
            "file": self.log_file,
            "categories": self.log_categories,
            "output_level": self.output_level,
        }
