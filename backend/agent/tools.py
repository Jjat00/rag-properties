"""Search tool for the conversational agent."""

import json
import logging
import time

from langchain_core.tools import tool

from config import EmbeddingModel
from embeddings.registry import EmbeddingRegistry
from search.query_parser import QueryParser
from search.searcher import Searcher
from vectorstore.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


def create_search_tool(
    query_parser: QueryParser,
    embedding_registry: EmbeddingRegistry,
    qdrant_manager: QdrantManager,
    model: EmbeddingModel,
    top_k: int = 10,
):
    """Factory that creates a search_properties tool with runtime dependencies."""

    @tool
    async def search_properties(query: str) -> str:
        """Search for real estate properties in the Mexican catalog.

        Use this tool to find properties based on natural language queries.
        The query should include all relevant criteria: property type, location,
        bedrooms, bathrooms, price range, etc.

        Args:
            query: Natural language search query, e.g. "casa de 3 recámaras en Polanco menos de 10 millones"
        """
        parse_start = time.perf_counter()
        parsed = await query_parser.parse(query)
        parse_time_ms = (time.perf_counter() - parse_start) * 1000

        provider = embedding_registry.get(model)
        searcher = Searcher(
            client=qdrant_manager.client,
            provider=provider,
            top_k=top_k,
        )

        result = await searcher.search(query, parsed, parse_time_ms=parse_time_ms)

        # Build a concise summary for the agent
        summary_parts = [f"Total: {result.total} resultados."]
        if result.results:
            prices = [r.price for r in result.results if r.price]
            if prices:
                summary_parts.append(
                    f"Precios: ${min(prices):,.0f} - ${max(prices):,.0f}."
                )
            types = set(r.property_type for r in result.results if r.property_type)
            if types:
                summary_parts.append(f"Tipos: {', '.join(sorted(types))}.")
            locations = set(
                f"{r.city}, {r.state}"
                for r in result.results
                if r.city and r.state
            )
            if locations:
                summary_parts.append(f"Ubicaciones: {'; '.join(sorted(locations))}.")

        if result.disambiguation:
            for d in result.disambiguation:
                bucket_str = ", ".join(
                    f"{b.value} ({b.count})" for b in d.buckets[:5]
                )
                summary_parts.append(f"Desambiguación [{d.field}]: {bucket_str}.")

        summary = " ".join(summary_parts)

        # Return structured data as JSON for the agent to reason over
        # and for the frontend to parse from tool results
        return json.dumps(
            {
                "summary": summary,
                "total": result.total,
                "results": [r.model_dump() for r in result.results],
                "parsed_filters": result.parsed_filters.model_dump(exclude_none=True),
                "disambiguation": [d.model_dump() for d in result.disambiguation],
                "state_results": {
                    k: [r.model_dump() for r in v]
                    for k, v in result.state_results.items()
                },
                "metrics": result.metrics.model_dump(),
            },
            ensure_ascii=False,
        )

    return search_properties
