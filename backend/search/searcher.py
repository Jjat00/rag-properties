"""Semantic search engine: builds Qdrant filters from parsed queries and runs vector search."""

import asyncio
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


class FacetBucket(BaseModel):
    """A single value and its count from a faceted field."""

    value: str
    count: int


class DisambiguationInfo(BaseModel):
    """Breakdown of ambiguous filters by actual values in the catalog."""

    field: str
    buckets: list[FacetBucket]


class SearchResult(BaseModel):
    """Full search response including parsed filters and results."""

    query: str
    parsed_filters: ParsedQuery
    filters_applied: bool
    results: list[PropertyResult]
    total: int
    metrics: SearchMetrics = SearchMetrics()
    disambiguation: list[DisambiguationInfo] = []


def _normalize_parsed_locations(parsed: ParsedQuery) -> tuple[ParsedQuery, list[str]]:
    """Apply static alias resolution to the LLM-extracted locations.

    Returns the updated ParsedQuery and a merged list of all city variants for MatchAny.
    """
    if parsed.state:
        resolved = resolve_state_alias(parsed.state)
        if resolved:
            parsed.state = resolved

    # Resolve each city through aliases → merge into a single deduplicated list
    all_city_variants: list[str] = []
    for city in parsed.cities:
        resolved = resolve_city_alias(city)
        if resolved:
            all_city_variants.extend(resolved)
        else:
            all_city_variants.append(city)
    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for v in all_city_variants:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return parsed, deduped


class _FilterMeta:
    """Tracks which fields expanded to multiple values (candidates for disambiguation)."""

    def __init__(self) -> None:
        self.expanded_type_variants: list[str] = []
        self.expanded_city_variants: list[str] = []


