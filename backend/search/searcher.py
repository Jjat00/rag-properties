"""Semantic search engine: builds Qdrant filters from parsed queries and runs vector search."""

import logging
import time

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchText,
    MatchValue,
    Range,
)

from embeddings.base import EmbeddingProvider
from ingestion.location_normalizer import resolve_city_alias, resolve_state_alias
from search.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# Maps every possible LLM output to the exact values stored in Qdrant payloads.
# If the LLM output already matches a payload value exactly, it won't be here
# and _build_filter falls through to a simple MatchValue.
PROPERTY_TYPE_ALIASES: dict[str, list[str]] = {
    # Generic "Terreno" → all subtypes
    "Terreno": ["Terreno residencial", "Terreno comercial", "Terreno industrial"],
    # Generic "Casa" → all casa subtypes
    "Casa": ["Casa", "Casa en condominio", "Casa uso de suelo"],
    # Generic "Local" → all local subtypes
    "Local": ["Local", "Local en centro comercial"],
    # User/LLM says "Bodega" but data has "Bodega comercial"
    "Bodega": ["Bodega comercial", "Nave industrial"],
    # User says "Nave" but data has "Nave industrial"
    "Nave": ["Nave industrial"],
    "Nave industrial": ["Nave industrial"],
    # User/LLM says "Penthouse" / "PH" / "Pent house"
    "Penthouse": ["PH"],
    "Pent house": ["PH"],
    "PH": ["PH"],
    # User says "Rancho" / "Hacienda" / "Quinta" but data has "Finca"
    "Rancho": ["Finca"],
    "Hacienda": ["Finca"],
    "Quinta": ["Finca"],
    "Finca": ["Finca"],
    # Explicit subtypes — match themselves exactly via MatchAny
    "Terreno residencial": ["Terreno residencial"],
    "Terreno comercial": ["Terreno comercial"],
    "Terreno industrial": ["Terreno industrial"],
    "Casa en condominio": ["Casa en condominio"],
    "Casa uso de suelo": ["Casa uso de suelo"],
    "Local en centro comercial": ["Local en centro comercial"],
    "Bodega comercial": ["Bodega comercial"],
    # These match exactly in data, but list them for completeness
    "Departamento": ["Departamento"],
    "Oficina": ["Oficina"],
    "Edificio": ["Edificio"],
}

# Maps LLM condition output to exact values in Qdrant payloads.
CONDITION_ALIASES: dict[str, list[str]] = {
    "Excelente": ["Excelente"],
    "Bueno": ["Bueno"],
    "Regular": ["Regular"],
    "Malo": ["Malo"],
    "Para remodelar": ["Para remodelar"],
    "Remodelado": ["Remodelado"],
    # Possible LLM outputs that don't match exactly
    "Nuevo": ["Excelente"],
    "Nueva": ["Excelente"],
}


class PropertyResult(BaseModel):
    """A single property returned from search."""

    score: float
    id: str | None = None
    title: str | None = None
    property_type: str | None = None
    operation: str | None = None
    price: float | None = None
    currency: str | None = None
    city: str | None = None
    state: str | None = None
    neighborhood: str | None = None
    address: str | None = None
    bedrooms: float | None = None
    bathrooms: float | None = None
    surface: float | None = None
    roofed_surface: float | None = None
    condition: str | None = None
    internal_id: str | None = None
    agent_first_name: str | None = None
    agent_last_name: str | None = None
    agent_company: str | None = None
    agent_phone: str | None = None
    address_name: str | None = None


class SearchMetrics(BaseModel):
    """Performance and score metrics for a search."""

    parse_time_ms: float = 0.0
    embed_time_ms: float = 0.0
    search_time_ms: float = 0.0
    total_time_ms: float = 0.0
    candidates_before_filter: int = 0
    score_min: float = 0.0
    score_max: float = 0.0
    score_avg: float = 0.0


class SearchResult(BaseModel):
    """Full search response including parsed filters and results."""

    query: str
    parsed_filters: ParsedQuery
    filters_applied: bool
    results: list[PropertyResult]
    total: int
    metrics: SearchMetrics = SearchMetrics()


def _normalize_parsed_locations(parsed: ParsedQuery) -> tuple[ParsedQuery, list[str] | None]:
    """Apply static alias resolution to the LLM-extracted locations.

    Returns the updated ParsedQuery and an optional list of city variants for MatchAny.
    """
    city_variants: list[str] | None = None
    if parsed.state:
        resolved = resolve_state_alias(parsed.state)
        if resolved:
            parsed.state = resolved
    if parsed.city:
        city_variants = resolve_city_alias(parsed.city)
    return parsed, city_variants


