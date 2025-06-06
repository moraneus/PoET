# PoET: Partial Order Execution Tracer

```
██████╗  ██████╗ ███████╗████████╗
██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝
██████╔╝██║   ██║█████╗     ██║   
██╔═══╝ ██║   ██║██╔══╝     ██║   
██║     ╚██████╔╝███████╗   ██║   
╚═╝      ╚═════╝ ╚══════╝   ╚═╝   
        Partial Order Execution Tracer
```

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Tool-orange.svg)]()

## Overview

**PoET (Partial Order Execution Tracer)** is a sophisticated runtime verification tool for concurrent and distributed systems. Built on solid theoretical foundations from academic research, PoET monitors execution traces against formal specifications written in **PCTL (Past Computation Tree Logic)**.

Unlike traditional approaches that use interleaving semantics, PoET embraces **partial order semantics** to construct a branching structure of global states (frontiers) from distributed system executions. This enables precise verification of temporal properties that are naturally expressed in terms of causality and concurrency.

### Key Capabilities

- 🔍 **Runtime Verification**: Monitor system executions against formal PCTL specifications
- 🌐 **Partial Order Semantics**: Native support for concurrent and distributed system behaviors  
- ⏱️ **Vector Clock Analysis**: Fidge-Mattern vector clocks for precise event ordering
- 📊 **State Space Exploration**: Complete exploration of valid concurrent interleavings
- 🎨 **Visual Analysis**: Interactive state graph generation with property satisfaction highlighting
- ⚡ **Performance Optimized**: Efficient algorithms with optional state space reduction

## Installation

### Prerequisites

**PoET** requires Python 3.12 or higher. Verify your installation:

```bash
python --version  # Should output Python 3.12.x or higher
```

### Quick Setup

1. **Clone the repository** (or download the source code):
   ```bash
   git clone <repository-url>
   cd PoET
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Unix/macOS)
   source venv/bin/activate
   
   # Activate (Windows)
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies

PoET relies on several key libraries:
- **PLY (Python Lex-Yacc)**: PCTL parser generation
- **Graphviz**: State diagram visualization  
- **Colorama**: Colored console output
- **Pillow**: Image processing for animations
- **CairoSVG**: SVG to PNG conversion

## Usage

### Basic Command Structure

```bash
python poet.py --property=<property_file> --trace=<trace_file> [options]
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --property` | PCTL property file (required) | - |
| `-t, --trace` | JSON trace file (required) | - |
| `-r, --reduce` | Enable state space reduction | disabled |
| `-v, --visual` | Generate visual state graphs | disabled |
| `--output-level` | Output verbosity level | `default` |
| `--log-file` | Write logs to file | none |
| `--log-categories` | Filter log categories | all |

### Output Levels

- **`nothing`**: Suppress all non-error output
- **`experiment`**: Minimal output for benchmarks
- **`default`**: Standard operational messages  
- **`max_state`**: Global state summaries after each event
- **`debug`**: Maximum detailed output for developers

### Quick Start Example

```bash
# Basic verification
python poet.py -p property.pctl -t trace.json

# With visualization and debug output
python poet.py -p property.pctl -t trace.json --visual --output-level=debug

