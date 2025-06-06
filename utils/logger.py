# utils/logger.py
"""
Comprehensive logging utility for the PoET (Partial Order Execution Tracer) project.
Provides structured logging with different levels and specialized debugging capabilities.
"""

import sys
import time
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path


class LogLevel(Enum):
    """Log levels for different types of output."""

    NOTHING = "nothing"  # Suppress all output except errors
    ERROR = "error"  # Only critical errors
    WARN = "warn"  # Warnings and errors
    INFO = "info"  # General information
    DEBUG = "debug"  # Detailed debugging
    TRACE = "trace"  # Maximum verbosity
    EXPERIMENT = "experiment"  # Minimal output for benchmarks


class LogCategory(Enum):
    """Categories for different types of log messages."""

    GENERAL = "GENERAL"
    PARSER = "PARSER"
    AST = "AST"
    TRACE = "TRACE"
    EVENT = "EVENT"
    STATE = "STATE"
    VECTOR_CLOCK = "VC"
    PCTL = "PCTL"
    PERFORMANCE = "PERF"
    VISUAL = "VISUAL"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    data: Optional[Dict[str, Any]] = None
    indent: int = 0


class PoETLogger:
    """
    Comprehensive logger for the PoET project with support for:
    - Multiple log levels
    - Categorized logging
    - Structured data logging
    - Performance tracking
    - File output
    - Integration with existing Prints class
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        output_file: Optional[str] = None,
        allowed_categories: Optional[List[str]] = None,
    ):
        """
        Initialize the logger.

        Args:
            level: Default logging level
            output_file: Optional file to write logs to
            allowed_categories: List of allowed log categories (None means all)
        """
        self.level = level
        self.output_file = output_file
        self.log_entries: List[LogEntry] = []
        self.indent_level = 0
        self.start_time = time.time()

        # Set allowed categories
        self.allowed_categories = None
        if allowed_categories is not None:
            # Convert strings to LogCategory enums
            self.allowed_categories = set()
            for cat in allowed_categories:
                try:
                    self.allowed_categories.add(LogCategory(cat.upper()))
                except ValueError:
                    pass  # Ignore invalid categories

        self.category_colors = {
            LogCategory.GENERAL: "",
            LogCategory.AST: "\033[38;5;208m",  # Orange/Amber
            LogCategory.PARSER: "\033[95m",  # Magenta
            LogCategory.TRACE: "\033[96m",  # Cyan
            LogCategory.EVENT: "\033[92m",  # Green
            LogCategory.STATE: "\033[94m",  # Blue
            LogCategory.VECTOR_CLOCK: "\033[93m",  # Yellow
            LogCategory.PCTL: "\033[91m",  # Red
            LogCategory.PERFORMANCE: "\033[90m",  # Gray
            LogCategory.VISUAL: "\033[97m",  # White
            LogCategory.ERROR: "\033[91m\033[1m",  # Bold Red
        }
        self.reset_color = "\033[0m"

        # Performance tracking
        self.timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}

        # Initialize file if specified
        if self.output_file:
            self._init_log_file()

    def _init_log_file(self):
        """Initialize the log file."""
        try:
            log_path = Path(self.output_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w") as f:
                f.write(f"PoET Execution Log - Started at {time.ctime()}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file {self.output_file}: {e}")

    def set_level(self, level: Union[LogLevel, str]):
        """Set the logging level."""
        if isinstance(level, str):
            try:
                level = LogLevel(level.lower())
            except ValueError:
                level = LogLevel.INFO
        self.level = level

    def _should_log(self, level: LogLevel, category: LogCategory) -> bool:
        """Check if a message should be logged based on current level and category."""
        # First check level
        level_order = {
            LogLevel.NOTHING: 0,
            LogLevel.ERROR: 1,
            LogLevel.WARN: 2,
            LogLevel.INFO: 3,
            LogLevel.DEBUG: 4,
            LogLevel.TRACE: 5,
            LogLevel.EXPERIMENT: 3,  # Same as INFO
        }

        if level_order.get(level, 3) > level_order.get(self.level, 3):
            return False

        # Then check category if filtering is enabled
        if self.allowed_categories is not None:
            return category in self.allowed_categories

        return True

    def _format_message(self, entry: LogEntry) -> str:
        """Format a log entry for display."""
        elapsed = entry.timestamp - self.start_time
        indent = "  " * entry.indent

        # Color coding
        color = self.category_colors.get(entry.category, "")
        reset = self.reset_color if color else ""

        # Format timestamp
        time_str = f"[{elapsed:8.3f}s]"

        # Format category
        cat_str = f"[{entry.category.value:>8}]"

        # Build message
        msg = f"{color}{time_str} {cat_str} {indent}{entry.data or ''}{entry.message}{reset}"

        return msg

    def _log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        indent_override: Optional[int] = None,
    ):
        """Internal logging method."""
        if not self._should_log(level, category):
            return

        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            data=data,
            indent=(
                indent_override if indent_override is not None else self.indent_level
            ),
        )

        self.log_entries.append(entry)

        # Output to console
        formatted_msg = self._format_message(entry)
        print(formatted_msg)
        sys.stdout.flush()

        # Output to file if specified
        if self.output_file:
            try:
                with open(self.output_file, "a") as f:
                    # Strip color codes for file output
                    clean_msg = formatted_msg
                    for color in self.category_colors.values():
                        clean_msg = clean_msg.replace(color, "")
                    clean_msg = clean_msg.replace(self.reset_color, "")
                    f.write(clean_msg + "\n")
            except Exception:
                pass  # Silently ignore file write errors

    # Convenience methods for different log levels
    def error(self, message: str, category: LogCategory = LogCategory.ERROR, **kwargs):
        """Log an error message."""
        self._log(LogLevel.ERROR, category, message, kwargs if kwargs else None)

    def warn(self, message: str, category: LogCategory = LogCategory.GENERAL, **kwargs):
        """Log a warning message."""
        self._log(LogLevel.WARN, category, message, kwargs if kwargs else None)

    def info(self, message: str, category: LogCategory = LogCategory.GENERAL, **kwargs):
        """Log an info message."""
        self._log(LogLevel.INFO, category, message, kwargs if kwargs else None)

    def debug(
        self, message: str, category: LogCategory = LogCategory.GENERAL, **kwargs
    ):
        """Log a debug message."""
        self._log(LogLevel.DEBUG, category, message, kwargs if kwargs else None)

    def trace(
        self, message: str, category: LogCategory = LogCategory.GENERAL, **kwargs
    ):
        """Log a trace message."""
        self._log(LogLevel.TRACE, category, message, kwargs if kwargs else None)

    # Specialized logging methods for PoET components
    def event(
        self,
        event_name: str,
        vector_clock: List[int],
        propositions: List[str],
        processes: List[str],
        **kwargs,
    ):
        """Log event processing."""
        data = {"vc": vector_clock, "props": propositions, "procs": processes, **kwargs}
        self._log(LogLevel.DEBUG, LogCategory.EVENT, f"Processing {event_name}", data)

    def state(
        self,
        state_name: str,
        propositions: Set[str],
        verdict: bool,
        enabled: bool = True,
        **kwargs,
    ):
        """Log state information."""
        data = {
            "props": sorted(propositions),
            "verdict": verdict,
            "enabled": enabled,
            **kwargs,
        }
        self._log(LogLevel.DEBUG, LogCategory.STATE, f"State {state_name}", data)

    def pctl_eval(
        self,
        formula: str,
        state_name: str,
        result: bool,
        breakdown: Optional[Dict[str, Any]] = None,
    ):
        """Log PCTL formula evaluation."""
        data = {"formula": formula, "result": result}
        if breakdown:
            data.update(breakdown)
        self._log(
            LogLevel.DEBUG,
            LogCategory.PCTL,
            f"PCTL eval on {state_name}: {result}",
            data,
        )

    def vector_clock(
        self,
        action: str,
        expected_vc: List[int],
        event_vc: List[int] = None,
        in_order: bool = None,
    ):
        """Log vector clock operations."""
        data = {"expected": expected_vc}
        if event_vc:
            data["event"] = event_vc
        if in_order is not None:
            data["in_order"] = in_order
        self._log(LogLevel.DEBUG, LogCategory.VECTOR_CLOCK, action, data)

    def performance(self, metric: str, value: Union[float, int], unit: str = ""):
        """Log performance metrics."""
        data = {"value": value, "unit": unit}
        self._log(
            LogLevel.INFO, LogCategory.PERFORMANCE, f"{metric}: {value}{unit}", data
        )

    # Context management for indentation
    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)

    def section(self, title: str, category: LogCategory = LogCategory.GENERAL):
        """Start a new section with separator."""
        separator = "=" * 60
        self._log(self.level, category, separator)
        self._log(self.level, category, title.upper())
        self._log(self.level, category, separator)

    # Timer utilities
    def start_timer(self, name: str):
        """Start a named timer."""
        self.timers[name] = time.time()
        self.trace(f"Timer '{name}' started", LogCategory.PERFORMANCE)

    def end_timer(self, name: str) -> float:
        """End a named timer and return elapsed time."""
        if name not in self.timers:
            self.warn(f"Timer '{name}' was not started")
            return 0.0

        elapsed = time.time() - self.timers[name]
        del self.timers[name]
        self.performance(f"Timer '{name}'", elapsed, "s")
        return elapsed

    # Counter utilities
    def increment_counter(self, name: str, amount: int = 1):
        """Increment a named counter."""
        self.counters[name] = self.counters.get(name, 0) + amount
        self.trace(f"Counter '{name}': {self.counters[name]}")

    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        return self.counters.get(name, 0)

    # Summary and statistics
    def print_summary(self):
        """Print execution summary."""
        if not self._should_log(LogLevel.INFO, LogCategory.GENERAL):
            return

        self.section("EXECUTION SUMMARY")

        total_time = time.time() - self.start_time
        self.performance("Total execution time", total_time, "s")
        self.performance("Total log entries", len(self.log_entries))

        # Counter summary
        if self.counters:
            self.info("Counters:")
            self.indent()
            for name, value in sorted(self.counters.items()):
                self.info(f"{name}: {value}")
            self.dedent()

        # Category breakdown
        category_counts = {}
        for entry in self.log_entries:
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        if category_counts:
            self.info("Log entries by category:")
            self.indent()
            for category, count in sorted(
                category_counts.items(), key=lambda x: x[1], reverse=True
            ):
                self.info(f"{category.value}: {count}")
            self.dedent()


# Global logger instance
_logger: Optional[PoETLogger] = None


def get_logger() -> PoETLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = PoETLogger()
    return _logger


def init_logger(
    level: Union[LogLevel, str] = LogLevel.INFO,
    output_file: Optional[str] = None,
    allowed_categories: Optional[List[str]] = None,
) -> PoETLogger:
    """Initialize the global logger."""
    global _logger
    if isinstance(level, str):
        level = LogLevel(level.lower())
    _logger = PoETLogger(level, output_file, allowed_categories)
    return _logger


def set_log_level(level: Union[LogLevel, str]):
    """Set the global logger level."""
    get_logger().set_level(level)


# Convenience functions for common logging operations
def log_error(message: str, **kwargs):
    """Log an error message."""
    get_logger().error(message, **kwargs)


def log_warn(message: str, **kwargs):
    """Log a warning message."""
    get_logger().warn(message, **kwargs)


def log_info(message: str, **kwargs):
    """Log an info message."""
    get_logger().info(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log a debug message."""
    get_logger().debug(message, **kwargs)


def log_event(
    event_name: str,
    vector_clock: List[int],
    propositions: List[str],
    processes: List[str],
    **kwargs,
):
    """Log event processing."""
    get_logger().event(event_name, vector_clock, propositions, processes, **kwargs)


def log_state(state_name: str, propositions: Set[str], verdict: bool, **kwargs):
    """Log state information."""
    get_logger().state(state_name, propositions, verdict, **kwargs)


def log_pctl_eval(formula: str, state_name: str, result: bool, **kwargs):
    """Log PCTL evaluation."""
    get_logger().pctl_eval(formula, state_name, result, **kwargs)
