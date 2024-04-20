# PoET (Partial Order Execution Tracer) Tool
```
██████╗          ███████╗████████╗
██╔══██╗ ██████╗ ██╔════╝╚══██╔══╝
██████╔╝██╔═══██╗█████╗     ██║   
██╔═══╝ ██║   ██║██╔══╝     ██║   
██║     ╚██████╔╝███████╗   ██║   
╚═╝      ╚═════╝ ╚══════╝   ╚═╝ 
Partial Order Execution Tracer
```
## Description

PoET is a proof-of-concept tool developed to analyze and evaluate all equivalent executions of concurrent or distributed systems based on provided execution traces. Written in Python 3.12, **PoET** aims to explore various possible interleavings of events and processes that can occur in these systems, starting from a specific execution sequence.

In concurrent or distributed environments, processes or threads operate independently, often interacting via shared resources or communication channels. These interactions are inherently non-deterministic, leading to multiple potential execution sequences. **PoET** takes an initial execution trace as input and determines all possible equivalent executions that preserve the causal relationships and dependencies among the events and processes involved.

This analysis helps identify potential synchronization issues like race conditions or deadlocks, providing a comprehensive view of the system's behavior under different scenarios.

## Features

- **Equivalence Analysis:** Explore all possible interleavings of events and detect potential issues in concurrent executions.
- **Graphical Representation:** Visualize the state space or DAG of the system's possible executions.
- **Dual Mode Functionality:** Operate in either Normal mode, which retains all nodes in the graph, or Reduce mode, which optimizes the graph by eliminating nodes without successors.

## Installation Guide

### Prerequisites

Ensure you have Python 3.12 installed on your machine. You can verify this by running:
```bash
python --version
```
### Setting Up a Virtual Environment
Using a virtual environment for Python projects is recommended as it keeps dependencies required by 
different projects separate. To set up and activate a virtual environment, follow these steps:
1. **Install virtualenv**
```bash 
# Install virtualenv if it's not already installed
pip install virtualenv

# Create a virtual environment
virtualenv venv
```
2. **Activate the virtual environment**
   1. On Windows:
        ```commandline
        venv\Scripts\activate
        ```
   2. On Unix or MacOS:
        ```   
        source venv/bin/activate
        ```
### Installing Dependencies
**PoET** requires several Python packages to function properly. 
These dependencies are listed in the `requirements.txt` file and can be installed using pip:
```bash
pip install -r requirements.txt
```

## Usage

To operate **PoET**, execute the following command with the required options:

```bash
  poet.py --property=<property> --trace.json.json=<trace.json.json> [--reduce] [--debug] [--visual] [--experiment]
  poet.py -p <property> -t <trace.json.json> [-r] [-d] [-v] [-e]
```

### Command Line Options
* `-p <property>`, `--property=<property>`: Specifies the filename that contains the property\specification to be checked. This is a mandatory argument.
* `-t <trace>`, `--trace=<trace>`: Specifies the filename that contains the trace to be analyzed. This is also a mandatory argument.
* `-r`, `--reduce`: Enables the reduce mode, which optimizes the graph representation by pruning unnecessary nodes. This is an optional flag.
* `-d`, `--debug`: Activates debug mode, providing detailed logs that can assist in diagnosing and understanding the tool's operation. This is an optional flag.
* `-v`, `--visual`: Enable visual output (state graphs files). This is an optional flag.
* `-e`, `--experiment`: Disable all print due to experiment benchmarks. This is an optional flag.
* `-h`, `--help`: Displays the help message and exits, useful for quick reference on command usage.

#### Property File (`<property>`)
The property file specifies the temporal properties that the trace must satisfy. It contains temporal logic expressions that define the expected behavior of the system under analysis based on the events and states captured in the trace file. For more details, refer to the specification language section provided below.

#### Trace File (`<trace>`)
The trace file should be in a specific JSON format that describes the events occurring within the system during execution. Here is an example of how the trace file should be structured:

```json
{
  "processes": 2,
  "events": [
    ["e1", ["P1"], ["a"]],
    ["e2", ["P1"], ["b"]],
    ["e3", ["P1", "P2"], ["a", "c"]],
    ["e4", ["P2"], ["b"]]
  ]
}
```
##### Key Descriptions:
* `processes`: Indicates the number of processes involved in the trace. In the example above, there are two processes involved.
* `events`: Lists the events recorded during the trace. Each event is represented as an array containing:
  * The event identifier (e.g., `e1`)
  * The process or processes (e.g., `P1`, `P2`) to which the event belongs.
  * An array of propositions that describe the event (e.g., `a`, `b`, `c`). 

For example, `["e3", ["P1", P2"], ["a", "c"]]` denotes that event `e3` involves processes `P1` and `P2` and is linked to propositions `a` and `c`.

## **PoET** Specification Logic
### Grammar
```
<formula> ::= <proposition>
            | <formula> & <formula>
            | <formula> | <formula>
            | <formula> -> <formula>
            | <formula> <-> <formula>
            | ! <formula>
            | A(<formula> S <formula>)
            | E(<formula> S <formula>)
            | AP <formula>
            | EP <formula>
            | AH <formula>
            | EH <formula>
            | AY <formula>
            | EY <formula>
            | (<formula>)
            | TRUE
            | FALSE

<proposition> ::= string
```

### Formulas
The different formulas <formula> have the following intuitive meaning:
```commandline
TRUE, FALSE     : Boolean truth and falsehood 
p & q           : p and q
p | q           : p or q
p -> q          : p implies q
p <-> q         : p iff q
! p             : not p
E(p S q)        : Exist path where p since q (q was true in the past, and since then, including that point in time, p has been true)
E(p S q)        : Forall paths p since q
EP p            : Exist path where p previously happened
AP p            : Forall paths p previously happened
EH p            : Exist path where p historically (always in the past) happened
EH p            : Forall paths p historically happened
EY p            : Exist path where p happened in the pervious step
AY p            : Forall paths p happened in the pervious step
```

## Graphical Representation
**PoET** yields a set of SVG images as its output, which describe the graph (state space) 
construction after each event. Each node in the graph corresponds to a specific state of the 
system, with the state name displayed at the top and the aggregated propositions that 
hold for that state listed below. The state is determined by the combination of process 
states and event occurrences.
The blue nodes or states are the ones that satisfy the specified property. The edges in 
the graph represent the transitions between states based on the execution of events.

![graph.gif](doc%2Fimages%2Fgraph.gif)

In this example, the graph is visually represented as a directed graph, with nodes 
representing the states and edges representing the transitions between states. 
The propositions that hold for each state are listed within the corresponding node. 
The blue coloring of certain nodes indicates that they satisfy the specified property.

By examining the graphical representation, you can gain insights into the behavior of 
the system and identify the states that meet the desired property. The visual representation 
aids in understanding the flow of events and the relationships between different states 
in the system.