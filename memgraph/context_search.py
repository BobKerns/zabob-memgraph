"""
Context-aware graph search with parallel attention heads.

Implements multi-agent context management where each agent maintains
a set of relevant starting nodes and searches outward with shared
visited tracking.

Utility in Complex Domains:

This context-based search approach addresses a fundamental challenge in
AI agent systems: how to provide relevant information without overwhelming
the agent with the entire knowledge graph.

In complex domains, exhaustive search is intractable. Consider:
- A software codebase with thousands of files and functions
- A research corpus with millions of papers and citations
- A VFX pipeline with thousands of assets, shots, and tasks
- A game design with hundreds of mechanics, items, and interactions

Context provides locality bias - most work is local to a specific area.
When debugging authentication, you don't need the entire codebase, just
the authentication module's neighborhood in the dependency graph.

Parallel Search Heads (Attention Mechanism):

Like transformer attention heads operating on token positions, these
search heads operate on graph positions. Each explores independently
but shares visited tracking, providing:

1. Scalability - O(E + V) per head, embarrassingly parallel
2. Incremental results - Early termination when enough matches found
3. Resumability - "Search harder" expands from saved state
4. Distance weighting - Natural relevance ranking by graph proximity

Multi-Agent Collaboration:

Different agents can work in different contexts simultaneously:
- Agent A (frontend): Context = {UIComponents, StateManagement}
- Agent B (backend): Context = {APIs, Database}
- Shared visited set prevents duplicate exploration
- Each maintains focus on their domain of concern

Domain-Specific Terminology:

The same graph structure supports different conceptual models:
- SOP networks: data flow, geometry operations, groups
- TOP/PDG networks: task dependencies, wedging, distribution
- OBJ hierarchies: transforms, containment, instances
- Code graphs: imports, calls, inheritance

Context allows the graph traversal to adapt to domain semantics
without changing the underlying algorithm.

Integration with Vector Search:

The match_query callable can integrate with embedding-based search:
1. Generate query embedding
2. Compare against node embeddings
3. Return cosine similarity as match score
4. Distance-weighted relevance combines semantic + structural proximity

This creates a hybrid search: vector embeddings for semantic matching,
graph structure for contextual relevance.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class SearchStatus(Enum):
    """Status of a search head."""
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    PAUSED = "paused"


@dataclass
class SearchHead:
    """
    A single search head (attention head) traversing the graph.

    Maintains its own deque of nodes to visit but shares visited set
    with other heads to avoid duplicate work.
    """
    context_node_id: str
    to_visit: deque[tuple[str, int]] = field(default_factory=deque)  # (node_id, distance)
    status: SearchStatus = SearchStatus.ACTIVE
    nodes_explored: int = 0

    def __post_init__(self) -> None:
        """Initialize with the starting context node at distance 0."""
        if not self.to_visit:
            self.to_visit.append((self.context_node_id, 0))


@dataclass
class SearchResult:
    """Result from a context-aware search."""
    entity_id: str
    distance: int  # Graph distance from nearest context node
    context_node: str  # Which context node provided this result
    relevance_score: float  # Distance-weighted relevance


@dataclass
class Context:
    """
    A named context defining a set of starting nodes for search.

    Contexts can be saved, restored, and shared between agents.
    """
    name: str
    node_ids: list[str]  # Ordered list of context nodes
    search_params: dict[str, int] = field(default_factory=lambda: {
        "max_distance": 5,
        "steps_per_expansion": 10,
        "max_results": 100,
    })

    def __post_init__(self) -> None:
        """Validate context has at least one node."""
        if not self.node_ids:
            raise ValueError("Context must have at least one node")


class ContextSearch:
    """
    Parallel breadth-first search from multiple context nodes.

    Each context node spawns a search head that traverses the graph
    independently but shares visited tracking to avoid redundant work.
    """

    def __init__(
        self,
        get_neighbors: Callable[[str], list[str]],
        match_query: Callable[[str, str], float],
    ) -> None:
        """
        Initialize with graph traversal functions.

        Args:
            get_neighbors: Function to get neighbor node IDs for a given node
            match_query: Function to score how well a node matches a search query
        """
        self.get_neighbors = get_neighbors
        self.match_query = match_query

    def search(
        self,
        context: Context,
        query: str | None = None,
        resume_heads: list[SearchHead] | None = None,
    ) -> tuple[list[SearchResult], list[SearchHead]]:
        """
        Execute parallel breadth-first search from context nodes.

        Args:
            context: Context defining starting nodes and search parameters
            query: Optional query string for semantic filtering
            resume_heads: Optional list of search heads to resume (for "search harder")

        Returns:
            tuple of (search results, pausable search heads)
        """
        # Initialize or resume search heads
        if resume_heads:
            heads = resume_heads
            visited: set[str] = set()
            # Reconstruct visited set from heads
            for head in heads:
                visited.add(head.context_node_id)
        else:
            heads = [SearchHead(node_id) for node_id in context.node_ids]
            visited = set(context.node_ids)

        results: list[SearchResult] = []
        max_distance = context.search_params["max_distance"]
        steps_per_expansion = context.search_params["steps_per_expansion"]
        max_results = context.search_params["max_results"]

        context_index = 0  # Track which context node to add next
        if resume_heads:
            # When resuming, start from where we left off
            context_index = len([h for h in heads if h.status == SearchStatus.ACTIVE])

        # Main search loop
        steps_since_expansion = 0
        while any(h.status == SearchStatus.ACTIVE for h in heads):
            # Process each active head
            for head in heads:
                if head.status != SearchStatus.ACTIVE:
                    continue

                if not head.to_visit:
                    head.status = SearchStatus.EXHAUSTED
                    continue

                # Get next node from this head's deque
                current_id, distance = head.to_visit.popleft()
                head.nodes_explored += 1

                # Check if this node matches our search
                if query:
                    match_score = self.match_query(current_id, query)
                    if match_score > 0:
                        results.append(SearchResult(
                            entity_id=current_id,
                            distance=distance,
                            context_node=head.context_node_id,
                            relevance_score=self._calculate_relevance(distance, match_score),
                        ))
                else:
                    # No query - return all reachable nodes
                    results.append(SearchResult(
                        entity_id=current_id,
                        distance=distance,
                        context_node=head.context_node_id,
                        relevance_score=self._calculate_relevance(distance, 1.0),
                    ))

                # Stop if we hit result limit
                if len(results) >= max_results:
                    # Mark all heads as paused for potential resumption
                    for h in heads:
                        if h.status == SearchStatus.ACTIVE:
                            h.status = SearchStatus.PAUSED
                    return self._rank_results(results, max_results), heads

                # Expand to neighbors if within distance limit
                if distance < max_distance:
                    neighbors = self.get_neighbors(current_id)
                    for neighbor_id in neighbors:
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            head.to_visit.append((neighbor_id, distance + 1))

            # After N steps, add another context node to the search
            steps_since_expansion += 1
            if steps_since_expansion >= steps_per_expansion:
                steps_since_expansion = 0
                if context_index < len(context.node_ids):
                    # Add a new search head from the next context node
                    new_head = SearchHead(context.node_ids[context_index])
                    heads.append(new_head)
                    visited.add(context.node_ids[context_index])
                    context_index += 1

        # All heads exhausted
        return self._rank_results(results, max_results), heads

    def _calculate_relevance(self, distance: int, match_score: float) -> float:
        """
        Calculate relevance score weighted by graph distance.

        Closer nodes are more relevant. Uses exponential decay.
        """
        distance_weight = 1.0 / (2.0 ** distance)
        return match_score * distance_weight

    def _rank_results(
        self,
        results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Rank and limit results by relevance score."""
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]