# Performance benchmarking
python poet.py -p property.pctl -t trace.json --output-level=experiment --reduce
```

## Input Formats

### PCTL Property Files

Properties are specified using **Past Computation Tree Logic (PCTL)**, a branching-time temporal logic with past operators.

**Example property file** (`property.pctl`):
```
EP(ready & confirmed)
```

### Trace Files

Traces are JSON files describing distributed system executions with vector clocks.

**Example trace file** (`trace.json`):
```json
{
  "processes": 3,
  "process_names": ["Client", "Server", "Database"],
  "events": [
    ["client_start", ["P1"], ["init", "ready"], [1, 0, 0]],
    ["server_req", ["P2"], ["confirmed"], [0, 1, 0]], 
    ["db_query", ["P3"], ["data_ready"], [0, 0, 1]],
    ["sync_point", ["P1", "P2"], ["synchronized"], [2, 2, 0]]
  ]
}
```

#### Trace Format Specification

| Field | Type | Description |
|-------|------|-------------|
| `processes` | `int` | Total number of processes in the system |
| `process_names` | `list[str]` | Optional human-readable process names |
| `events` | `list` | Sequence of events in chronological order |

#### Event Format

Each event is a 4-tuple: `[name, processes, propositions, vector_clock]`

- **`name`** (`str`): Unique event identifier
- **`processes`** (`list[str]`): Participating processes (e.g., `["P1"]`, `["P1", "P2"]`)
- **`propositions`** (`list[str]`): Atomic propositions that become true
- **`vector_clock`** (`list[int]`): Fidge-Mattern vector clock values

## PCTL Specification Language

### Grammar

```bnf
<formula> ::= <proposition>
            | <formula> & <formula>           (* conjunction *)
            | <formula> | <formula>           (* disjunction *)
            | <formula> -> <formula>          (* implication *)
            | <formula> <-> <formula>         (* biconditional *)
            | ! <formula>                     (* negation *)
            | A(<formula> S <formula>)        (* universal since *)
            | E(<formula> S <formula>)        (* existential since *)
            | AP <formula>                    (* always previously *)
            | EP <formula>                    (* exists previously *)
            | AH <formula>                    (* always historically *)
            | EH <formula>                    (* exists historically *)
            | AY <formula>                    (* always yesterday *)
            | EY <formula>                    (* exists yesterday *)
            | (<formula>)                     (* parentheses *)
            | TRUE | FALSE                    (* constants *)

