"""Agent state definition for the conversational property search agent."""

from typing import Any

from langgraph.graph import MessagesState

from search.searcher import DisambiguationInfo, PropertyResult, SearchMetrics


class AgentState(MessagesState):
    """Extended MessagesState with search-related fields.

    These fields are updated by the search tool and read by the frontend
    via SSE events to update the properties panel.
    """

    latest_results: list[PropertyResult]
    latest_filters: dict[str, Any]
    latest_disambiguation: list[DisambiguationInfo]
    latest_state_results: dict[str, list[PropertyResult]]
    latest_metrics: SearchMetrics | None
    search_count: int
