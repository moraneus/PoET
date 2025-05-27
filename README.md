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

**PoET (Partial Order Execution Tracer)** is a runtime verification (RV) tool designed to monitor and verify executions of concurrent or distributed systems against formal specifications. Developed in Python 3.12, PoET analyzes a given execution trace, which represents a partial order of events, by constructing a graph of global states (frontiers). It then checks this graph against properties specified in **PCTL (Past Computation Tree Logic)**, a temporal logic with past operators.

In concurrent or distributed systems, non-deterministic interactions can lead to numerous potential execution paths. PoET focuses on a single observed partial order execution and evaluates properties based on the branching structure of consistent global states derivable from it. This allows for the verification of complex temporal behaviors and the detection of specification violations within the observed execution.

## Features

- **Runtime Verification (RV):** Verifies execution traces against PCTL specifications.
- **Partial Order Semantics:** Interprets executions based on partial order between events, focusing on the structure of global states (frontiers).
- **PCTL Specification:** Uses Past Computation Tree Logic (PCTL) for expressing temporal properties with past operators.
- **Vector Clock Based Analysis:** Utilizes vector clocks associated with events to manage and understand the partial order.
- **Graphical Representation:** Can generate visualizations of the explored global state graph (frontiers and transitions), with states colored based on property satisfaction.
- **Reduce Mode Functionality:** Offers an optional "Reduce mode" to optimize the state graph by removing redundant states that no longer affect future verdicts.

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
  poet.py --property=<property> --trace.json.json.json=<trace.json.json.json> [--reduce] [--debug] [--visual] [--experiment]
  poet.py -p <property> -t <trace.json.json.json> [-r] [-d] [-v] [-e]
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
The trace file must be a JSON formatted file describing the events, the number of processes, and vector clocks.
```json
{
  "processes": 2,
  "events": [
    ["e1", ["P1"], ["a"], [1, 0]],
    ["e2", ["P1"], ["b"], [2, 0]],
    ["e3", ["P1", "P2"], ["a", "c"], [3, 1]],
    ["e4", ["P2"], ["b"], [3, 2]]
  ]
}
```
##### Key Descriptions:
* `processes` (int): The total number of processes in the distributed system.
* `events` (list): A list of recorded events. Each event is an array:
  * **event_identifier** (str): e.g., `"e1"`. 
  * **involved_processes** (list of str): Processes participating in this event, e.g., `["P1"]`, `["P1", "P2"]`.
  * **propositions** (list of str): Atomic propositions true in the local state(s) of the involved process(es) after this event occurs. e.g., `["a"]`, `["a", "c"]`. 
  * **vector_clock** (list of int): The vector clock associated with this event. The length of the vector clock must match the processes count. e.g., `[1, 0]` for a 2-process system.

For example, `["e3", ["P1", "P2"], ["a", "c"], [3, 1]]` denotes event `e3` involves processes `P1` and `P2`, makes propositions a (for P1) and `c` (for P2) `true`, and has a vector clock `[3, 1]`.

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