<proposition> ::= [a-zA-Z_][a-zA-Z0-9_'\.]*  (* identifiers *)
```

### Temporal Operators

| Operator | Semantics | Intuitive Meaning |
|----------|-----------|-------------------|
| `EP φ` | ∃path: φ held previously | "φ happened sometime in the past" |
| `AP φ` | ∀paths: φ held previously | "φ held in all past states" |
| `EY φ` | ∃path: φ held yesterday | "φ held in some immediate predecessor" |
| `AY φ` | ∀paths: φ held yesterday | "φ held in all immediate predecessors" |
| `EH φ` | ∃path: φ always held | "φ held continuously in some path" |
| `AH φ` | ∀paths: φ always held | "φ held continuously in all paths" |
| `E(φ S ψ)` | ∃path: φ since ψ | "ψ occurred, then φ held until now" |
| `A(φ S ψ)` | ∀paths: φ since ψ | "In all paths: ψ occurred, then φ held" |

### Example Properties

```pctl
// Safety: No deadlock detected
AH(!deadlock)

// Liveness: Request eventually confirmed  
EP(request -> EP(confirmed))

// Ordering: Initialization before operation
EP(initialized) -> AH(initialized -> !operation | EP(operation))

// Mutual exclusion: At most one in critical section
AH(!(critical_p1 & critical_p2))

// Response property: Every request gets a response
AH(request -> EP(response))
```

## Understanding the Output

### State Graph Visualization

When using `--visual`, PoET generates SVG state diagrams showing:

- **Gray nodes**: States that don't satisfy the property
- **Blue nodes**: States that satisfy the property  
- **Edges**: State transitions labeled with triggering events
- **Node labels**: State names and active propositions

### Console Output Modes

**Default Mode**:
```
INFO: Property: EP(ready & confirmed)
INFO: Parsed formula: EP((ready & confirmed))
[FINAL VERDICT]: TRUE
```

**Max State Mode**:
```
Initial:[P1:0,P2:0,P3:0] → state=S0, props=[], verdict=FALSE ❌
client_start:[P1:1,P2:0,P3:0] → state=S1, props=[init,ready], verdict=FALSE ❌
server_req:[P1:1,P2:1,P3:0] → state=S3, props=[confirmed,init,ready], verdict=TRUE ✅
```

**Debug Mode**: Includes detailed state exploration, frontier calculations, and PCTL evaluation traces.

## Advanced Features

### State Space Reduction

The `--reduce` flag enables automatic pruning of disabled states that no longer affect the verification verdict:

```bash
python poet.py -p property.pctl -t trace.json --reduce
```

### Concurrent Event Handling

PoET automatically detects concurrent events using vector clock analysis and explores alternative interleavings to ensure complete verification coverage.

### Performance Monitoring

Use `--output-level=experiment` for benchmark-friendly output:
```
[TOTAL_EVENTS]: 1247
[TOTAL_STATES]: 89
[MAX_EVENT]: 0.023s for event sync_operation
[FINAL VERDICT]: TRUE
```

### Logging and Debugging

Fine-grained logging control:
```bash
# Log only state and PCTL categories to file
python poet.py -p prop.pctl -t trace.json --log-file=debug.log --log-categories=STATE,PCTL

# Enable all logging categories
python poet.py -p prop.pctl -t trace.json --log-file=debug.log --log-categories=

# Disable all logging (performance mode)
python poet.py -p prop.pctl -t trace.json --log-categories=none
```

## Architecture Overview

PoET implements the sliding window algorithm from academic research on partial order runtime verification:

```
Event Stream → Vector Clock Manager → State Manager → PCTL Evaluator → Verdict
     ↓              ↓                      ↓              ↓
 JSON Parser    Fidge-Mattern         Frontier        AST-based
               Deliverability       Construction     Evaluation
```

### Core Components

- **Event Processor**: Validates and initializes events from trace data
- **Vector Clock Manager**: Manages event ordering using Fidge-Mattern clocks
- **State Manager**: Constructs global states and manages transitions
- **PCTL Parser**: PLY-based parser for temporal logic formulas
- **AST Evaluator**: Recursive evaluation engine for PCTL expressions
- **Visualization Engine**: Graphviz-based state diagram generation

## Examples and Use Cases

### Distributed Database Verification

```json
{
  "processes": 3,
  "process_names": ["Client", "Primary", "Replica"], 
  "events": [
    ["begin_txn", ["P1"], ["txn_active"], [1, 0, 0]],
    ["write_primary", ["P2"], ["data_written"], [1, 1, 0]],
    ["replicate", ["P2", "P3"], ["replicated"], [1, 2, 1]],
    ["commit", ["P1", "P2"], ["committed"], [2, 3, 1]]
  ]
}
```

Property: `AH(committed -> EP(replicated))`  
*"Commits only happen after replication"*

### Mutual Exclusion Protocol

```json
{
  "processes": 2,
  "events": [
    ["request_cs", ["P1"], ["requesting"], [1, 0]],
    ["grant_cs", ["P1"], ["in_critical"], [2, 0]], 
    ["release_cs", ["P1"], ["released"], [3, 0]],
    ["request_cs", ["P2"], ["requesting"], [3, 1]],
    ["grant_cs", ["P2"], ["in_critical"], [3, 2]]
  ]
}
```

Property: `AH(!(in_critical & requesting))`  
*"Mutual exclusion: never both in critical section"*

## Troubleshooting

### Common Issues

**Import Errors**: Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

**Graphviz Not Found**: Install Graphviz system package:
```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz

# Windows
# Download from: https://graphviz.org/download/
```

**Memory Issues**: Use `--reduce` for large traces:
```bash
python poet.py -p property.pctl -t large_trace.json --reduce
```

**Parser Errors**: Check PCTL syntax:
```bash
# Valid
EP(ready & confirmed)

# Invalid - missing parentheses
EP ready & confirmed
```

### Performance Tips

1. **Use state reduction** for large state spaces: `--reduce`
2. **Filter log categories** for better performance: `--log-categories=ERROR`
3. **Use experiment mode** for benchmarking: `--output-level=experiment`
4. **Optimize trace format** by minimizing vector clock dimensions

## Contributing

PoET is a research tool developed for academic and educational purposes. Contributions are welcome!

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run specific test scenarios
python -m pytest tests/integration_tests/test_poet_scenario.py::test_poet_scenario[EP_01_SIMPLE_TRUE]
```

### Testing

PoET includes comprehensive test suites:
- **Unit tests**: Parser, AST evaluation, vector clocks
- **Integration tests**: End-to-end scenarios with various PCTL properties
- **Performance tests**: Benchmarking with large traces

## Academic Background

PoET implements algorithms from research on runtime verification of distributed systems using partial order semantics. The tool bridges theoretical computer science with practical verification needs.

### Key References

- **Partial Order Semantics**: Based on Mazurkiewicz traces and event structures
- **Vector Clocks**: Fidge-Mattern algorithm for distributed systems
- **PCTL Logic**: Past-time Computation Tree Logic for branching-time properties
- **Runtime Verification**: Online monitoring of system executions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use PoET in academic work, please cite:
```bibtex
@misc{poet2024,
  title={PoET: Partial Order Execution Tracer for Runtime Verification},
  author={[Authors]},
  year={2024},
  url={https://github.com/[repository]}
}
```

---

**PoET** - Bringing theoretical rigor to practical distributed system verification.