def _build_filter(
    parsed: ParsedQuery,
    city_variants: list[str] | None = None,
) -> tuple[Filter | None, _FilterMeta]:
    """Build a Qdrant Filter from the parsed query fields.

    Uses must for hard filters and should for soft text-match filters
    (street, neighborhoods) that boost but don't exclude.

    Returns the filter and metadata about which fields expanded to multiple values.
    """
    must_conditions: list[FieldCondition] = []
    should_conditions: list[FieldCondition] = []
    meta = _FilterMeta()

    # --- MUST conditions (hard filters) ---

    # Cities: MatchAny with the union of all resolved variants
    if city_variants:
        must_conditions.append(
            FieldCondition(key="city", match=MatchAny(any=city_variants))
        )
        if len(city_variants) > 1:
            meta.expanded_city_variants = city_variants

    if parsed.state:
        must_conditions.append(
            FieldCondition(key="state", match=MatchValue(value=parsed.state))
        )

    # Property types: union all aliases for each type mentioned
    if parsed.property_types:
        all_type_variants: list[str] = []
        for pt in parsed.property_types:
            type_variants = PROPERTY_TYPE_ALIASES.get(pt)
            if type_variants:
                all_type_variants.extend(type_variants)
            else:
                all_type_variants.append(pt)
        # Deduplicate
        all_type_variants = list(dict.fromkeys(all_type_variants))
        must_conditions.append(
            FieldCondition(key="property_type", match=MatchAny(any=all_type_variants))
        )
        if len(all_type_variants) > 1:
            meta.expanded_type_variants = all_type_variants

    if parsed.operation:
        must_conditions.append(
            FieldCondition(key="operation", match=MatchValue(value=parsed.operation))
        )
    if parsed.condition:
        cond_variants = CONDITION_ALIASES.get(parsed.condition)
        if cond_variants:
            must_conditions.append(
                FieldCondition(key="condition", match=MatchAny(any=cond_variants))
            )
        else:
            must_conditions.append(
                FieldCondition(key="condition", match=MatchValue(value=parsed.condition))
            )
    if parsed.currency:
        must_conditions.append(
            FieldCondition(key="currency", match=MatchValue(value=parsed.currency))
        )

    # Range filters for numeric fields
    if parsed.min_bedrooms is not None or parsed.max_bedrooms is not None:
        must_conditions.append(
            FieldCondition(
                key="bedrooms",
                range=Range(
                    gte=float(parsed.min_bedrooms) if parsed.min_bedrooms is not None else None,
                    lte=float(parsed.max_bedrooms) if parsed.max_bedrooms is not None else None,
                ),
            )
        )
    if parsed.min_bathrooms is not None or parsed.max_bathrooms is not None:
        must_conditions.append(
            FieldCondition(
                key="bathrooms",
                range=Range(
                    gte=float(parsed.min_bathrooms) if parsed.min_bathrooms is not None else None,
                    lte=float(parsed.max_bathrooms) if parsed.max_bathrooms is not None else None,
                ),
            )
        )
    if parsed.min_price is not None or parsed.max_price is not None:
        must_conditions.append(
            FieldCondition(
                key="price",
                range=Range(
                    gte=parsed.min_price,
                    lte=parsed.max_price,
                ),
            )
        )
    if parsed.min_surface is not None or parsed.max_surface is not None:
        must_conditions.append(
            FieldCondition(
                key="surface",
                range=Range(
                    gte=parsed.min_surface,
                    lte=parsed.max_surface,
                ),
            )
        )
    if parsed.min_roofed_surface is not None or parsed.max_roofed_surface is not None:
        must_conditions.append(
            FieldCondition(
                key="roofed_surface",
                range=Range(
                    gte=parsed.min_roofed_surface,
                    lte=parsed.max_roofed_surface,
                ),
            )
        )

    # --- SHOULD conditions (soft text-match filters) ---

    # Street: MatchText on address and title
    if parsed.street:
        should_conditions.append(
            FieldCondition(key="address", match=MatchText(text=parsed.street))
        )
        should_conditions.append(
            FieldCondition(key="title", match=MatchText(text=parsed.street))
        )

    # Neighborhoods: MatchText on neighborhood and title for each
    for nb in parsed.neighborhoods:
        should_conditions.append(
            FieldCondition(key="neighborhood", match=MatchText(text=nb))
        )
        should_conditions.append(
            FieldCondition(key="title", match=MatchText(text=nb))
        )

    if not must_conditions and not should_conditions:
        return None, meta

    # Build filter combining must and should
    # When must + should: Qdrant requires all must AND at least one should
    # When only should: requires at least one should
    # When only must: just the must conditions
    return Filter(
        must=must_conditions if must_conditions else None,
        should=should_conditions if should_conditions else None,
    ), meta


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

    async def _facet_field(
        self,
        field: str,
        variants: list[str],
        base_filter: Filter | None,
    ) -> DisambiguationInfo | None:
        """Count occurrences per value of a field using Qdrant count().

        Runs one count() call per variant in parallel and returns a DisambiguationInfo
        with only non-zero buckets. Returns None if fewer than 2 buckets have results.
        """
        async def _count_value(value: str) -> FacetBucket:
            value_condition = FieldCondition(key=field, match=MatchValue(value=value))
            # Combine with existing base filter must conditions
            must = list(base_filter.must) if base_filter and base_filter.must else []
            # Remove the original MatchAny for this field (we're counting per value)
            must = [c for c in must if not (isinstance(c, FieldCondition) and c.key == field)]
            must.append(value_condition)
            count_filter = Filter(
                must=must,
                should=base_filter.should if base_filter and base_filter.should else None,
            )
            result = await self._client.count(
                collection_name=self._provider.collection_name,
                count_filter=count_filter,
                exact=False,
            )
            return FacetBucket(value=value, count=result.count)

        buckets = await asyncio.gather(*[_count_value(v) for v in variants])
        non_zero = [b for b in buckets if b.count > 0]

        if len(non_zero) < 2:
            return None

        # Sort by count descending
        non_zero.sort(key=lambda b: b.count, reverse=True)
        return DisambiguationInfo(field=field, buckets=non_zero)

    async def search(
        self,
        query: str,
        parsed: ParsedQuery,
        top_k: int | None = None,
        parse_time_ms: float = 0.0,
    ) -> SearchResult:
        """Execute the full search pipeline: normalize → filter → embed → query → disambiguate."""
        total_start = time.perf_counter()
        k = top_k or self._top_k

        # Normalize locations extracted by LLM
        parsed, city_variants = _normalize_parsed_locations(parsed)

        # Build Qdrant filter
        qdrant_filter, filter_meta = _build_filter(parsed, city_variants)
        filters_applied = qdrant_filter is not None

        if filters_applied:
            logger.info("Qdrant filter: %s", qdrant_filter.model_dump(exclude_none=True))

        # Get total points in collection (candidates before filtering)
        collection_info = await self._client.get_collection(self._provider.collection_name)
        candidates_before_filter = collection_info.indexed_vectors_count or 0

        # Embed the full user query
        embed_start = time.perf_counter()
        embed_text = parsed.clean_query or parsed.semantic_query
        query_vector = await self._provider.embed_query(embed_text)
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

        # Disambiguation: facet ambiguous fields in parallel
        disambiguation: list[DisambiguationInfo] = []
        facet_tasks = []
        if filter_meta.expanded_type_variants:
            facet_tasks.append(
                self._facet_field("property_type", filter_meta.expanded_type_variants, qdrant_filter)
            )
        if filter_meta.expanded_city_variants:
            facet_tasks.append(
                self._facet_field("city", filter_meta.expanded_city_variants, qdrant_filter)
            )
        if facet_tasks:
            facet_results = await asyncio.gather(*facet_tasks)
            disambiguation = [r for r in facet_results if r is not None]

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
            disambiguation=disambiguation,
        )
