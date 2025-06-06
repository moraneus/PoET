#!/usr/bin/env python3
# poet.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Main entry point for the PoET application providing command-line interface
# for property-oriented event trace monitoring and PCTL verification.

"""
PoET: Property-oriented Event Trace Monitor

Usage:
  poet.py --property=<property_file> --trace=<trace_file> [--reduce] [--visual] [--output-level=<level>] [--log-file=<file>] [--log-categories=<cats>]
  poet.py -p <property_file> -t <trace_file> [-r] [-v] [--output-level=<level>] [--log-file=<file>] [--log-categories=<cats>]

Options:
  -p <property_file>, --property=<property_file>  Property filename (PCTL specification). (Mandatory)
  -t <trace_file>, --trace=<trace_file>             Trace filename (JSON format). (Mandatory)
  -r, --reduce                                      Enable reduce mode: prunes redundant states from the graph. (Optional)
  -v, --visual                                      Enable visual output: generates state graph files (SVG, GIF). (Optional)
  --output-level=<level>                            Specify output verbosity:
                                                    'nothing'    (suppresses all non-error console output).
                                                    'experiment' (minimal output for benchmarks; prints stats and final PCTL verdict).
                                                    'default'    (standard operational messages; prints final PCTL verdict).
                                                    'max_state'  (prints summary for the system's current global state defined by the
                                                                  monitor's vector clock after each event, plus final PCTL verdict.
                                                                  Also prints a collected list of these summaries at the end).
                                                    'debug'      (maximum detailed output for developers; includes all prints).
                                                    [default: default]
  --log-file=<file>                                Optional file to write structured logs to (e.g., poet_debug.log)
  --log-categories=<cats>                          Comma-separated list of log categories to enable.
                                                   Available: GENERAL,PARSER,TRACE,EVENT,STATE,VC,PCTL,PERF,VISUAL,ERROR
                                                   If not specified, all categories are logged.
                                                   Use empty string or 'none' to disable all logging categories.
  -h, --help                                        Show this help message and exit.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Optional

from docopt import docopt

from core.poet_monitor import PoETMonitor
from utils.config import Config
from utils.logger import init_logger, get_logger, LogLevel, LogCategory


def validate_arguments(arguments: dict) -> None:
    """Validate command line arguments."""
    logger = get_logger()

    property_file = arguments["--property"]
    trace_file = arguments["--trace"]

    _validate_required_files(property_file, trace_file, logger)
    _validate_file_existence(property_file, trace_file, logger)
    _validate_output_level(arguments["--output-level"], logger)
    _validate_log_file(arguments.get("--log-file"), logger)
    _validate_log_categories(arguments.get("--log-categories"), logger)

    logger.debug("Argument validation completed successfully", LogCategory.GENERAL)


def _validate_required_files(property_file: str, trace_file: str, logger) -> None:
    """Validate that required files are specified."""
    if not property_file:
        logger.error("Property file is required", LogCategory.ERROR)
        print("ERROR: Property file is required. Use -p or --property option.")
        sys.exit(1)

    if not trace_file:
        logger.error("Trace file is required", LogCategory.ERROR)
        print("ERROR: Trace file is required. Use -t or --trace option.")
        sys.exit(1)


def _validate_file_existence(property_file: str, trace_file: str, logger) -> None:
    """Validate that specified files exist."""
    if not Path(property_file).exists():
        logger.error(f"Property file not found: {property_file}", LogCategory.ERROR)
        print(f"ERROR: Property file not found: {property_file}")
        sys.exit(1)

    if not Path(trace_file).exists():
        logger.error(f"Trace file not found: {trace_file}", LogCategory.ERROR)
        print(f"ERROR: Trace file not found: {trace_file}")
        sys.exit(1)


def _validate_output_level(output_level: Optional[str], logger) -> None:
    """Validate output level argument."""
    valid_levels = ["nothing", "experiment", "default", "max_state", "debug"]
    level = output_level or "default"

    if level not in valid_levels:
        logger.error(f"Invalid output level: {level}", LogCategory.ERROR)
        print(
            f"ERROR: Invalid output level '{level}'. Must be one of: {', '.join(valid_levels)}"
        )
        sys.exit(1)


def _validate_log_file(log_file: Optional[str], logger) -> None:
    """Validate log file path and write access."""
    if not log_file:
        return

    log_path = Path(log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        test_file = log_path.with_suffix(".test")
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        logger.error(f"Cannot write to log file: {log_file}", LogCategory.ERROR)
        print(f"ERROR: Cannot write to log file '{log_file}': {e}")
        sys.exit(1)


def _validate_log_categories(log_categories: Optional[str], logger) -> None:
    """Validate log categories argument."""
    if not log_categories or log_categories.lower() in ["", "none"]:
        return

    valid_categories = [cat.value for cat in LogCategory]
    specified_cats = [
        cat.strip().upper() for cat in log_categories.split(",") if cat.strip()
    ]
    invalid_cats = [cat for cat in specified_cats if cat not in valid_categories]

    if invalid_cats:
        logger.error(f"Invalid log categories: {invalid_cats}", LogCategory.ERROR)
        print(f"ERROR: Invalid log categories: {', '.join(invalid_cats)}")
        print(f"Valid categories: {', '.join(valid_categories)}")
        sys.exit(1)


def setup_logging(arguments: dict):
    """Setup logging based on command line arguments."""
    output_level = arguments["--output-level"] or "default"
    log_file = arguments.get("--log-file")
    log_categories = arguments.get("--log-categories")

    log_level = _get_log_level_from_output(output_level)
    allowed_categories = _process_log_categories(log_categories)

    logger = init_logger(
        level=log_level, output_file=log_file, allowed_categories=allowed_categories
    )
    _log_initialization_info(logger, output_level, log_level, log_file, log_categories)

    return logger


def _get_log_level_from_output(output_level: str) -> LogLevel:
    """Convert output level to logger level."""
    level_mapping = {
        "nothing": LogLevel.NOTHING,
        "experiment": LogLevel.INFO,
        "default": LogLevel.INFO,
        "max_state": LogLevel.DEBUG,
        "debug": LogLevel.DEBUG,
    }
    return level_mapping.get(output_level, LogLevel.INFO)


def _process_log_categories(log_categories: Optional[str]) -> Optional[list]:
    """Process log categories from command line."""
    if log_categories is None:
        return None
    if log_categories.lower() in ["", "none"]:
        return []
    return [cat.strip().upper() for cat in log_categories.split(",") if cat.strip()]


def _log_initialization_info(
    logger,
    output_level: str,
    log_level: LogLevel,
    log_file: Optional[str],
    log_categories: Optional[str],
) -> None:
    """Log initialization information."""
    logger.info(
        "PoET logging system initialized",
        LogCategory.GENERAL,
        output_level=output_level,
        log_level=log_level.value,
        log_file=log_file,
        log_categories=log_categories,
    )

    logger.debug(
        "System information:",
        LogCategory.GENERAL,
        python_version=sys.version,
        platform=sys.platform,
        working_directory=os.getcwd(),
    )


def create_config(arguments: dict) -> Config:
    """Create configuration from command line arguments."""
    logger = get_logger()

    log_categories = arguments.get("--log-categories")
    if log_categories is not None and log_categories.lower() in ["", "none"]:
        log_categories = ""

    config = Config(
        property_file=arguments["--property"],
        trace_file=arguments["--trace"],
        reduce_enabled=bool(arguments["--reduce"]),
        visual_enabled=bool(arguments["--visual"]),
        output_level=arguments["--output-level"] or "default",
        log_file=arguments.get("--log-file"),
        log_categories=log_categories,
    )

    _log_config_creation(logger, config)
    return config


def _log_config_creation(logger, config: Config) -> None:
    """Log configuration creation details."""
    # Display configuration info messages as requested
    print("INFO: PoET Runtime Verification Starting")
    print(f"INFO: Property File: {config.property_file}")
    print(f"INFO: Trace File: {config.trace_file}")
    print(f"INFO: Output Level: {config.output_level}")
    print(f"INFO: Reduce Mode: {config.reduce_enabled}")
    print(f"INFO: Visual Output: {config.visual_enabled}")
    print(f"INFO: Trace Validation: {getattr(config, 'validate_enabled', False)}")

    logger.info(
        "Configuration created",
        LogCategory.GENERAL,
        property_file=config.property_file,
        trace_file=config.trace_file,
        reduce_enabled=config.reduce_enabled,
        visual_enabled=config.visual_enabled,
        output_level=config.output_level,
    )

    logger.debug(
        "Detailed configuration:",
        LogCategory.GENERAL,
        config_dict=config.get_log_config(),
    )


def handle_execution_error(error: Exception, logger) -> None:
    """Handle execution errors with detailed logging."""
    logger.error(
        f"PoET execution failed: {error}",
        LogCategory.ERROR,
        error_type=type(error).__name__,
        error_message=str(error),
    )

    _log_traceback(logger)
    _print_user_error_message(error, logger)


def _log_traceback(logger) -> None:
    """Log full traceback for debugging."""
    tb_lines = traceback.format_exc().split("\n")
    logger.debug("Full traceback:", LogCategory.ERROR)
    for line in tb_lines:
        if line.strip():
            logger.debug(f"  {line}", LogCategory.ERROR)


def _print_user_error_message(error: Exception, logger) -> None:
    """Print user-friendly error message."""
    print(f"ERROR: {error}")

    config_log_level = getattr(logger, "level", LogLevel.INFO)
    if config_log_level == LogLevel.DEBUG:
        print("\nFull traceback:")
        traceback.print_exc()
    else:
        print("Run with --output-level=debug for detailed error information.")


def log_execution_summary(logger, monitor: Optional[PoETMonitor] = None) -> None:
    """Log execution summary and statistics."""
    logger.info("PoET execution completed", LogCategory.GENERAL)

    if monitor:
        _log_monitor_statistics(logger, monitor)

    logger.print_summary()


def _log_monitor_statistics(logger, monitor: PoETMonitor) -> None:
    """Log monitor execution statistics."""
    try:
        stats = monitor.get_execution_stats()

        logger.info(
            "Execution statistics:",
            LogCategory.PERFORMANCE,
            events_processed=stats.get("events_processed", 0),
            events_queued=stats.get("events_queued", 0),
            total_states=stats.get("total_states", 0),
        )

        perf_metrics = stats.get("performance_metrics")
        if perf_metrics:
            avg_time = perf_metrics.get("avg_event_processing_time_seconds", 0)
            logger.performance("Event processing metrics", avg_time, "s")

    except Exception as e:
        logger.warn(
            f"Could not retrieve execution statistics: {e}", LogCategory.PERFORMANCE
        )


def run_poet_monitor(config: Config, logger) -> PoETMonitor:
    """Run the PoET monitor with given configuration."""
    logger.info("Initializing PoET monitor", LogCategory.GENERAL)
    monitor = PoETMonitor(config)

    logger.info("Starting PoET execution", LogCategory.GENERAL)
    logger.start_timer("total_application_runtime")

    monitor.run()

    total_runtime = logger.end_timer("total_application_runtime")
    logger.performance("Total application runtime", total_runtime, "s")

    return monitor


def should_suppress_summary(monitor: Optional[PoETMonitor]) -> bool:
    """Check if execution summary should be suppressed."""
    if not monitor:
        return False

    config = getattr(monitor, "config", None)
    return (
        config
        and config.is_max_state
        and config.log_categories is not None
        and len(config.log_categories) == 0
    )


def main() -> None:
    """Main entry point for the PoET application."""
    arguments = docopt(__doc__)
    logger = setup_logging(arguments)

    # Don't show the banner or section headers for cleaner INFO output
    logger.info("PoET: Property-oriented Event Trace Monitor", LogCategory.GENERAL)

    monitor = None
    exit_code = 0

    try:
        validate_arguments(arguments)
        config = create_config(arguments)
        monitor = run_poet_monitor(config, logger)

    except KeyboardInterrupt:
        logger.info("PoET execution interrupted by user", LogCategory.GENERAL)
        print("\nExecution interrupted by user")
        exit_code = 130

    except SystemExit as e:
        exit_code = e.code if hasattr(e, "code") else 1
        if exit_code != 0:
            logger.error(f"PoET exited with code {exit_code}", LogCategory.ERROR)

    except Exception as e:
        handle_execution_error(e, logger)
        exit_code = 1

    finally:
        if not should_suppress_summary(monitor):
            log_execution_summary(logger, monitor)

        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