def _build_filter(parsed: ParsedQuery, city_variants: list[str] | None = None) -> Filter | None:
    """Build a Qdrant Filter from the parsed query fields."""
    conditions: list[FieldCondition] = []

    # City: use MatchAny if aliases resolved to multiple values
    if city_variants:
        conditions.append(
            FieldCondition(key="city", match=MatchAny(any=city_variants))
        )
    elif parsed.city:
        conditions.append(
            FieldCondition(key="city", match=MatchValue(value=parsed.city))
        )
    if parsed.state:
        conditions.append(
            FieldCondition(key="state", match=MatchValue(value=parsed.state))
        )
    if parsed.property_type:
        type_variants = PROPERTY_TYPE_ALIASES.get(parsed.property_type)
        if type_variants:
            conditions.append(
                FieldCondition(key="property_type", match=MatchAny(any=type_variants))
            )
        else:
            conditions.append(
                FieldCondition(
                    key="property_type", match=MatchValue(value=parsed.property_type)
                )
            )
    if parsed.operation:
        conditions.append(
            FieldCondition(key="operation", match=MatchValue(value=parsed.operation))
        )
    if parsed.condition:
        cond_variants = CONDITION_ALIASES.get(parsed.condition)
        if cond_variants:
            conditions.append(
                FieldCondition(key="condition", match=MatchAny(any=cond_variants))
            )
        else:
            conditions.append(
                FieldCondition(key="condition", match=MatchValue(value=parsed.condition))
            )
    if parsed.currency:
        conditions.append(
            FieldCondition(key="currency", match=MatchValue(value=parsed.currency))
        )

    # Neighborhood: NOT used as a hard filter.
    # Users mix colonias, landmarks, addresses and zones — too unreliable for exact match.
    # The embedding already contains neighborhood text, so vector search handles it.

    # Range filters for numeric fields
    if parsed.min_bedrooms is not None or parsed.max_bedrooms is not None:
        conditions.append(
            FieldCondition(
                key="bedrooms",
                range=Range(
                    gte=float(parsed.min_bedrooms) if parsed.min_bedrooms is not None else None,
                    lte=float(parsed.max_bedrooms) if parsed.max_bedrooms is not None else None,
                ),
            )
        )
    if parsed.min_bathrooms is not None or parsed.max_bathrooms is not None:
        conditions.append(
            FieldCondition(
                key="bathrooms",
                range=Range(
                    gte=float(parsed.min_bathrooms) if parsed.min_bathrooms is not None else None,
                    lte=float(parsed.max_bathrooms) if parsed.max_bathrooms is not None else None,
                ),
            )
        )
    if parsed.min_price is not None or parsed.max_price is not None:
        conditions.append(
            FieldCondition(
                key="price",
                range=Range(
                    gte=parsed.min_price,
                    lte=parsed.max_price,
                ),
            )
        )
    if parsed.min_surface is not None or parsed.max_surface is not None:
        conditions.append(
            FieldCondition(
                key="surface",
                range=Range(
                    gte=parsed.min_surface,
                    lte=parsed.max_surface,
                ),
            )
        )

    if not conditions:
        return None
    return Filter(must=conditions)


class Searcher:
    """Runs semantic search with pre-filtering on Qdrant."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        provider: EmbeddingProvider,
        top_k: int = 10,
    ) -> None:
        self._client = client
        self._provider = provider
        self._top_k = top_k

    async def search(
        self,
        query: str,
        parsed: ParsedQuery,
        top_k: int | None = None,
        parse_time_ms: float = 0.0,
    ) -> SearchResult:
        """Execute the full search pipeline: normalize → filter → embed → query."""
        total_start = time.perf_counter()
        k = top_k or self._top_k

        # Normalize locations extracted by LLM
        parsed, city_variants = _normalize_parsed_locations(parsed)

        # Build Qdrant filter
        qdrant_filter = _build_filter(parsed, city_variants)
        filters_applied = qdrant_filter is not None

        if filters_applied:
            logger.info("Qdrant filter: %s", qdrant_filter.model_dump(exclude_none=True))

        # Get total points in collection (candidates before filtering)
        collection_info = await self._client.get_collection(self._provider.collection_name)
        candidates_before_filter = collection_info.indexed_vectors_count or 0

        # Embed the full user query
        embed_start = time.perf_counter()
        query_vector = await self._provider.embed_query(parsed.semantic_query)
        embed_time_ms = (time.perf_counter() - embed_start) * 1000

        # Search in Qdrant
        search_start = time.perf_counter()
        results = await self._client.query_points(
            collection_name=self._provider.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=k,
            with_payload=True,
        )
        search_time_ms = (time.perf_counter() - search_start) * 1000

        # Format results
        properties: list[PropertyResult] = []
        for point in results.points:
            payload = point.payload or {}
            properties.append(
                PropertyResult(
                    score=point.score,
                    id=payload.get("id"),
                    title=payload.get("title"),
                    property_type=payload.get("property_type"),
                    operation=payload.get("operation"),
                    price=payload.get("price"),
                    currency=payload.get("currency"),
                    city=payload.get("city"),
                    state=payload.get("state"),
                    neighborhood=payload.get("neighborhood"),
                    address=payload.get("address"),
                    bedrooms=payload.get("bedrooms"),
                    bathrooms=payload.get("bathrooms"),
                    surface=payload.get("surface"),
                    roofed_surface=payload.get("roofed_surface"),
                    condition=payload.get("condition"),
                    internal_id=payload.get("internal_id"),
                    agent_first_name=payload.get("agent_first_name"),
                    agent_last_name=payload.get("agent_last_name"),
                    agent_company=payload.get("agent_company"),
                    agent_phone=payload.get("agent_phone"),
                    address_name=payload.get("address_name"),
                )
            )

        # Compute score stats
        scores = [p.score for p in properties]
        total_time_ms = (time.perf_counter() - total_start) * 1000

        metrics = SearchMetrics(
            parse_time_ms=round(parse_time_ms, 2),
            embed_time_ms=round(embed_time_ms, 2),
            search_time_ms=round(search_time_ms, 2),
            total_time_ms=round(total_time_ms + parse_time_ms, 2),
            candidates_before_filter=candidates_before_filter,
            score_min=round(min(scores), 4) if scores else 0.0,
            score_max=round(max(scores), 4) if scores else 0.0,
            score_avg=round(sum(scores) / len(scores), 4) if scores else 0.0,
        )

        return SearchResult(
            query=query,
            parsed_filters=parsed,
            filters_applied=filters_applied,
            results=properties,
            total=len(properties),
            metrics=metrics,
        )
