# core/sliding_window_graph.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Sliding window graph implementation as described in the paper.
# Manages nodes (frontiers) and edges with backward propagation for
# independent event commutation.

from typing import Dict, List, Set, Tuple, Optional, Any

from model.event import Event
from model.process_modes import ProcessModes
from utils.logger import get_logger, LogCategory


class SlidingWindowNode:
    """Represents a node (frontier) in the sliding window graph."""

    def __init__(self, node_id: str, frontier: List[Any]):
        self.node_id = node_id
        self.frontier = frontier  # List representing the frontier state
        self.incoming_edges: List[Tuple['SlidingWindowNode', Event]] = []
        self.outgoing_edges: List[Tuple['SlidingWindowNode', Event]] = []
        self.R_s: Set[str] = set()  # Processes that have contributed successors
        self.is_redundant = False

    def add_incoming_edge(self, from_node: 'SlidingWindowNode', event: Event):
        """Add incoming edge from another node via event."""
        self.incoming_edges.append((from_node, event))

    def add_outgoing_edge(self, to_node: 'SlidingWindowNode', event: Event):
        """Add outgoing edge to another node via event."""
        self.outgoing_edges.append((to_node, event))

    def __repr__(self):
        return f"Node({self.node_id}, frontier={[str(f) for f in self.frontier]})"