class ContextManager:
    """
    Manages saved contexts for different agents and purposes.

    Contexts can be created, listed, loaded, updated, and deleted.
    """

    def __init__(self) -> None:
        """Initialize with empty context storage."""
        self.contexts: dict[str, Context] = {}

    def create_context(
        self,
        name: str,
        initial_nodes: list[str],
        search_params: dict[str, int] | None = None,
    ) -> Context:
        """Create and store a new context."""
        if name in self.contexts:
            raise ValueError(f"Context '{name}' already exists")

        context = Context(
            name=name,
            node_ids=initial_nodes,
            search_params=search_params or {},
        )
        self.contexts[name] = context
        return context

    def get_context(self, name: str) -> Context:
        """Retrieve a saved context by name."""
        if name not in self.contexts:
            raise ValueError(f"Context '{name}' not found")
        return self.contexts[name]

    def list_contexts(self) -> list[str]:
        """list all saved context names."""
        return list(self.contexts.keys())

    def expand_context(self, name: str, additional_nodes: list[str]) -> Context:
        """Add nodes to an existing context."""
        context = self.get_context(name)
        context.node_ids.extend(additional_nodes)
        return context

    def delete_context(self, name: str) -> None:
        """Remove a saved context."""
        if name not in self.contexts:
            raise ValueError(f"Context '{name}' not found")
        del self.contexts[name]
