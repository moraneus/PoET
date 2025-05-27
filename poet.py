# # """
# # Usage:
# #   poet.py --property=<property> --trace.json.json.json=<trace.json.json.json> [--reduce] [--debug] [--visual] [--experiment]
# #   poet.py -p <property> -t <trace.json.json.json> [-r] [-d] [-v] [-e]
# #
# # Options:
# #   -p <property>, --property=<property>  Property filename (mandatory)
# #   -t <trace.json.json.json>, --trace.json.json.json=<trace.json.json.json>           Trace filename (mandatory)
# #   -r, --reduce                          Enable reduce (optional)
# #   -d, --debug                           Enable debug mode (optional)
# #   -v, --visual                          Enable visual output (optional)
# #   -e, --experiment                      Disable all print due to experiment benchmarks
# #   -h, --help                            Show this help message and exit
# # """
# # from typing import List, Dict, Tuple, Set
# # from docopt import docopt
# # import time
# #
# # from graphics.automaton import Automaton
# # from graphics.prints import Prints
# # from model.event import Event
# # from model.process import Process
# # from model.process_modes import ProcessModes
# # from model.state import State
# # from parser.ast import Formula
# # from parser.parser import parse
# #
# # from utils.generic_utils import GenericUtils
# #
# #
# # def main(i_property: str, i_trace: str, i_reduce: bool, i_debug: bool, i_visual: bool, i_experiment: bool):
# #     if not i_experiment:
# #         Prints.banner()
# #
# #     # Read property file
# #     raw_prop = GenericUtils.read_property(i_property)
# #     prop = parse(raw_prop)
# #     Prints.raw_property(''.join(raw_prop))
# #     Prints.compiled_property(prop)
# #
# #     # Read trace.json.json.json file
# #     trace_data = GenericUtils.read_json(i_trace)
# #     trace = trace_data['events']
# #     num_of_processes = trace_data['processes']
# #
# #     # Initialize processes structure
# #     processes = initialize_processes(num_of_processes)
# #
# #     # Initialize first state
# #     formulas = Formula.collect_formulas(prop)
# #     states = initialize_states(num_of_processes, formulas)
# #     res = prop.eval(state=states[0])
# #     states[0].value = res
# #
# #     # Used for measure the maximum time it takes process the events
# #     if i_experiment:
# #         Prints.total_events(len(trace))
# #         events_processing_time = []
# #
# #     for event_data in trace:
# #
# #         # Used for measure the maximum time it takes process the events
# #         if i_experiment:
# #             start_time = time.time()
# #
# #         event = initialize_event(event_data, num_of_processes)
# #         Prints.event(event)
# #
# #         # Attach events to the processes they belong
# #         attach_event_to_process(event, processes)
# #
# #         # The new state are the cuts
# #         new_states, closed_events = find_new_states(states, event)
# #
# #         # Update closed events' mode
# #         for finish_event, index in filter(None, closed_events):
# #             finish_event.update_mode(ProcessModes.CLOSED, index)
# #
# #         # Checking for states that couldn't yield another successors
# #         for state in states:
# #             if all(State.is_proc_closed(state.processes, i) for i in range(len(state.processes))):
# #                 state.enabled = False
# #
# #         # For the last states in the cut we check for internal edges
# #         for i, state in enumerate(new_states):
# #             state.edges_completion(new_states[i:], processes)
# #
# #         # Evaluate new states
# #         evaluate(new_states, prop)
# #
# #         if i_debug:
# #             Prints.display_states(new_states, i_title="NEW", i_debug=i_debug)
# #
# #         if i_reduce:
# #             for i in range(len(states) - 1, -1, -1):
# #                 if not states[i].enabled:
# #                     Prints.del_state(states[i], i_debug)
# #                     states[i] = None
# #                     del states[i]
# #
# #         states.extend(new_states)
# #         if i_debug and i_visual:
# #             create_automaton(states)
# #
# #         # Measures the maximum time taken to process events
# #         if i_experiment:
# #             current_time = time.time() - start_time
# #             events_processing_time.append(current_time)
# #
# #     if not i_experiment:
# #         Prints.display_states(states, i_title="ALL", i_debug=i_debug)
# #     else:
# #         Prints.total_states(len(states))
# #         max_time, max_index = max((t, idx) for idx, t in enumerate(events_processing_time))
# #         min_time, min_index = min((t, idx) for idx, t in enumerate(events_processing_time))
# #         avg_time = sum(events_processing_time) / len(events_processing_time)
# #         Prints.events_time((max_time, max_index), (min_time, min_index), avg_time)
# #
# #     if i_visual:
# #         create_automaton(states)
# #         if i_debug:
# #             Automaton.make_gif('output')
# #
# #
# # def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
# #     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(0, i_num_of_processes)}
# #
# #
# # def initialize_states(i_num_of_processes: int, i_formulas: List[str]):
# #     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
# #
# #
# # def initialize_event(i_event_data: List[str | List[str]], i_num_of_processes: int):
# #     event_name = i_event_data[0]
# #     event_processes = Process.distribute_processes(i_event_data[1], i_num_of_processes)
# #     propositions = i_event_data[2]
# #     return Event(i_name=event_name, i_processes=event_processes, i_propositions=propositions)
# #
# #
# # def attach_event_to_process(i_event: Event, i_processes: Dict[str, Process]):
# #     for p in i_event.processes:
# #         if p in i_processes:
# #             i_processes[p].add_event(i_event)
# #
# #
# # def find_new_states(i_states: List[State], i_event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
# #     # The new states are the cut slices
# #     new_states = []
# #     closed_events = set()
# #     for state in i_states:
# #         if state.enabled:
# #             new_state, closed_event = state | i_event
# #             if new_state is not None:
# #                 new_states.append(new_state)
# #                 closed_events.update(closed_event)
# #
# #     return new_states, closed_event
# #
# #
# # def evaluate(i_new_states: List[State], i_prop: Formula):
# #     for new_state in i_new_states:
# #         res = i_prop.eval(state=new_state)
# #         new_state.value = res
# #
# #
# # def create_automaton(i_states: List[State]):
# #     # Preparing for automaton creation
# #     state_names, transitions = set(), []
# #     for state in i_states:
# #         state_names.add(state.name)
# #         for pred_name, (event, _) in state.successors.items():
# #             transitions.append((pred_name, state.name, getattr(event, 'name')))
# #
# #     Automaton.create_automaton(i_states, transitions)
# #
# #
# # if __name__ == '__main__':
# #     arguments = docopt(__doc__)
# #
# #     property_value = arguments['--property']
# #     trace_value = arguments['--trace.json.json.json']
# #     reduce_enabled = arguments['--reduce']
# #     debug_enabled = arguments['--debug']
# #     visual_enabled = arguments['--visual']
# #     experiment_mode = arguments['--experiment']
# #
# #     main(property_value, trace_value, reduce_enabled, debug_enabled, visual_enabled, experiment_mode)
#
# # """
# # Usage:
# #   poet.py --property=<property> --trace.json.json.json=<trace.json.json.json> [--reduce] [--debug] [--visual] [--experiment]
# #   poet.py -p <property> -t <trace.json.json.json> [-r] [-d] [-v] [-e]
# #
# # Options:
# #   -p <property>, --property=<property>          Property filename (mandatory)
# #   -t <trace.json.json.json>, --trace.json.json.json=<trace.json.json.json>   Trace filename (mandatory)
# #   -r, --reduce                                  Enable reduce (optional)
# #   -d, --debug                                   Enable debug mode (optional)
# #   -v, --visual                                  Enable visual output (optional)
# #   -e, --experiment                              Disable all print due to experiment benchmarks
# #   -h, --help                                    Show this help message and exit
# # """
# # from typing import List, Dict, Tuple, Set
# # from docopt import docopt
# # import time
# #
# # from graphics.automaton import Automaton
# # from graphics.prints import Prints
# # from model.event import Event
# # from model.process import Process
# # from model.process_modes import ProcessModes
# # from model.state import State
# # from parser.ast import Formula
# # from parser.parser import parse
# #
# # from utils.generic_utils import GenericUtils
# #
# #
# # def get_origin_index(event: Event, expected_vc: List[int]) -> int:
# #     """
# #     Returns the origin index (0-based) for the event by scanning event.processes.
# #     It collects all elements that are strings starting with 'P' and selects the candidate
# #     for which the event's vector clock value equals expected_vc[i] + 1.
# #     If more than one qualifies, returns the smallest index.
# #     If none qualify, falls back to the smallest candidate.
# #     Defaults to 0 if no candidate is found.
# #     """
# #     candidate_indices = []
# #     for proc in event.processes:
# #         if isinstance(proc, str) and proc.startswith("P"):
# #             try:
# #                 candidate_indices.append(int(proc[1:]) - 1)
# #             except ValueError:
# #                 continue
# #     if not candidate_indices:
# #         return 0
# #
# #     eligible = [i for i in candidate_indices if event.vector_clock[i] == expected_vc[i] + 1]
# #     if eligible:
# #         return min(eligible)
# #     return min(candidate_indices)
# #
# #
# # def main(i_property: str, i_trace: str, i_reduce: bool, i_debug: bool, i_visual: bool, i_experiment: bool):
# #     if not i_experiment:
# #         Prints.banner()
# #
# #     # Read property file and compile it.
# #     raw_prop = GenericUtils.read_property(i_property)
# #     prop = parse(raw_prop)
# #     Prints.raw_property(''.join(raw_prop))
# #     Prints.compiled_property(prop)
# #
# #     # Read trace file (which now includes vector clocks as 4th element)
# #     trace_data = GenericUtils.read_json(i_trace)
# #     trace = trace_data['events']
# #     num_of_processes = trace_data['processes']
# #
# #     # Initialize processes and first state.
# #     processes = initialize_processes(num_of_processes)
# #     formulas = Formula.collect_formulas(prop)
# #     states = initialize_states(num_of_processes, formulas)
# #     res = prop.eval(state=states[0])
# #     states[0].value = res
# #
# #     # Setup for vector clock ordering.
# #     expected_vc = [0] * num_of_processes  # Expected vector clock for each process.
# #     holding_queue: List[Event] = []         # Buffer for out-of-order events.
# #
# #     if i_experiment:
# #         Prints.total_events(len(trace))
# #         events_processing_time = []
# #
# #     # Helper: Check if an event's vector clock is the next expected one for the given origin.
# #     def is_event_in_order(event_vc: List[int], expected_vc: List[int], origin_index: int) -> bool:
# #         if event_vc[origin_index] != expected_vc[origin_index] + 1:
# #             return False
# #         for j, (ev, exp) in enumerate(zip(event_vc, expected_vc)):
# #             if j != origin_index and ev > exp:
# #                 return False
# #         return True
# #
# #     # Helper: Process the event using existing logic.
# #     def process_event(event: Event):
# #         attach_event_to_process(event, processes)
# #         new_states, closed_events = find_new_states(states, event)
# #         for finish_event, index in filter(None, closed_events):
# #             finish_event.update_mode(ProcessModes.CLOSED, index)
# #         for state in states:
# #             if all(State.is_proc_closed(state.processes, i) for i in range(len(state.processes))):
# #                 state.enabled = False
# #         for i, state in enumerate(new_states):
# #             state.edges_completion(new_states[i:], processes)
# #         evaluate(new_states, prop)
# #         if i_debug:
# #             Prints.display_states(new_states, i_title="NEW", i_debug=i_debug)
# #         if i_reduce:
# #             for i in range(len(states) - 1, -1, -1):
# #                 if not states[i].enabled:
# #                     Prints.del_state(states[i], i_debug)
# #                     states[i] = None
# #                     del states[i]
# #         states.extend(new_states)
# #         if i_debug and i_visual:
# #             create_automaton(states)
# #
# #     # Helper: Flush the holding queue for events that are now in order.
# #     def flush_holding_queue():
# #         nonlocal expected_vc, holding_queue
# #         made_progress = True
# #         while made_progress:
# #             made_progress = False
# #             for evt in holding_queue[:]:
# #                 origin_idx = get_origin_index(evt, expected_vc)
# #                 if is_event_in_order(evt.vector_clock, expected_vc, origin_idx):
# #                     process_event(evt)
# #                     expected_vc[origin_idx] += 1
# #                     holding_queue.remove(evt)
# #                     made_progress = True
# #
# #     # Main event loop.
# #     for event_data in trace:
# #         if i_experiment:
# #             start_time = time.time()
# #
# #         event = initialize_event(event_data, num_of_processes)
# #         Prints.event(event)
# #
# #         # Determine origin index based on all candidate processes.
# #         origin_index = get_origin_index(event, expected_vc)
# #         if is_event_in_order(event.vector_clock, expected_vc, origin_index):
# #             process_event(event)
# #             expected_vc[origin_index] += 1
# #             flush_holding_queue()
# #         else:
# #             holding_queue.append(event)
# #
# #         if i_experiment:
# #             current_time = time.time() - start_time
# #             events_processing_time.append(current_time)
# #
# #     flush_holding_queue()
# #
# #     if not i_experiment:
# #         Prints.display_states(states, i_title="ALL", i_debug=i_debug)
# #     else:
# #         Prints.total_states(len(states))
# #         max_time, max_index = max((t, idx) for idx, t in enumerate(events_processing_time))
# #         min_time, min_index = min((t, idx) for idx, t in enumerate(events_processing_time))
# #         avg_time = sum(events_processing_time) / len(events_processing_time)
# #         Prints.events_time((max_time, max_index), (min_time, min_index), avg_time)
# #
# #     if i_visual:
# #         create_automaton(states)
# #         if i_debug:
# #             Automaton.make_gif('output')
# #
# #
# # def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
# #     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(0, i_num_of_processes)}
# #
# #
# # def initialize_states(i_num_of_processes: int, i_formulas: List[str]):
# #     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
# #
# #
# # def initialize_event(i_event_data: List[str | List[str]], i_num_of_processes: int):
# #     event_name = i_event_data[0]
# #     event_processes = Process.distribute_processes(i_event_data[1], i_num_of_processes)
# #     propositions = i_event_data[2]
# #     vector_clock = i_event_data[3] if len(i_event_data) > 3 else [0] * i_num_of_processes
# #     event = Event(i_name=event_name, i_processes=event_processes, i_propositions=propositions)
# #     event.vector_clock = vector_clock
# #     return event
# #
# #
# # def attach_event_to_process(i_event: Event, i_processes: Dict[str, Process]):
# #     for p in i_event.processes:
# #         if p in i_processes:
# #             i_processes[p].add_event(i_event)
# #
# #
# # def find_new_states(i_states: List[State], i_event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
# #     new_states = []
# #     closed_events = set()
# #     for state in i_states:
# #         if state.enabled:
# #             new_state, closed_event = state | i_event
# #             if new_state is not None:
# #                 new_states.append(new_state)
# #                 closed_events.update(closed_event)
# #     return new_states, closed_events
# #
# #
# # def evaluate(i_new_states: List[State], i_prop: Formula):
# #     for new_state in i_new_states:
# #         res = i_prop.eval(state=new_state)
# #         new_state.value = res
# #
# #
# # def create_automaton(i_states: List[State]):
# #     state_names, transitions = set(), []
# #     for state in i_states:
# #         state_names.add(state.name)
# #         for pred_name, (event, _) in state.successors.items():
# #             transitions.append((pred_name, state.name, getattr(event, 'name')))
# #     Automaton.create_automaton(i_states, transitions)
# #
# #
# # if __name__ == '__main__':
# #     arguments = docopt(__doc__)
# #
# #     property_value = arguments['--property']
# #     trace_value = arguments['--trace.json.json.json']
# #     reduce_enabled = arguments['--reduce']
# #     debug_enabled = arguments['--debug']
# #     visual_enabled = arguments['--visual']
# #     experiment_mode = arguments['--experiment']
# #
# #     main(property_value, trace_value, reduce_enabled, debug_enabled, visual_enabled, experiment_mode)
#
# # # poet.py
# #
# # """
# # Usage:
# #   poet.py --property=<property> --trace.json.json.json=<trace.json.json.json> [--reduce] [--debug] [--visual] [--experiment]
# #   poet.py -p <property> -t <trace.json.json.json> [-r] [-d] [-v] [-e]
# #
# # Options:
# #   -p <property>, --property=<property>          Property filename (mandatory)
# #   -t <trace.json.json.json>, --trace.json.json.json=<trace.json.json.json>   Trace filename (mandatory)
# #   -r, --reduce                                  Enable reduce (optional)
# #   -d, --debug                                   Enable debug mode (optional)
# #   -v, --visual                                  Enable visual output (optional)
# #   -e, --experiment                              Disable all print due to experiment benchmarks
# #   -h, --help                                    Show this help message and exit
# # """
# # from typing import List, Dict, Tuple, Set
# # from docopt import docopt
# # import time
# #
# # from graphics.automaton import Automaton
# # from graphics.prints import Prints
# # from model.event import Event
# # from model.process import Process
# # from model.process_modes import ProcessModes
# # from model.state import State
# # from parser.ast import Formula
# # from parser.parser import parse
# #
# # from utils.generic_utils import GenericUtils
# #
# #
# # def get_involved_indices(event: Event) -> List[int]:
# #     """
# #     Returns a list of indices (0-based) for all processes involved in the event.
# #     For each element in event.processes, if it is a string starting with "P",
# #     its index is computed from the numeric part.
# #     """
# #     indices = []
# #     for proc in event.processes:
# #         if isinstance(proc, str) and proc.startswith("P"):
# #             try:
# #                 indices.append(int(proc[1:]) - 1)
# #             except ValueError:
# #                 continue
# #     return indices
# #
# #
# # def is_event_in_order_multi(event_vc: List[int], expected_vc: List[int], involved: List[int]) -> bool:
# #     """
# #     For an event that involves multiple processes (given by indices in 'involved'),
# #     return True only if for every involved process, the event's vector clock equals
# #     expected_vc[i] + 1.
# #     """
# #     for i in involved:
# #         if event_vc[i] != expected_vc[i] + 1:
# #             return False
# #     return True
# #
# #
# # def main(i_property: str, i_trace: str, i_reduce: bool, i_debug: bool, i_visual: bool, i_experiment: bool):
# #     if not i_experiment:
# #         Prints.banner()
# #
# #     # Read and compile property.
# #     raw_prop = GenericUtils.read_property(i_property)
# #     prop = parse(raw_prop)
# #     Prints.raw_property(''.join(raw_prop))
# #     Prints.compiled_property(prop)
# #
# #     # Read trace file (trace events include vector clocks as 4th element)
# #     trace_data = GenericUtils.read_json(i_trace)
# #     trace = trace_data['events']
# #     num_of_processes = trace_data['processes']
# #
# #     # Initialize processes and the first state.
# #     processes = initialize_processes(num_of_processes)
# #     formulas = Formula.collect_formulas(prop)
# #     states = initialize_states(num_of_processes, formulas)
# #     res = prop.eval(state=states[0])
# #     states[0].value = res
# #
# #     # Setup for vector clock ordering:
# #     # For each process, expected_vc[i] is the last processed counter.
# #     expected_vc = [0] * num_of_processes
# #     holding_queue: List[Event] = []
# #
# #     if i_experiment:
# #         Prints.total_events(len(trace))
# #         events_processing_time = []
# #
# #     def flush_holding_queue():
# #         nonlocal expected_vc, holding_queue
# #         made_progress = True
# #         while made_progress:
# #             made_progress = False
# #             for evt in holding_queue[:]:
# #                 involved = get_involved_indices(evt)
# #                 if is_event_in_order_multi(evt.vector_clock, expected_vc, involved):
# #                     process_event(evt)
# #                     for i in involved:
# #                         expected_vc[i] = evt.vector_clock[i]
# #                     holding_queue.remove(evt)
# #                     made_progress = True
# #
# #     def process_event(event: Event):
# #         attach_event_to_process(event, processes)
# #         new_states, closed_events = find_new_states(states, event)
# #         for finish_event, index in filter(None, closed_events):
# #             finish_event.update_mode(ProcessModes.CLOSED, index)
# #         for state in states:
# #             if all(State.is_proc_closed(state.processes, i) for i in range(len(state.processes))):
# #                 state.enabled = False
# #         for i, state in enumerate(new_states):
# #             state.edges_completion(new_states[i:], processes)
# #         evaluate(new_states, prop)
# #         if i_debug:
# #             Prints.display_states(new_states, i_title="NEW", i_debug=i_debug)
# #         if i_reduce:
# #             for i in range(len(states) - 1, -1, -1):
# #                 if not states[i].enabled:
# #                     Prints.del_state(states[i], i_debug)
# #                     states[i] = None
# #                     del states[i]
# #         states.extend(new_states)
# #         if i_debug and i_visual:
# #             create_automaton(states)
# #
# #     # Main event loop with vector clock ordering.
# #     for event_data in trace:
# #         if i_experiment:
# #             start_time = time.time()
# #
# #         event = initialize_event(event_data, num_of_processes)
# #         Prints.event(event)
# #
# #         involved = get_involved_indices(event)
# #         if is_event_in_order_multi(event.vector_clock, expected_vc, involved):
# #             process_event(event)
# #             for i in involved:
# #                 expected_vc[i] = event.vector_clock[i]
# #             flush_holding_queue()
# #         else:
# #             holding_queue.append(event)
# #
# #         if i_experiment:
# #             current_time = time.time() - start_time
# #             events_processing_time.append(current_time)
# #
# #     flush_holding_queue()
# #
# #     if not i_experiment:
# #         Prints.display_states(states, i_title="ALL", i_debug=i_debug)
# #     else:
# #         Prints.total_states(len(states))
# #         max_time, max_index = max((t, idx) for idx, t in enumerate(events_processing_time))
# #         min_time, min_index = min((t, idx) for idx, t in enumerate(events_processing_time))
# #         avg_time = sum(events_processing_time) / len(events_processing_time)
# #         Prints.events_time((max_time, max_index), (min_time, min_index), avg_time)
# #
# #     if i_visual:
# #         create_automaton(states)
# #         if i_debug:
# #             Automaton.make_gif('output')
# #
# #
# # def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
# #     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(0, i_num_of_processes)}
# #
# #
# # def initialize_states(i_num_of_processes: int, i_formulas: List[str]):
# #     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
# #
# #
# # def initialize_event(i_event_data: List[str | List[str]], i_num_of_processes: int):
# #     event_name = i_event_data[0]
# #     event_processes = Process.distribute_processes(i_event_data[1], i_num_of_processes)
# #     propositions = i_event_data[2]
# #     vector_clock = i_event_data[3] if len(i_event_data) > 3 else [0] * i_num_of_processes
# #     event = Event(i_name=event_name, i_processes=event_processes, i_propositions=propositions)
# #     event.vector_clock = vector_clock
# #     return event
# #
# #
# # def attach_event_to_process(i_event: Event, i_processes: Dict[str, Process]):
# #     for p in i_event.processes:
# #         if p in i_processes:
# #             i_processes[p].add_event(i_event)
# #
# #
# # def find_new_states(i_states: List[State], i_event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
# #     new_states = []
# #     closed_events = set()
# #     for state in i_states:
# #         if state.enabled:
# #             new_state, closed_event = state | i_event
# #             if new_state is not None:
# #                 new_states.append(new_state)
# #                 closed_events.update(closed_event)
# #     return new_states, closed_events
# #
# #
# # def evaluate(i_new_states: List[State], i_prop: Formula):
# #     for new_state in i_new_states:
# #         res = i_prop.eval(state=new_state)
# #         new_state.value = res
# #
# #
# # def create_automaton(i_states: List[State]):
# #     state_names, transitions = set(), []
# #     for state in i_states:
# #         state_names.add(state.name)
# #         for pred_name, (event, _) in state.successors.items():
# #             transitions.append((pred_name, state.name, getattr(event, 'name')))
# #     Automaton.create_automaton(i_states, transitions)
# #
# #
# # if __name__ == '__main__':
# #     arguments = docopt(__doc__)
# #
# #     property_value = arguments['--property']
# #     trace_value = arguments['--trace.json.json.json']
# #     reduce_enabled = arguments['--reduce']
# #     debug_enabled = arguments['--debug']
# #     visual_enabled = arguments['--visual']
# #     experiment_mode = arguments['--experiment']
# #
# #     main(property_value, trace_value, reduce_enabled, debug_enabled, visual_enabled, experiment_mode)
#
#
# #
# # # poet.py
# #
# # """
# # Usage:
# #   poet.py --property=<property> --trace.json.json=<trace> [--reduce] [--debug] [--visual] [--experiment]
# #   poet.py -p <property> -t <trace> [-r] [-d] [-v] [-e]
# #
# # Options:
# #   -p <property>, --property=<property>          Property filename (mandatory)
# #   -t <trace>, --trace=<trace>   Trace filename (mandatory)
# #   -r, --reduce                                  Enable reduce (optional)
# #   -d, --debug                                   Enable debug mode (optional)
# #   -v, --visual                                  Enable visual output (optional)
# #   -e, --experiment                              Disable all print due to experiment benchmarks
# #   -h, --help                                    Show this help message and exit
# # """
# # from typing import List, Dict, Tuple, Set
# # from docopt import docopt
# # import time
# #
# # from graphics.automaton import Automaton
# # from graphics.prints import Prints
# # from model.event import Event
# # from model.process import Process
# # from model.process_modes import ProcessModes
# # from model.state import State
# # from parser.ast import Formula
# # from parser.parser import parse
# #
# # from utils.generic_utils import GenericUtils
# #
# #
# # def get_involved_indices(event: Event) -> List[int]:
# #     """
# #     Returns a list of indices (0-based) for all processes involved in the event.
# #     For each element in event.processes, if it is a string starting with "P",
# #     its index is computed from the numeric part.
# #     """
# #     indices = []
# #     for proc in event.processes:
# #         if isinstance(proc, str) and proc.startswith("P"):
# #             try:
# #                 indices.append(int(proc[1:]) - 1)
# #             except ValueError:
# #                 continue
# #     return indices
# #
# #
# # def is_event_in_order_multi(event_vc: List[int], expected_vc: List[int], involved: List[int]) -> bool:
# #     """
# #     For an event that involves multiple processes (given by indices in 'involved'),
# #     return True only if for every involved process, the event's vector clock equals
# #     expected_vc[i] + 1.
# #     """
# #     for i in involved:
# #         if event_vc[i] != expected_vc[i] + 1:
# #             return False
# #     return True
# #
# #
# # def main(i_property: str, i_trace: str, i_reduce: bool, i_debug: bool, i_visual: bool, i_experiment: bool):
# #     if not i_experiment:
# #         Prints.banner()
# #
# #     # Read and compile property.
# #     raw_prop = GenericUtils.read_property(i_property)
# #     prop = parse(raw_prop)
# #     Prints.raw_property(''.join(raw_prop))
# #     Prints.compiled_property(prop)
# #
# #     # Read trace file (trace events include vector clocks as 4th element)
# #     trace_data = GenericUtils.read_json(i_trace)
# #     trace = trace_data['events']
# #     num_of_processes = trace_data['processes']
# #
# #     # Initialize processes and the first state.
# #     processes = initialize_processes(num_of_processes)
# #     formulas = Formula.collect_formulas(prop)
# #     states = initialize_states(num_of_processes, formulas)
# #     res = prop.eval(state=states[0])
# #     states[0].value = res
# #
# #     # Setup for vector clock ordering:
# #     # For each process, expected_vc[i] is the last processed counter.
# #     expected_vc = [0] * num_of_processes
# #     holding_queue: List[Event] = []
# #
# #     if i_experiment:
# #         Prints.total_events(len(trace))
# #         events_processing_time = []
# #
# #     def flush_holding_queue():
# #         nonlocal expected_vc, holding_queue
# #         made_progress = True
# #         while made_progress:
# #             made_progress = False
# #             for evt in holding_queue[:]:
# #                 involved = get_involved_indices(evt)
# #                 if is_event_in_order_multi(evt.vector_clock, expected_vc, involved):
# #                     process_event(evt)
# #                     for i in involved:
# #                         expected_vc[i] = evt.vector_clock[i]
# #                     holding_queue.remove(evt)
# #                     made_progress = True
# #
# #     def process_event(event: Event):
# #         attach_event_to_process(event, processes)
# #         new_states, closed_events = find_new_states(states, event)
# #         for finish_event, index in filter(None, closed_events):
# #             finish_event.update_mode(ProcessModes.CLOSED, index)
# #         for state in states:
# #             if all(State.is_proc_closed(state.processes, i) for i in range(len(state.processes))):
# #                 state.enabled = False
# #         for i, state in enumerate(new_states):
# #             state.edges_completion(new_states[i:], processes)
# #         evaluate(new_states, prop)
# #         if i_debug:
# #             Prints.display_states(new_states, i_title="NEW", i_debug=i_debug)
# #         if i_reduce:
# #             for i in range(len(states) - 1, -1, -1):
# #                 if not states[i].enabled:
# #                     Prints.del_state(states[i], i_debug)
# #                     states[i] = None
# #                     del states[i]
# #         states.extend(new_states)
# #         if i_debug and i_visual:
# #             create_automaton(states)
# #
# #     # Main event loop with vector clock ordering.
# #     for event_data in trace:
# #         if i_experiment:
# #             start_time = time.time()
# #
# #         event = initialize_event(event_data, num_of_processes)
# #         Prints.event(event)
# #
# #         involved = get_involved_indices(event)
# #         if is_event_in_order_multi(event.vector_clock, expected_vc, involved):
# #             process_event(event)
# #             for i in involved:
# #                 expected_vc[i] = event.vector_clock[i]
# #             flush_holding_queue()
# #         else:
# #             holding_queue.append(event)
# #
# #         if i_experiment:
# #             current_time = time.time() - start_time
# #             events_processing_time.append(current_time)
# #
# #     flush_holding_queue()
# #
# #     if not i_experiment:
# #         Prints.display_states(states, i_title="ALL", i_debug=i_debug)
# #     else:
# #         Prints.total_states(len(states))
# #         max_time, max_index = max((t, idx) for idx, t in enumerate(events_processing_time))
# #         min_time, min_index = min((t, idx) for idx, t in enumerate(events_processing_time))
# #         avg_time = sum(events_processing_time) / len(events_processing_time)
# #         Prints.events_time((max_time, max_index), (min_time, min_index), avg_time)
# #
# #         # --- START MODIFICATION ---
# #         # Find the maximal state(s) which correspond to the final frontiers of the execution.
# #         # These are states that have no successors in the generated graph.
# #         maximal_states = [s for s in states if not s.successors]
# #
# #         if maximal_states:
# #             # In a partial order, there can be multiple maximal frontiers if the last events are concurrent.
# #             # We will display the verdict from the first one found, as it represents one possible final global state.
# #             final_verdict = maximal_states[0].value
# #             print(f"[FINAL VERDICT]: {final_verdict}")
# #         else:
# #             # This case might occur if the trace is empty or for other edge cases.
# #             print("[FINAL VERDICT]: Could not determine a final state.")
# #         # --- END MODIFICATION ---
# #
# #     if i_visual:
# #         create_automaton(states)
# #         if i_debug:
# #             Automaton.make_gif('output')
# #
# #
# # def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
# #     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(0, i_num_of_processes)}
# #
# #
# # def initialize_states(i_num_of_processes: int, i_formulas: List[str]):
# #     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
# #
# #
# # def initialize_event(i_event_data: List[str | List[str]], i_num_of_processes: int):
# #     event_name = i_event_data[0]
# #     event_processes = Process.distribute_processes(i_event_data[1], i_num_of_processes)
# #     propositions = i_event_data[2]
# #     vector_clock = i_event_data[3] if len(i_event_data) > 3 else [0] * i_num_of_processes
# #     event = Event(i_name=event_name, i_processes=event_processes, i_propositions=propositions)
# #     event.vector_clock = vector_clock
# #     return event
# #
# #
# # def attach_event_to_process(i_event: Event, i_processes: Dict[str, Process]):
# #     for p in i_event.processes:
# #         if p in i_processes:
# #             i_processes[p].add_event(i_event)
# #
# #
# # def find_new_states(i_states: List[State], i_event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
# #     new_states = []
# #     closed_events = set()
# #     for state in i_states:
# #         if state.enabled:
# #             new_state, closed_event = state | i_event
# #             if new_state is not None:
# #                 new_states.append(new_state)
# #                 closed_events.update(closed_event)
# #     return new_states, closed_events
# #
# #
# # def evaluate(i_new_states: List[State], i_prop: Formula):
# #     for new_state in i_new_states:
# #         res = i_prop.eval(state=new_state)
# #         new_state.value = res
# #
# #
# # def create_automaton(i_states: List[State]):
# #     state_names, transitions = set(), []
# #     for state in i_states:
# #         state_names.add(state.name)
# #         for pred_name, (event, _) in state.successors.items():
# #             transitions.append((pred_name, state.name, getattr(event, 'name')))
# #     Automaton.create_automaton(i_states, transitions)
# #
# #
# # if __name__ == '__main__':
# #     arguments = docopt(__doc__)
# #
# #     property_value = arguments['--property']
# #     trace_value = arguments['--trace']
# #     reduce_enabled = arguments['--reduce']
# #     debug_enabled = arguments['--debug']
# #     visual_enabled = arguments['--visual']
# #     experiment_mode = arguments['--experiment']
# #
# #     main(property_value, trace_value, reduce_enabled, debug_enabled, visual_enabled, experiment_mode)
#
# #
# # # poet.py
# #
# # """
# # Usage:
# #   poet.py --property=<property_file> --trace=<trace_file> [--reduce] [--visual] [--output-level=<level>]
# #   poet.py -p <property_file> -t <trace_file> [-r] [-v] [--output-level=<level>]
# #
# # Options:
# #   -p <property_file>, --property=<property_file>  Property filename (PCTL specification). (Mandatory)
# #   -t <trace_file>, --trace=<trace_file>             Trace filename (JSON format). (Mandatory)
# #   -r, --reduce                                      Enable reduce mode: prunes redundant states from the graph. (Optional)
# #   -v, --visual                                      Enable visual output: generates state graph files (SVG, GIF). (Optional)
# #   --output-level=<level>                            Specify output verbosity:
# #                                                     'nothing'    (suppresses all non-error console output).
# #                                                     'experiment' (minimal output for benchmarks; prints stats and final PCTL verdict).
# #                                                     'default'    (standard operational messages; prints final PCTL verdict).
# #                                                     'max_state'  (prints summary for the system's current global state defined by the
# #                                                                   monitor's vector clock after each event, plus final PCTL verdict).
# #                                                     'debug'      (maximum detailed output for developers; includes all prints).
# #                                                     [default: default]
# #   -h, --help                                        Show this help message and exit.
# # """
# # from typing import List, Dict, Tuple, Set, Any
# # from docopt import docopt
# # import time
# # import sys
# #
# # # Assuming these modules are in the correct relative paths for your project structure
# # from graphics.automaton import Automaton
# # from graphics.prints import Prints
# # from model.event import Event
# # from model.process import Process
# # from model.process_modes import ProcessModes
# # from model.state import State
# # from parser.ast import Formula
# # from parser.parser import parse
# # from utils.generic_utils import GenericUtils
# #
# # # Global flag to indicate if state reduction is active, used by create_automaton_snapshot logic
# # _SHOULD_REDUCE_STATES = False
# #
# #
# # def get_involved_indices(event: Event) -> List[int]:
# #     """
# #     Returns a list of 0-based indices for processes actively participating in the event.
# #     (This is your original implementation)
# #     """
# #     indices = []
# #     # event.processes here refers to the list like ['P1', ProcessModes.IOTA, ...]
# #     # set during Event initialization by Process.distribute_processes
# #     for proc_repr_in_event in event.processes:
# #         if isinstance(proc_repr_in_event, str) and proc_repr_in_event.startswith("P"):
# #             try:
# #                 indices.append(int(proc_repr_in_event[1:]) - 1)
# #             except ValueError:
# #                 continue
# #     return indices
# #
# #
# # def is_event_in_order_multi(event_vc: List[int], expected_vc: List[int], involved: List[int]) -> bool:
# #     """
# #     Your original vector clock check:
# #     For an event that involves multiple processes (given by indices in 'involved'),
# #     return True only if for every involved process, the event's vector clock equals
# #     expected_vc[i] + 1.
# #     """
# #     # Basic validation for vector clock lengths
# #     # It's assumed that involved indices are valid for both VCs if this point is reached.
# #     # Proper validation of VC length against num_processes should happen earlier (e.g., in initialize_event).
# #     for i in involved:
# #         if i >= len(event_vc) or i >= len(expected_vc):  # Boundary check
# #             # This indicates a serious inconsistency.
# #             if Prints.CURRENT_OUTPUT_LEVEL == "debug":  # Use global attribute from Prints
# #                 print(f"VC_CRITICAL_ERROR: Index {i} out of bounds in is_event_in_order_multi. "
# #                       f"Event VC len: {len(event_vc)}, Expected VC len: {len(expected_vc)}.")
# #             return False
# #         if event_vc[i] != expected_vc[i] + 1:
# #             return False
# #     return True
# #
# #
# # # --- Core Helper Functions (from your original poet.py structure) ---
# #
# # def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
# #     """Initializes a dictionary of Process objects, one for each process ID."""
# #     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(i_num_of_processes)}
# #
# #
# # def initialize_states(i_num_of_processes: int, i_formulas: List[str], output_level: str) -> List[State]:
# #     """Initializes the list of states, starting with S0."""
# #     if i_formulas:
# #         State._State__SUBFORMULAS = i_formulas
# #     else:
# #         State._State__SUBFORMULAS = []
# #     State._State__COUNTER = 0
# #
# #     # Pass output_level to State if its __init__ has conditional prints
# #     # (Currently, State.__init__ prints are not conditional on output_level in your provided code)
# #     if output_level == "debug":
# #         print(f"DEBUG_INIT: State class __SUBFORMULAS set to: {State._State__SUBFORMULAS}")
# #     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
# #
# #
# # def initialize_event(i_event_data: List[Any], i_num_of_processes: int, output_level: str) -> Event:
# #     """Creates an Event object from trace data, ensuring correct VC length."""
# #     event_name = str(i_event_data[0])
# #     # Process.distribute_processes can call sys.exit on error if process index is out of bounds.
# #     event_processes_for_constructor = Process.distribute_processes(i_event_data[1], i_num_of_processes)
# #     propositions = i_event_data[2]
# #     vector_clock_from_trace = i_event_data[3] if len(i_event_data) > 3 else [0] * i_num_of_processes
# #
# #     final_vector_clock = vector_clock_from_trace
# #     if len(vector_clock_from_trace) != i_num_of_processes:
# #         if output_level == "debug":
# #             print(f"VC_WARNING: Event '{event_name}' has VC length {len(vector_clock_from_trace)}, "
# #                   f"system has {i_num_of_processes} processes. Adjusting VC by padding/truncating.")
# #         final_vector_clock = (vector_clock_from_trace + [0] * i_num_of_processes)[:i_num_of_processes]
# #
# #     event = Event(i_name=event_name, i_processes=event_processes_for_constructor,
# #                   i_propositions=propositions, vector_clock=final_vector_clock)
# #     return event
# #
# #
# # def attach_event_to_process(i_event: Event, i_processes_map: Dict[str, Process]):
# #     """Adds an event to the history of each process string ID found in the event's process list."""
# #     # event.processes here is the original list like ['P1', ProcessModes.IOTA] from Event init.
# #     for proc_designator in i_event.processes:
# #         if isinstance(proc_designator, str) and proc_designator in i_processes_map:
# #             i_processes_map[proc_designator].add_event(i_event)
# #
# #
# # def find_new_states(i_current_states: List[State], i_event: Event, output_level: str) -> Tuple[
# #     List[State], Set[Tuple[Event, int]]]:
# #     """Generates new states by applying an event to all current enabled states."""
# #     newly_created_states = []
# #     all_closed_events_info = set()  # Stores (event_object, process_index) tuples
# #
# #     if output_level == "debug":
# #         # State.__or__ might have its own prints if you added them there
# #         pass  # Example: print(f"  DEBUG: find_new_states: Checking {len(i_current_states)} states for transitions with {i_event.name}")
# #
# #     for state_obj in i_current_states:
# #         if state_obj.enabled:
# #             new_state_candidate, closed_event_info_set_for_state = state_obj | i_event  # Calls State.__or__
# #             if new_state_candidate is not None:
# #                 # State.__init__ (called by State.__or__) might have debug prints
# #                 newly_created_states.append(new_state_candidate)
# #                 if closed_event_info_set_for_state:
# #                     all_closed_events_info.update(closed_event_info_set_for_state)
# #     return newly_created_states, all_closed_events_info
# #
# #
# # def evaluate(i_new_states: List[State], i_prop_formula: Formula, output_level: str):
# #     """Evaluates the PCTL property on a list of newly created states."""
# #     if output_level == "debug" and i_new_states:
# #         print(f"  DEBUG: evaluate: Evaluating PCTL on new states: {[s.name for s in i_new_states]}")
# #
# #     for new_state in i_new_states:
# #         if new_state.enabled:  # Typically, only evaluate enabled states for their final verdict
# #             if output_level == "debug":
# #                 print(f"    DEBUG: Evaluating spec '{str(i_prop_formula)}' on {new_state.name}")
# #             res = i_prop_formula.eval(state=new_state)  # AST eval methods might have their own prints
# #             new_state.value = res
# #             if output_level == "debug":
# #                 print(f"      DEBUG: {new_state.name}.value (main spec verdict) = {res}")
# #
# #
# # def create_automaton_snapshot(i_states_list: List[State]):  # Renamed to avoid conflict with user's original
# #     """
# #     Wrapper for Graphviz automaton snapshot generation.
# #     Uses the global _SHOULD_REDUCE_STATES flag.
# #     """
# #     # This function calls your original create_automaton logic
# #     # The list of states passed to it should be filtered if reduction is on.
# #     states_to_pass_to_actual_creation = [s for s in i_states_list if
# #                                          s.enabled] if _SHOULD_REDUCE_STATES else i_states_list
# #
# #     if not states_to_pass_to_actual_creation and i_states_list:
# #         # Fallback to show something if reduction removed all enabled states but states existed
# #         try:
# #             states_to_pass_to_actual_creation = [sorted(i_states_list, key=lambda s: int(s.name[1:]))[-1]]
# #         except (IndexError, ValueError, TypeError):
# #             if Prints.CURRENT_OUTPUT_LEVEL in ["default", "max_state", "debug"]:
# #                 print("VISUAL_WARN: Could not determine last state for fallback visualization during reduction.")
# #             return  # Can't visualize if no states or error
# #
# #     if not states_to_pass_to_actual_creation:
# #         if Prints.CURRENT_OUTPUT_LEVEL in ["default", "max_state", "debug"]:
# #             print("VISUAL_WARN: No states to create automaton for visualization.")
# #         return
# #
# #     # Call your original create_automaton function, which takes a list of states
# #     # and internally derives names and transitions.
# #     create_automaton(states_to_pass_to_actual_creation)
# #
# #
# # # --- Your original create_automaton function ---
# # def create_automaton(i_states: List[State]):
# #     """
# #     This is your original create_automaton function.
# #     It generates graphviz objects and renders them.
# #     """
# #     state_names, transitions = set(), []
# #     for state in i_states:  # i_states is now already filtered if reduction is on
# #         state_names.add(state.name)
# #         # Assuming state.successors exists and is populated correctly
# #         for pred_name, (event, _) in state.successors.items():
# #             # getattr is safer if event might not be an Event object, though it should be
# #             transitions.append((pred_name, state.name, getattr(event, 'name', 'ERROR_NO_EVENT_NAME')))
# #     # Automaton.create_automaton expects list of State objects
# #     Automaton.create_automaton(i_states, transitions)
# #
# #
# # # Main execution logic
# # def main(property_arg: str, trace_arg: str, reduce_arg: bool,
# #          visual_arg: bool, output_level_arg: str):
# #     global _SHOULD_REDUCE_STATES
# #     _SHOULD_REDUCE_STATES = reduce_arg
# #
# #     Prints.CURRENT_OUTPUT_LEVEL = output_level_arg  # Set for Prints class
# #
# #     # --- Initial Setup & Prints ---
# #     if output_level_arg not in ["experiment", "nothing"]:
# #         Prints.banner()  # Prints class methods now use Prints.CURRENT_OUTPUT_LEVEL
# #
# #     if output_level_arg == "debug":
# #         print(f"DEBUG: Output Level: Debug (Full Verbosity)")
# #         print(f"DEBUG: Using simplified vector clock deliverability rule (checks involved processes only).")
# #     elif output_level_arg in ["default", "max_state"]:
# #         print(f"Output Level: {output_level_arg}. Using simplified VC rule.")
# #
# #     State._State__COUNTER = 0
# #     Event._Event__TIMELINE = 0
# #
# #     # --- Property and Trace Loading ---
# #     try:
# #         raw_prop = GenericUtils.read_property(property_arg)
# #     except FileNotFoundError:
# #         Prints.process_error(f"Property file not found: {property_arg}");
# #         return
# #     prop_formula = parse(raw_prop)
# #     if not prop_formula: Prints.process_error(f"Failed to parse property: {raw_prop.strip()}"); return
# #
# #     if output_level_arg not in ["experiment", "nothing"]:
# #         Prints.raw_property(''.join(raw_prop))
# #         Prints.compiled_property(prop_formula)
# #
# #     try:
# #         trace_data = GenericUtils.read_json(trace_arg)
# #         trace_event_list_data = trace_data['events']
# #         num_processes = trace_data['processes']
# #     except FileNotFoundError:
# #         Prints.process_error(f"Trace file not found: {trace_arg}");
# #         return
# #     except Exception as e:
# #         Prints.process_error(f"Failed to read or parse trace file '{trace_arg}': {e}");
# #         return
# #
# #     # --- POET Core Initialization ---
# #     all_subformulas = Formula.collect_formulas(prop_formula)
# #     current_states: List[State] = initialize_states(num_processes, all_subformulas, output_level_arg)
# #     if not current_states: Prints.process_error("State initialization failed: No S0 state created."); return
# #
# #     s0_initial_verdict = prop_formula.eval(state=current_states[0])
# #     current_states[0].value = s0_initial_verdict
# #     if output_level_arg == "debug":
# #         print(f"DEBUG: S0 ({current_states[0].name}) initial PCTL verdict: {s0_initial_verdict}")
# #
# #     processes_map = initialize_processes(num_processes)
# #     expected_vc = [0] * num_processes
# #     holding_queue: List[Event] = []
# #     events_processing_times_list = []
# #
# #     # --- Function for --output-level=max_state ---
# #     def print_monitor_defined_frontier_details(triggering_event_name: str):
# #         # This function is only active if output_level is 'max_state'
# #         if output_level_arg != "max_state":
# #             return
# #
# #         print(f"\n--- Max State Info After Event: {triggering_event_name} ---")
# #
# #         # Display the monitor's current vector clock (expected_vc)
# #         vc_print_parts = [f"P{i + 1}:{val}" for i, val in enumerate(expected_vc)]
# #         print(f"  Monitor Expected VC (Defines Target Frontier): [{', '.join(vc_print_parts)}]")
# #
# #         # Construct the target frontier definition based on expected_vc
# #         # This means finding the event objects that correspond to the counts in expected_vc
# #         target_frontier_event_components: List[Any] = []
# #         for i in range(num_processes):
# #             proc_id_str = f"P{i + 1}"
# #             event_count_for_this_proc = expected_vc[i]
# #             if event_count_for_this_proc > 0:
# #                 process_obj = processes_map.get(proc_id_str)
# #                 # Ensure the process exists and has enough events recorded
# #                 if process_obj and event_count_for_this_proc <= len(process_obj.events):
# #                     # Event lists are 0-indexed, counts are 1-indexed
# #                     event_for_this_frontier_component = process_obj.events[event_count_for_this_proc - 1]
# #                     target_frontier_event_components.append(event_for_this_frontier_component)
# #                 else:
# #                     # This signifies an issue if expected_vc is ahead of recorded events
# #                     target_frontier_event_components.append(ProcessModes.ERROR)  # Indicate problem
# #                     if output_level_arg == "debug" or output_level_arg == "max_state":  # Print warning for these levels
# #                         print(f"    MAX_STATE_WARN: For {proc_id_str}, expected_vc count {event_count_for_this_proc} "
# #                               f"has no corresponding event in its history (len: {len(processes_map.get(proc_id_str, Process(proc_id_str)).events)}). "
# #                               f"Cannot define this component of target frontier precisely.")
# #             else:  # count_for_proc is 0, meaning no event from this process in the cut
# #                 target_frontier_event_components.append(ProcessModes.IOTA)
# #
# #         # Find the State object in current_states that matches this exact frontier definition
# #         found_target_state: State = None
# #         # Iterate through states to find an *enabled* one that matches the definition
# #         for s_candidate in reversed(current_states):  # Check newer states first
# #             if not s_candidate.enabled:
# #                 continue  # Only consider enabled states for the "current" view
# #
# #             if len(s_candidate.processes) != num_processes:  # Basic sanity check
# #                 continue
# #
# #             is_exact_match = True
# #             for i in range(num_processes):
# #                 target_component = target_frontier_event_components[i]
# #                 state_component = s_candidate.processes[i]
# #
# #                 # Compare types first
# #                 if type(target_component) != type(state_component):
# #                     is_exact_match = False;
# #                     break
# #
# #                 if isinstance(target_component, Event):  # Both are Events
# #                     # Compare by object identity (is) for exact match
# #                     if target_component is not state_component:
# #                         is_exact_match = False;
# #                         break
# #                 elif isinstance(target_component, ProcessModes):  # Both are ProcessModes
# #                     if target_component != state_component:
# #                         is_exact_match = False;
# #                         break
# #                 # If ProcessModes.ERROR was put in target_frontier_event_components, it won't match an Event/IOTA
# #
# #             if is_exact_match:
# #                 found_target_state = s_candidate
# #                 break  # Found the state corresponding to expected_vc
# #
# #         if found_target_state:
# #             state_to_print = found_target_state
# #             frontier_desc_parts = []
# #             for i, item in enumerate(state_to_print.processes):
# #                 proc_alias_for_print = f"P{i + 1}"  # Using P1, P2, ... as per trace
# #                 item_desc = item.name if isinstance(item, Event) else "iota"
# #                 frontier_desc_parts.append(f"{proc_alias_for_print}:{item_desc}")
# #
# #             print(f"  Target Frontier State: {state_to_print.name} = <{', '.join(frontier_desc_parts)}>")
# #             print(f"    Verdict (Spec): {state_to_print.value}")  # The PCTL verdict on this state
# #             print(f"    Propositions: {sorted(list(state_to_print.propositions))}")  # Global props for this state
# #             if output_level_arg == "debug":  # Extra info if also debugging
# #                 print(f"    Is Graph Maximal (no successors)?: {not bool(state_to_print.successors)}")
# #         else:
# #             print(
# #                 f"  Target Frontier State matching Monitor Expected VC = {expected_vc} was not found or not enabled among current states.")
# #             if output_level_arg == "debug":  # Help debug why it wasn't found
# #                 target_def_str = [(f"{t.name}<VC:{t.vector_clock}>" if isinstance(t, Event) else (
# #                     t.value if hasattr(t, 'value') else str(t))) for t in target_frontier_event_components]
# #                 print(f"    Target frontier definition sought (based on expected_vc): {target_def_str}")
# #         print("------------------------------------")
# #
# #     # --- Nested helper functions for event processing logic ---
# #     def process_single_event_local(event_to_process: Event):
# #         nonlocal current_states
# #         if output_level_arg == "debug": print(f"DEBUG: process_single_event_local for {event_to_process.name}")
# #
# #         attach_event_to_process(event_to_process, processes_map)
# #         newly_generated_states, closed_events_set = find_new_states(current_states, event_to_process, output_level_arg)
# #
# #         for fe, idx in filter(None, closed_events_set):
# #             if isinstance(fe, Event): fe.update_mode(ProcessModes.CLOSED, idx)
# #
# #         for s_obj in current_states:
# #             if s_obj.enabled:
# #                 all_closed_flag = True
# #                 if not s_obj.processes:
# #                     all_closed_flag = False
# #                 else:
# #                     for i_idx in range(len(s_obj.processes)):
# #                         if not State.is_proc_closed(s_obj.processes[i_idx], i_idx):
# #                             all_closed_flag = False;
# #                             break
# #                 if all_closed_flag:
# #                     if output_level_arg == "debug": print(
# #                         f"DEBUG: Disabling state {s_obj.name} (all process paths closed).")
# #                     s_obj.enabled = False
# #
# #         for i_enum, state_enum_obj in enumerate(newly_generated_states):
# #             state_enum_obj.edges_completion(newly_generated_states[i_enum:], processes_map)
# #         evaluate(newly_generated_states, prop_formula, output_level_arg)
# #
# #         if output_level_arg == "debug":
# #             Prints.display_states(newly_generated_states, i_title=f"NEWLY FORMED from {event_to_process.name}",
# #                                   i_debug=True)
# #
# #         if reduce_arg:
# #             idx = len(current_states) - 1
# #             while idx >= 0:
# #                 if not current_states[idx].enabled:
# #                     if output_level_arg == "debug": Prints.del_state(current_states[idx], True)
# #                     del current_states[idx]
# #                 idx -= 1
# #
# #         current_states.extend(newly_generated_states)
# #         if output_level_arg == "debug" and visual_arg:
# #             create_automaton_snapshot(current_states)
# #
# #     def local_flush_holding_queue_fn():
# #         nonlocal expected_vc, holding_queue, current_states
# #         made_progress_this_flush = True
# #         while made_progress_this_flush:
# #             made_progress_this_flush = False
# #             if not holding_queue: break
# #
# #             if output_level_arg == "debug": print(
# #                 f"DEBUG: Flushing queue. Queue: {[e.name for e in holding_queue]}. Expected VC: {expected_vc}")
# #
# #             for event_from_queue in holding_queue[:]:
# #                 # Use your original is_event_in_order_multi as per your last code snippet
# #                 involved_indices_for_queued = get_involved_indices(event_from_queue)
# #                 if is_event_in_order_multi(event_from_queue.vector_clock, expected_vc, involved_indices_for_queued):
# #                     if output_level_arg == "debug": print(
# #                         f"DEBUG: Flushing {event_from_queue.name} (VC: {event_from_queue.vector_clock}) from queue.")
# #
# #                     process_single_event_local(event_from_queue)
# #
# #                     # Update expected_vc for processes involved in the flushed event
# #                     for i_val in involved_indices_for_queued:
# #                         expected_vc[i_val] = event_from_queue.vector_clock[i_val]
# #
# #                     holding_queue.remove(event_from_queue)
# #                     made_progress_this_flush = True
# #                     if output_level_arg == "debug": print(
# #                         f"DEBUG: After flushing {event_from_queue.name}, new expected_vc: {expected_vc}")
# #
# #                     # After a successful flush, call the print function for max_state level
# #                     print_monitor_defined_frontier_details(f"{event_from_queue.name} (from queue)")
# #                     break  # Restart scan of the holding queue as expected_vc changed
# #
# #             if not made_progress_this_flush and output_level_arg == "debug" and holding_queue:
# #                 print(f"DEBUG: Flush queue: No progress made. Queue: {[e.name for e in holding_queue]}")
# #
# #     # --- End Nested Helper Functions ---
# #
# #     # --- Main Event Processing Loop ---
# #     if output_level_arg == "experiment": Prints.total_events(len(trace_event_list_data))
# #
# #     # Print initial state info for max_state level (based on S0 and initial expected_vc=[0,0,...])
# #     print_monitor_defined_frontier_details("Initial_S0")
# #
# #     for event_idx, event_data in enumerate(trace_event_list_data):
# #         if output_level_arg == "experiment": current_event_start_time = time.time()
# #
# #         current_event_obj = initialize_event(event_data, num_processes, output_level_arg)
# #         if not current_event_obj:
# #             Prints.process_error(f"Could not initialize event {event_idx} from data: {event_data}")
# #             continue
# #
# #         if output_level_arg == "debug":
# #             Prints.event(current_event_obj, i_debug=True)  # This is your existing Prints.event
# #             print(
# #                 f"DEBUG: MainLoop - Handling trace event {current_event_obj.name}. Current Expected VC: {expected_vc}")
# #         elif output_level_arg in ["default", "max_state"]:
# #             print(f"\nProcessing Event: {current_event_obj.name} (VC: {current_event_obj.vector_clock})")
# #
# #         involved_indices = get_involved_indices(current_event_obj)
# #         # Use your original is_event_in_order_multi for deliverability check
# #         if is_event_in_order_multi(current_event_obj.vector_clock, expected_vc, involved_indices):
# #             if output_level_arg == "debug": print(f"DEBUG: Event {current_event_obj.name} is IN ORDER.")
# #             process_single_event_local(current_event_obj)
# #             # Update expected_vc for processes involved in the current event
# #             for i in involved_indices: expected_vc[i] = current_event_obj.vector_clock[i]
# #             if output_level_arg == "debug": print(
# #                 f"DEBUG: After {current_event_obj.name}, new expected_vc: {expected_vc}. Flushing queue...")
# #             local_flush_holding_queue_fn()
# #         else:
# #             if output_level_arg == "debug": print(
# #                 f"DEBUG: Event {current_event_obj.name} is OUT OF ORDER. Adding to holding queue.")
# #             holding_queue.append(current_event_obj)
# #
# #         # Print max_state info after this event and any resulting queue flushes are done
# #         if not any(e is current_event_obj for e in holding_queue):  # If event was processed directly
# #             print_monitor_defined_frontier_details(current_event_obj.name)
# #
# #         if output_level_arg == "experiment":
# #             event_processing_duration = time.time() - current_event_start_time
# #             events_processing_times_list.append(event_processing_duration)
# #
# #     # --- Post-Trace Processing ---
# #     if output_level_arg == "debug": print("DEBUG: End of trace events. Final flush of holding queue...")
# #     local_flush_holding_queue_fn()
# #
# #     # Final print for max_state level after all trace events and all queue flushing.
# #     print_monitor_defined_frontier_details("End_Of_Trace")
# #
# #     # --- Final Outputs Section ---
# #     if output_level_arg in ["default", "debug", "max_state"]:
# #         Prints.display_states(current_states, i_title="ALL FINAL STATES", i_debug=(output_level_arg == "debug"))
# #
# #     if output_level_arg == "experiment":
# #         Prints.total_states(len(current_states))
# #         if events_processing_times_list:
# #             max_time_val = max(events_processing_times_list)
# #             max_idx_val = events_processing_times_list.index(max_time_val)
# #             max_event_name = trace_event_list_data[max_idx_val][0] if max_idx_val < len(
# #                 trace_event_list_data) else "N/A"
# #             min_time_val = min(events_processing_times_list)
# #             min_idx_val = events_processing_times_list.index(min_time_val)
# #             min_event_name = trace_event_list_data[min_idx_val][0] if min_idx_val < len(
# #                 trace_event_list_data) else "N/A"
# #             avg_time_val = sum(events_processing_times_list) / len(events_processing_times_list)
# #             Prints.events_time((max_time_val, max_event_name), (min_time_val, min_event_name), avg_time_val)
# #
# #     if output_level_arg != "nothing":
# #         # For final verdict, use the standard way: first maximal enabled state
# #         final_maximal_enabled_frontiers = [s for s in current_states if not s.successors and s.enabled]
# #         final_verdict_val_str = "Undetermined"
# #         if final_maximal_enabled_frontiers:
# #             final_verdict_val_str = str(final_maximal_enabled_frontiers[0].value)
# #             print(f"[FINAL VERDICT]: {final_verdict_val_str}")
# #         elif current_states:
# #             newest_overall_states = sorted(current_states, key=lambda s: int(s.name[1:]), reverse=True)
# #             if newest_overall_states:
# #                 final_verdict_val_str = str(newest_overall_states[0].value)
# #                 print(f"[FINAL VERDICT (from newest state overall)]: {final_verdict_val_str}")
# #             else:
# #                 print("[FINAL VERDICT]: Could not determine (no states remaining).")
# #         else:
# #             print("[FINAL VERDICT]: Could not determine (no states generated after S0).")
# #
# #     if visual_arg:
# #         create_automaton_snapshot(current_states)
# #         if output_level_arg == "debug":
# #             Automaton.make_gif('output')
# #
# #     if holding_queue:
# #         if output_level_arg not in ["experiment", "nothing"]:
# #             print(f"WARNING: Program ended with events still in holding queue: {[e.name for e in holding_queue]}")
# #
# #
# # if __name__ == '__main__':
# #     arguments = docopt(__doc__)
# #
# #     property_arg_val = arguments['--property']
# #     trace_arg_val = arguments['--trace']
# #     reduce_arg_val = bool(arguments['--reduce'])
# #     visual_arg_val = bool(arguments['--visual'])
# #     output_level_arg_val = arguments['--output-level']
# #
# #     main(property_arg_val, trace_arg_val,
# #          reduce_arg_val, visual_arg_val, output_level_arg_val)
#
#
# # poet.py
#
# """
# Usage:
#   poet.py --property=<property_file> --trace=<trace_file> [--reduce] [--visual] [--output-level=<level>]
#   poet.py -p <property_file> -t <trace_file> [-r] [-v] [--output-level=<level>]
#
# Options:
#   -p <property_file>, --property=<property_file>  Property filename (PCTL specification). (Mandatory)
#   -t <trace_file>, --trace=<trace_file>             Trace filename (JSON format). (Mandatory)
#   -r, --reduce                                      Enable reduce mode: prunes redundant states from the graph. (Optional)
#   -v, --visual                                      Enable visual output: generates state graph files (SVG, GIF). (Optional)
#   --output-level=<level>                            Specify output verbosity:
#                                                     'nothing'    (suppresses all non-error console output).
#                                                     'experiment' (minimal output for benchmarks; prints stats and final PCTL verdict).
#                                                     'default'    (standard operational messages; prints final PCTL verdict).
#                                                     'max_state'  (prints summary for the system's current global state defined by the
#                                                                   monitor's vector clock after each event, plus final PCTL verdict.
#                                                                   Also prints a collected list of these summaries at the end).
#                                                     'debug'      (maximum detailed output for developers; includes all prints).
#                                                     [default: default]
#   -h, --help                                        Show this help message and exit.
# """
# from typing import List, Dict, Tuple, Set, Any
# from docopt import docopt
# import time
# import sys
#
# # Assuming these modules are in the correct relative paths for your project structure
# from graphics.automaton import Automaton
# from graphics.prints import Prints  # Using the version you provided
# from model.event import Event
# from model.process import Process
# from model.process_modes import ProcessModes
# from model.state import State
# from parser.ast import Formula
# from parser.parser import parse
# from utils.generic_utils import GenericUtils
#
# # Global flag to indicate if state reduction is active
# _SHOULD_REDUCE_STATES = False
#
#
# def get_involved_indices(event: Event) -> List[int]:
#     """
#     Returns a list of 0-based indices for processes actively participating in the event.
#     (This is your original implementation)
#     """
#     indices = []
#     for proc_repr_in_event in event.processes:
#         if isinstance(proc_repr_in_event, str) and proc_repr_in_event.startswith("P"):
#             try:
#                 indices.append(int(proc_repr_in_event[1:]) - 1)
#             except ValueError:
#                 continue  # Should not happen if P<num> is well-formed
#     return indices
#
#
# def is_event_in_order_multi(event_vc: List[int], expected_vc: List[int], involved: List[int]) -> bool:
#     """
#     Original vector clock check:
#     For an event that involves multiple processes (given by indices in 'involved'),
#     return True only if for every involved process, the event's vector clock equals
#     expected_vc[i] + 1.
#     """
#     for i in involved:
#         if i >= len(event_vc) or i >= len(expected_vc):
#             # Conditional print based on global setting in Prints class
#             if hasattr(Prints, 'CURRENT_OUTPUT_LEVEL') and Prints.CURRENT_OUTPUT_LEVEL == "debug":
#                 print(f"VC_CRITICAL_ERROR: Index {i} out of bounds in is_event_in_order_multi. "
#                       f"Event VC len: {len(event_vc)}, Expected VC len: {len(expected_vc)}.")
#             return False
#         if event_vc[i] != expected_vc[i] + 1:
#             return False
#     return True
#
#
# # --- Core Helper Functions ---
# def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
#     return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(i_num_of_processes)}
#
#
# def initialize_states(i_num_of_processes: int, i_formulas: List[str], output_level: str) -> List[State]:
#     if i_formulas:
#         State._State__SUBFORMULAS = i_formulas
#     else:
#         State._State__SUBFORMULAS = []
#     State._State__COUNTER = 0
#     if output_level == "debug":
#         print(f"DEBUG_INIT: State class __SUBFORMULAS set to: {State._State__SUBFORMULAS}")
#     return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]
#
#
# def initialize_event(i_event_data: List[Any], i_num_of_processes: int, output_level: str) -> Event:
#     event_name = str(i_event_data[0])
#     event_processes_for_constructor = Process.distribute_processes(i_event_data[1], i_num_of_processes)
#     propositions = i_event_data[2]
#     vector_clock_from_trace = i_event_data[3] if len(i_event_data) > 3 else [0] * i_num_of_processes
#     final_vector_clock = vector_clock_from_trace
#     if len(vector_clock_from_trace) != i_num_of_processes:
#         if output_level == "debug":
#             print(
#                 f"VC_WARNING: Event '{event_name}' has VC length {len(vector_clock_from_trace)}, system has {i_num_of_processes} processes. Adjusting VC.")
#         final_vector_clock = (vector_clock_from_trace + [0] * i_num_of_processes)[:i_num_of_processes]
#     event = Event(i_name=event_name, i_processes=event_processes_for_constructor,
#                   i_propositions=propositions, vector_clock=final_vector_clock)
#     return event
#
#
# def attach_event_to_process(i_event: Event, i_processes_map: Dict[str, Process]):
#     for proc_designator in i_event.processes:
#         if isinstance(proc_designator, str) and proc_designator in i_processes_map:
#             i_processes_map[proc_designator].add_event(i_event)
#
#
# def find_new_states(i_current_states: List[State], i_event: Event, output_level: str) -> Tuple[
#     List[State], Set[Tuple[Event, int]]]:
#     newly_created_states = []
#     all_closed_events_info = set()
#     if output_level == "debug": pass
#     for state_obj in i_current_states:
#         if state_obj.enabled:
#             new_state_candidate, closed_event_info_set_for_state = state_obj | i_event
#             if new_state_candidate is not None:
#                 newly_created_states.append(new_state_candidate)
#                 if closed_event_info_set_for_state:
#                     all_closed_events_info.update(closed_event_info_set_for_state)
#     return newly_created_states, all_closed_events_info
#
#
# def evaluate(i_new_states: List[State], i_prop_formula: Formula, output_level: str):
#     if output_level == "debug" and i_new_states:
#         print(f"  DEBUG: evaluate: Evaluating PCTL on new states: {[s.name for s in i_new_states]}")
#     for new_state in i_new_states:
#         if new_state.enabled:
#             if output_level == "debug":
#                 print(f"    DEBUG: Evaluating spec '{str(i_prop_formula)}' on {new_state.name}")
#             res = i_prop_formula.eval(state=new_state)
#             new_state.value = res
#             if output_level == "debug":
#                 print(f"      DEBUG: {new_state.name}.value (main spec verdict) = {res}")
#
#
# # Using your original create_automaton directly, no wrapper needed if it's self-contained
# def create_automaton(i_states: List[State]):  # This is your existing function
#     state_names, transitions = set(), []
#     for state in i_states:
#         state_names.add(state.name)
#         for pred_name, (event, _) in state.successors.items():
#             transitions.append((pred_name, state.name, getattr(event, 'name', 'ERROR_NO_EVENT_NAME')))
#     Automaton.create_automaton(i_states, transitions)
#
#
# # Main execution logic
# def main(property_arg: str, trace_arg: str, reduce_arg: bool,
#          visual_arg: bool, output_level_arg: str):
#     global _SHOULD_REDUCE_STATES
#     _SHOULD_REDUCE_STATES = reduce_arg  # Set global based on argument
#
#     Prints.CURRENT_OUTPUT_LEVEL = output_level_arg
#
#     if output_level_arg not in ["experiment", "nothing"]:
#         Prints.banner()
#
#     if output_level_arg == "debug":
#         print(f"DEBUG: Output Level: Debug (Full Verbosity)")
#         print(f"DEBUG: Using PoET's standard vector clock deliverability rule.")
#     elif output_level_arg in ["default", "max_state"]:
#         print(f"Output Level: {output_level_arg}. Using PoET's standard VC rule.")
#
#     State._State__COUNTER = 0
#     Event._Event__TIMELINE = 0
#
#     try:
#         raw_prop = GenericUtils.read_property(property_arg)
#     except FileNotFoundError:
#         Prints.process_error(f"Property file not found: {property_arg}"); return
#     prop_formula = parse(raw_prop)
#     if not prop_formula: Prints.process_error(f"Failed to parse property: {raw_prop.strip()}"); return
#
#     if output_level_arg not in ["experiment", "nothing"]:
#         Prints.raw_property(''.join(raw_prop))
#         Prints.compiled_property(prop_formula)
#
#     try:
#         trace_data = GenericUtils.read_json(trace_arg)
#         trace_event_list_data = trace_data['events']
#         num_processes = trace_data['processes']
#     except FileNotFoundError:
#         Prints.process_error(f"Trace file not found: {trace_arg}"); return
#     except Exception as e:
#         Prints.process_error(f"Failed to read or parse trace file '{trace_arg}': {e}"); return
#
#     all_subformulas = Formula.collect_formulas(prop_formula)
#     current_states: List[State] = initialize_states(num_processes, all_subformulas, output_level_arg)
#     if not current_states: Prints.process_error("State initialization failed: No S0 state created."); return
#
#     s0_initial_verdict = prop_formula.eval(state=current_states[0])
#     current_states[0].value = s0_initial_verdict
#     if output_level_arg == "debug":
#         print(f"DEBUG: S0 ({current_states[0].name}) initial PCTL verdict: {s0_initial_verdict}")
#
#     processes_map = initialize_processes(num_processes)
#     expected_vc = [0] * num_processes
#     holding_queue: List[Event] = []
#     events_processing_times_list = []
#
#     max_state_history: List[str] = []  # List to store summaries for final print
#
#     def collect_and_print_monitor_frontier_details(triggering_event_name: str, event_obj_for_aliases: Event = None):
#         # This function is only active if output_level is 'max_state'
#         if output_level_arg != "max_state":
#             return
#
#         # For process aliases like M, S, A as in your example output
#         # This is a simple mapping for 3 processes. Adjust if needed.
#         proc_alias_map = {0: "M", 1: "S", 2: "A"}  # P1=M, P2=S, P3=A
#         proc_aliases = [proc_alias_map.get(i, f"P{i + 1}") for i in range(num_processes)]
#
#         vc_print_parts = [f"{proc_aliases[i]}:{expected_vc[i]}" for i in range(num_processes)]
#         current_vc_str = f"[{', '.join(vc_print_parts)}]"
#
#         trigger_proc_alias_part = ""
#         if event_obj_for_aliases:
#             active_p_indices = get_involved_indices(event_obj_for_aliases)
#             if active_p_indices:
#                 # Get the alias of the first involved process for the @X part
#                 trigger_proc_alias_part = f"@{proc_aliases[active_p_indices[0]]}" if active_p_indices[0] < len(
#                     proc_aliases) else ""
#
#         header_str = f"{triggering_event_name}{trigger_proc_alias_part}:{current_vc_str}"
#
#         target_frontier_event_components: List[Any] = []
#         for i in range(num_processes):
#             proc_id_str = f"P{i + 1}"
#             count_for_proc = expected_vc[i]
#             if count_for_proc > 0:
#                 process_obj = processes_map.get(proc_id_str)
#                 if process_obj and count_for_proc <= len(process_obj.events):
#                     event_for_this_frontier_component = process_obj.events[count_for_proc - 1]
#                     target_frontier_event_components.append(event_for_this_frontier_component)
#                 else:
#                     target_frontier_event_components.append(ProcessModes.IOTA)
#             else:
#                 target_frontier_event_components.append(ProcessModes.IOTA)
#
#         found_target_state: State = None
#         for s_candidate in reversed(current_states):
#             if not s_candidate.enabled: continue
#             if len(s_candidate.processes) != num_processes: continue
#             is_exact_match = True
#             for i in range(num_processes):
#                 target_comp_item = target_frontier_event_components[i]
#                 state_comp_item = s_candidate.processes[i]
#                 if type(target_comp_item) != type(state_comp_item): is_exact_match = False; break
#                 if isinstance(target_comp_item, Event):
#                     if target_comp_item is not state_comp_item: is_exact_match = False; break
#                 elif isinstance(target_comp_item, ProcessModes):
#                     if target_comp_item != state_comp_item: is_exact_match = False; break
#             if is_exact_match:
#                 found_target_state = s_candidate;
#                 break
#
#         frontier_str_for_list = "frontiers=['<unknown_frontier>']"
#         verdict_str = "UNKNOWN"
#
#         if found_target_state:
#             state_to_print = found_target_state
#             frontier_desc_parts = [f"{proc_aliases[i]}:{item.name if isinstance(item, Event) else 'iota'}"
#                                    for i, item in enumerate(state_to_print.processes)]
#
#             formatted_frontier_str = f"⟨{', '.join(frontier_desc_parts)}⟩"
#             frontier_str_for_list = f"frontiers=['{formatted_frontier_str}']"
#             verdict_str = str(state_to_print.value).upper()
#
#             # Print to console immediately (this is the existing max_state per-event print)
#             print(f"\n--- Max State Info (Trigger: {triggering_event_name}) ---")
#             print(f"  {header_str} → {frontier_str_for_list}, verdict={verdict_str}")
#             if output_level_arg == "debug":
#                 print(
#                     f"    State Object: {state_to_print.name}, Propositions: {sorted(list(state_to_print.propositions))}")
#                 print(f"    Is Graph Maximal (no successors)?: {not bool(state_to_print.successors)}")
#         else:
#             print(f"\n--- Max State Info (Trigger: {triggering_event_name}) ---")
#             print(f"  Monitor Expected VC: {current_vc_str}")
#             print(f"  Target Frontier State matching Expected VC was not found or not enabled.")
#             # Do not add to history if state not found, or add a specific "not found" message
#             max_state_history.append(f"{header_str} → frontiers=['<state_not_found_for_vc>'], verdict=NOT_FOUND")
#             print("------------------------------------")
#             return
#
#         summary_line = f"{header_str} → {frontier_str_for_list}, verdict={verdict_str}"
#         max_state_history.append(summary_line)
#         print("------------------------------------")
#
#     def process_single_event_local(event_to_process: Event):
#         nonlocal current_states
#         # Use Prints.event for debug, as it has more detail
#         if output_level_arg == "debug": Prints.event(event_to_process, i_debug=True)
#
#         attach_event_to_process(event_to_process, processes_map)
#         newly_generated_states, closed_events_set = find_new_states(current_states, event_to_process, output_level_arg)
#
#         for fe, idx in filter(None, closed_events_set):
#             if isinstance(fe, Event): fe.update_mode(ProcessModes.CLOSED, idx)
#
#         for s_obj in current_states:
#             if s_obj.enabled:
#                 all_closed_flag = True
#                 if not s_obj.processes:
#                     all_closed_flag = False
#                 else:
#                     for i_idx in range(len(s_obj.processes)):
#                         if not State.is_proc_closed(s_obj.processes[i_idx], i_idx):
#                             all_closed_flag = False;
#                             break
#                 if all_closed_flag:
#                     # Use Prints.del_state for disabling message if debug
#                     if output_level_arg == "debug": Prints.del_state(s_obj, i_debug=True)  # Logically "deleting"
#                     s_obj.enabled = False  # Actual disabling
#
#         for i_enum, state_enum_obj in enumerate(newly_generated_states):
#             state_enum_obj.edges_completion(newly_generated_states[i_enum:], processes_map)
#         evaluate(newly_generated_states, prop_formula, output_level_arg)
#
#         if output_level_arg == "debug":
#             Prints.display_states(newly_generated_states, i_title=f"NEWLY FORMED from {event_to_process.name}",
#                                   i_debug=True)
#
#         if reduce_arg:
#             idx = len(current_states) - 1
#             while idx >= 0:
#                 if not current_states[idx].enabled:
#                     if output_level_arg == "debug": Prints.del_state(current_states[idx], i_debug=True)
#                     del current_states[idx]
#                 idx -= 1
#
#         current_states.extend(newly_generated_states)
#         if output_level_arg == "debug" and visual_arg:
#             create_automaton_snapshot(current_states)
#
#     def local_flush_holding_queue_fn():
#         nonlocal expected_vc, holding_queue, current_states
#         made_progress_this_flush = True
#         while made_progress_this_flush:
#             made_progress_this_flush = False
#             if not holding_queue: break
#             if output_level_arg == "debug": print(
#                 f"DEBUG: Flushing queue. Queue: {[e.name for e in holding_queue]}. Expected VC: {expected_vc}")
#             for event_from_queue in holding_queue[:]:
#                 involved_indices_for_queued = get_involved_indices(event_from_queue)
#                 if is_event_in_order_multi(event_from_queue.vector_clock, expected_vc, involved_indices_for_queued):
#                     if output_level_arg == "debug": print(
#                         f"DEBUG: Flushing {event_from_queue.name} (VC: {event_from_queue.vector_clock}) from queue.")
#                     process_single_event_local(event_from_queue)
#                     for i_val in involved_indices_for_queued:
#                         expected_vc[i_val] = event_from_queue.vector_clock[i_val]
#                     holding_queue.remove(event_from_queue)
#                     made_progress_this_flush = True
#                     if output_level_arg == "debug": print(
#                         f"DEBUG: After flushing {event_from_queue.name}, new expected_vc: {expected_vc}")
#                     collect_and_print_monitor_frontier_details(f"{event_from_queue.name} (from queue)",
#                                                                event_from_queue)
#                     break
#             if not made_progress_this_flush and output_level_arg == "debug" and holding_queue:
#                 print(f"DEBUG: Flush queue: No progress made. Queue: {[e.name for e in holding_queue]}")
#
#     if output_level_arg == "experiment": Prints.total_events(len(trace_event_list_data))
#
#     collect_and_print_monitor_frontier_details("Initial_S0")
#
#     for event_idx, event_data in enumerate(trace_event_list_data):
#         if output_level_arg == "experiment": current_event_start_time = time.time()
#
#         current_event_obj = initialize_event(event_data, num_processes, output_level_arg)
#         if not current_event_obj:
#             Prints.process_error(f"Could not initialize event {event_idx} from data: {event_data}");
#             continue
#
#         # Use Prints.event if debug, otherwise simpler print for default/max_state
#         if output_level_arg == "debug":
#             Prints.event(current_event_obj, i_debug=True)
#             print(
#                 f"DEBUG: MainLoop - Handling trace event {current_event_obj.name}. Current Expected VC: {expected_vc}")
#         elif output_level_arg in ["default", "max_state"]:
#             print(f"\nProcessing Event: {current_event_obj.name} (VC: {current_event_obj.vector_clock})")
#
#         involved_indices = get_involved_indices(current_event_obj)
#         if is_event_in_order_multi(current_event_obj.vector_clock, expected_vc, involved_indices):
#             if output_level_arg == "debug": print(f"DEBUG: Event {current_event_obj.name} is IN ORDER.")
#             process_single_event_local(current_event_obj)
#             for i in involved_indices: expected_vc[i] = current_event_obj.vector_clock[i]
#             if output_level_arg == "debug": print(
#                 f"DEBUG: After {current_event_obj.name}, new expected_vc: {expected_vc}. Flushing queue...")
#             local_flush_holding_queue_fn()
#         else:
#             if output_level_arg == "debug": print(
#                 f"DEBUG: Event {current_event_obj.name} is OUT OF ORDER. Adding to holding queue.")
#             holding_queue.append(current_event_obj)
#
#         if not any(e is current_event_obj for e in holding_queue):
#             collect_and_print_monitor_frontier_details(current_event_obj.name, current_event_obj)
#
#         if output_level_arg == "experiment":
#             event_processing_duration = time.time() - current_event_start_time
#             events_processing_times_list.append(event_processing_duration)
#
#     if output_level_arg == "debug": print("DEBUG: End of trace events. Final flush of holding queue...")
#     local_flush_holding_queue_fn()
#     collect_and_print_monitor_frontier_details("End_Of_Trace")
#
#     # --- Final Summary List for max_state ---
#     if output_level_arg == "max_state" and max_state_history:
#         Prints.seperator("MAXIMAL STATES HISTORY (Monitor's VC Cut @ Trigger)")  # Using Prints.seperator
#         for summary_line in max_state_history:
#             # The summary line is already formatted, print directly.
#             # Add color if desired, e.g., using Prints.Fore.CYAN, but Prints class doesn't expose Fore directly.
#             print(summary_line)
#         Prints.seperator("END MAXIMAL STATES HISTORY")
#
#     if output_level_arg in ["default", "debug", "max_state"]:
#         Prints.display_states(current_states, i_title="ALL FINAL STATES", i_debug=(output_level_arg == "debug"))
#
#     if output_level_arg == "experiment":
#         Prints.total_states(len(current_states))
#         if events_processing_times_list:
#             max_time_val = max(events_processing_times_list)
#             max_idx_val = events_processing_times_list.index(max_time_val)
#             max_event_name = trace_event_list_data[max_idx_val][0] if max_idx_val < len(
#                 trace_event_list_data) else "N/A"
#             min_time_val = min(events_processing_times_list)
#             min_idx_val = events_processing_times_list.index(min_time_val)
#             min_event_name = trace_event_list_data[min_idx_val][0] if min_idx_val < len(
#                 trace_event_list_data) else "N/A"
#             avg_time_val = sum(events_processing_times_list) / len(events_processing_times_list)
#             Prints.events_time((max_time_val, max_event_name), (min_time_val, min_event_name), avg_time_val)
#
#     if output_level_arg != "nothing":
#         final_maximal_enabled_frontiers = [s for s in current_states if not s.successors and s.enabled]
#         final_verdict_val_str = "Undetermined"
#         if final_maximal_enabled_frontiers:
#             final_verdict_val_str = str(final_maximal_enabled_frontiers[0].value).upper()
#             print(f"[FINAL VERDICT]: {final_verdict_val_str}")
#         elif current_states:
#             newest_overall_states = sorted(current_states, key=lambda s: int(s.name[1:]), reverse=True)
#             if newest_overall_states:
#                 final_verdict_val_str = str(newest_overall_states[0].value).upper()
#                 print(f"[FINAL VERDICT (from newest state overall)]: {final_verdict_val_str}")
#             else:
#                 print("[FINAL VERDICT]: Could not determine (no states remaining).")
#         else:
#             print("[FINAL VERDICT]: Could not determine (no states generated after S0).")
#
#     if visual_arg:
#         create_automaton_wrapper(current_states)
#         if output_level_arg == "debug":
#             Automaton.make_gif('output')
#
#     if holding_queue:
#         if output_level_arg not in ["experiment", "nothing"]:
#             print(f"WARNING: Program ended with events still in holding queue: {[e.name for e in holding_queue]}")
#
#
# if __name__ == '__main__':
#     arguments = docopt(__doc__)
#
#     property_arg_val = arguments['--property']
#     trace_arg_val = arguments['--trace']
#     reduce_arg_val = bool(arguments['--reduce'])
#     visual_arg_val = bool(arguments['--visual'])
#     output_level_arg_val = arguments['--output-level']
#
#     main(property_arg_val, trace_arg_val,
#          reduce_arg_val, visual_arg_val, output_level_arg_val)


# !/usr/bin/env python3
# poet.py
"""
PoET: Property-oriented Event Trace Monitor
Main entry point for the application.

Usage:
  poet.py --property=<property_file> --trace=<trace_file> [--reduce] [--visual] [--output-level=<level>]
  poet.py -p <property_file> -t <trace_file> [-r] [-v] [--output-level=<level>]

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
  -h, --help                                        Show this help message and exit.
"""

from docopt import docopt
from core.poet_monitor import PoETMonitor
from utils.config import Config


def main():
    """Main entry point for the PoET application."""
    arguments = docopt(__doc__)

    # Parse command line arguments
    config = Config(
        property_file=arguments['--property'],
        trace_file=arguments['--trace'],
        reduce_enabled=bool(arguments['--reduce']),
        visual_enabled=bool(arguments['--visual']),
        output_level=arguments['--output-level'] or 'default'
    )

    try:
        # Create and run the monitor
        monitor = PoETMonitor(config)
        monitor.run()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Force program termination
        import sys
        print("DEBUG: Program execution completed")
        sys.stdout.flush()
        sys.exit(0)


if __name__ == '__main__':
    main()