class SlidingWindowGraph:
    """
    Implements the sliding window graph algorithm from the paper.
    Manages frontier nodes and handles backward propagation of independent events.
    """

    def __init__(self, num_processes: int):
        self.num_processes = num_processes
        self.nodes: Dict[str, SlidingWindowNode] = {}
        self.maximal_node: Optional[SlidingWindowNode] = None
        self.logger = get_logger()
        self.node_counter = 0
        self.P = set(f"P{i + 1}" for i in range(num_processes))  # Set of all processes

    def _generate_node_id(self) -> str:
        """Generate unique node ID."""
        self.node_counter += 1
        return f"s{self.node_counter}"

    def _frontier_to_key(self, frontier: List[Any]) -> str:
        """Convert frontier to string key for node lookup."""
        key_parts = []
        for component in frontier:
            if isinstance(component, Event):
                key_parts.append(f"E:{component.name}")
            elif isinstance(component, ProcessModes):
                key_parts.append(f"M:{component.name}")
            else:
                key_parts.append(f"U:{str(component)}")
        return "|".join(key_parts)

    def _create_successor_frontier(self, current_frontier: List[Any], event: Event) -> List[Any]:
        """
        Create successor frontier by applying event to current frontier.
        Implements the frontier successor procedure from the paper.
        """
        # Start with current frontier + new event
        new_frontier = list(current_frontier)

        # Apply event to involved processes
        for i, process_name in enumerate([f"P{j + 1}" for j in range(self.num_processes)]):
            if process_name in event.processes:
                # Replace the component for this process with the new event
                new_frontier[i] = event

        return new_frontier

    def _are_events_independent(self, event1: Event, event2: Event) -> bool:
        """Check if two events are independent (disjoint process sets)."""
        set1 = set(event1.processes) if hasattr(event1, 'processes') else set()
        set2 = set(event2.processes) if hasattr(event2, 'processes') else set()
        return len(set1.intersection(set2)) == 0

    def add_new_event(self, event: Event) -> List[SlidingWindowNode]:
        """
        Process new event according to the paper's algorithm:
        1. Add direct edge
        2. Backward propagation via depth-first search
        3. Remove redundant nodes
        """
        self.logger.debug(f"Adding new event '{event.name}' to sliding window graph.", LogCategory.STATE)

        # Step 1: Add direct edge
        new_nodes = self._add_direct_edge(event)

        # Step 2: Backward propagation
        self._perform_backward_propagation(event)

        # Step 3: Remove redundant nodes
        self._remove_redundant_nodes()

        return new_nodes

    def _add_direct_edge(self, event: Event) -> List[SlidingWindowNode]:
        """Add direct edge s_m --event--> s_n where s_m is maximal frontier."""
        if self.maximal_node is None:
            # Initialize with IOTA frontier
            initial_frontier = [ProcessModes.IOTA] * self.num_processes
            self.maximal_node = self.create_or_get_node(initial_frontier)

        # Create new maximal frontier
        new_frontier = self._create_successor_frontier(self.maximal_node.frontier, event)
        new_node = self.create_or_get_node(new_frontier)

        # Add edge
        self._add_edge(self.maximal_node, new_node, event)

        # Update maximal node
        previous_maximal = self.maximal_node
        self.maximal_node = new_node

        self.logger.debug(
            f"Added direct edge: {previous_maximal.node_id} --{event.name}--> {new_node.node_id}",
            LogCategory.STATE
        )

        return [new_node]

    def create_or_get_node(self, frontier: List[Any]) -> SlidingWindowNode:
        """Create new node or return existing node with same frontier."""
        frontier_key = self._frontier_to_key(frontier)

        if frontier_key in self.nodes:
            return self.nodes[frontier_key]

        node_id = self._generate_node_id()
        new_node = SlidingWindowNode(node_id, list(frontier))
        self.nodes[frontier_key] = new_node

        self.logger.trace(f"Created new node {node_id} with frontier {[str(f) for f in frontier]}", LogCategory.STATE)
        return new_node

    def _add_edge(self, from_node: SlidingWindowNode, to_node: SlidingWindowNode, event: Event):
        """Add edge between nodes."""
        from_node.add_outgoing_edge(to_node, event)
        to_node.add_incoming_edge(from_node, event)

        # Update R_s for redundancy tracking
        for process_name in event.processes:
            from_node.R_s.add(process_name)

    def _perform_backward_propagation(self, new_event: Event):
        """
        Perform depth-first backward propagation exactly as described in the paper (pages 9-10).
        Search from s_m (previous maximal node) backwards to find edge patterns:
        s --α--> s' --β--> s'' where α and β are independent.
        Then create commutative paths: s --β--> r --α--> s''.
        """
        if self.maximal_node is None:
            return

        # Find the previous maximal node (the one that had the direct edge added)
        previous_maximal = None
        for prev_node, event in self.maximal_node.incoming_edges:
            if event is new_event:
                previous_maximal = prev_node
                break

        if previous_maximal is None:
            self.logger.debug("No previous maximal node found for backward propagation", LogCategory.STATE)
            return

        self.logger.debug(f"Starting backward propagation from previous maximal node {previous_maximal.node_id}",
                          LogCategory.STATE)
        visited = set()
        self._dfs_search_for_edge_patterns(previous_maximal, new_event, visited)

    def _dfs_search_for_edge_patterns(self, current_node: SlidingWindowNode, new_event: Event, visited: Set[str]):
        """
        Depth-first search to find edge patterns as described in the paper.
        Look for patterns: s --α--> s' --β--> s'' where α and β are independent,
        and β is the new_event we just added.
        """
        if current_node.node_id in visited:
            return

        visited.add(current_node.node_id)
        self.logger.trace(f"DFS visiting node {current_node.node_id} looking for patterns with {new_event.name}",
                          LogCategory.STATE)

        # Look for edge patterns: current_node --α--> s' --β--> s''
        # where β is new_event and α, β are independent
        self._find_and_create_commutative_patterns(current_node, new_event)

        # Continue DFS recursively to all predecessor nodes
        for prev_node, _ in current_node.incoming_edges:
            self._dfs_search_for_edge_patterns(prev_node, new_event, visited)

    def _find_and_create_commutative_patterns(self, s_node: SlidingWindowNode, beta_event: Event):
        """
        Find edge patterns s --α--> s' --β--> s'' where α and β are independent.
        Create commutative path s --β--> r --α--> s'' for each such pattern found.
        """
        # For each outgoing edge from s_node: s --α--> s'
        for s_prime, alpha_event in s_node.outgoing_edges:
            # For each outgoing edge from s': s' --β--> s''
            for s_double_prime, beta_in_pattern in s_prime.outgoing_edges:
                # Check if this forms the pattern we're looking for
                if (beta_in_pattern is beta_event and
                        self._are_events_independent(alpha_event, beta_event)):
                    self.logger.trace(
                        f"Found commutative pattern: {s_node.node_id} --{alpha_event.name}--> "
                        f"{s_prime.node_id} --{beta_event.name}--> {s_double_prime.node_id}",
                        LogCategory.STATE
                    )

                    # Create commutative path: s --β--> r --α--> s''
                    self._create_commutative_path_exact(s_node, alpha_event, beta_event, s_double_prime)

    def _create_commutative_path_exact(self, s_node: SlidingWindowNode, alpha: Event, beta: Event,
                                       s_double_prime: SlidingWindowNode):
        """
        Create commutative path exactly as described in paper:
        Given pattern s --α--> s' --β--> s'', create s --β--> r --α--> s''
        where α and β are independent events.
        """
        # Create intermediate node r by applying β to s
        r_frontier = self._create_successor_frontier(s_node.frontier, beta)
        r_node = self.create_or_get_node(r_frontier)

        # Add edges for commutative path if they don't already exist
        if not self._edge_exists(s_node, r_node, beta):
            self._add_edge(s_node, r_node, beta)
            self.logger.trace(f"Added edge: {s_node.node_id} --{beta.name}--> {r_node.node_id}", LogCategory.STATE)

        if not self._edge_exists(r_node, s_double_prime, alpha):
            self._add_edge(r_node, s_double_prime, alpha)
            self.logger.trace(f"Added edge: {r_node.node_id} --{alpha.name}--> {s_double_prime.node_id}",
                              LogCategory.STATE)

        self.logger.debug(
            f"Created commutative path: {s_node.node_id} --{beta.name}--> "
            f"{r_node.node_id} --{alpha.name}--> {s_double_prime.node_id}",
            LogCategory.STATE
        )

    def _edge_exists(self, from_node: SlidingWindowNode, to_node: SlidingWindowNode, event: Event) -> bool:
        """Check if edge already exists between nodes."""
        return any(
            target_node is to_node and edge_event is event
            for target_node, edge_event in from_node.outgoing_edges
        )

    def _remove_redundant_nodes(self):
        """
        Remove redundant nodes according to the paper's conditions:
        1. R_s = P (all processes have contributed successors)
        2. If s --alpha--> s' and s' is redundant, then s is also redundant

        Note: Be conservative - don't remove the maximal node or recently created nodes
        """
        redundant_nodes = []

        # Find nodes where R_s = P (but preserve maximal node and essential nodes)
        for node in self.nodes.values():
            if node is self.maximal_node:
                continue  # Never remove maximal node

            # Be conservative: don't remove nodes that still have useful outgoing edges
            if len(node.outgoing_edges) > 0:
                continue  # Keep nodes that connect to other nodes

            if len(node.R_s) >= len(self.P):  # All processes have contributed
                node.is_redundant = True
                redundant_nodes.append(node)

        # Propagate redundancy backwards (conservatively)
        changed = True
        iteration = 0
        while changed and iteration < 5:  # Limit iterations to prevent over-removal
            changed = False
            iteration += 1

            for node in self.nodes.values():
                if not node.is_redundant and node is not self.maximal_node:
                    # Check if all successors are redundant AND node has successors
                    if (node.outgoing_edges and
                            len(node.outgoing_edges) > 1 and  # Only if multiple successors
                            all(target_node.is_redundant for target_node, _ in node.outgoing_edges)):
                        node.is_redundant = True
                        redundant_nodes.append(node)
                        changed = True

        # Remove redundant nodes (but keep at least one node)
        if len(self.nodes) - len(redundant_nodes) > 0:
            for redundant_node in redundant_nodes:
                self._remove_node(redundant_node)

            if redundant_nodes:
                self.logger.debug(
                    f"Removed {len(redundant_nodes)} redundant nodes: {[n.node_id for n in redundant_nodes]}",
                    LogCategory.STATE
                )
        else:
            self.logger.debug("Skipping node removal to preserve graph structure", LogCategory.STATE)

    def _remove_node(self, node: SlidingWindowNode):
        """Remove node and all its edges from the graph."""
        # Remove incoming edges to this node
        for prev_node, _ in node.incoming_edges:
            prev_node.outgoing_edges = [
                (target, event) for target, event in prev_node.outgoing_edges
                if target is not node
            ]

        # Remove outgoing edges from this node
        for next_node, _ in node.outgoing_edges:
            next_node.incoming_edges = [
                (source, event) for source, event in next_node.incoming_edges
                if source is not node
            ]

        # Remove from nodes dict
        frontier_key = self._frontier_to_key(node.frontier)
        if frontier_key in self.nodes:
            del self.nodes[frontier_key]

        self.logger.trace(f"Removed redundant node {node.node_id}", LogCategory.STATE)

    def get_all_nodes(self) -> List[SlidingWindowNode]:
        """Return all non-redundant nodes in the graph."""
        return [node for node in self.nodes.values() if not node.is_redundant]

    def get_maximal_node(self) -> Optional[SlidingWindowNode]:
        """Return the current maximal node."""
        return self.maximal_node
