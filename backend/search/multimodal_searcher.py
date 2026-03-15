"""Multimodal semantic search with LLM-parsed filters + cosine similarity.

Uses the same QueryParser as the playground to extract structured filters
from natural language, then runs vector search against fused embeddings.

Field mapping (QueryParser → multimodal payload):
  property_type → house_type, operation "sale"→"Venta", bedrooms → bedroom,
  bathrooms → bathroom, surface → land_area, roofed_surface → construction_area,
  neighborhood → suburb.
"""

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

from config import MULTIMODAL_COLLECTION
from embeddings.gemini_multimodal_provider import GeminiMultimodalProvider
from ingestion.location_normalizer import resolve_city_alias, resolve_state_alias
from search.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# Maps QueryParser operation values to multimodal payload values
OPERATION_MAP: dict[str, list[str]] = {
    "sale": ["Venta", "Preventa", "Venta / Alquiler", "Venta / Renta"],
    "rent": ["Renta", "Alquiler", "Venta / Alquiler", "Venta / Renta"],
}

# Maps QueryParser property_type values to multimodal house_type values
HOUSE_TYPE_ALIASES: dict[str, list[str]] = {
    "Terreno": ["Terreno"],
    "Terreno residencial": ["Terreno"],
    "Terreno comercial": ["Terreno"],
    "Terreno industrial": ["Terreno"],
    "Casa": ["Casa", "Casa en Condominio", "Casa Dúplex"],
    "Casa en condominio": ["Casa en Condominio"],
    "Casa uso de suelo": ["Casa"],
    "Departamento": ["Departamento"],
    "Oficina": ["Oficina", "Oficinas"],
    "Bodega": ["Bodega", "Bodega / Nave industrial"],
    "Bodega comercial": ["Bodega", "Bodega / Nave industrial"],
    "Nave": ["Nave Industrial", "Bodega / Nave industrial"],
    "Nave industrial": ["Nave Industrial", "Bodega / Nave industrial"],
    "Local": ["Local Comercial", "Local comercial"],
    "Local en centro comercial": ["Local Comercial", "Local comercial"],
    "PH": ["Departamento"],  # No PH in JSON data, closest is Departamento
    "Penthouse": ["Departamento"],
    "Pent house": ["Departamento"],
    "Finca": ["Rancho / Quinta", "Quinta"],
    "Rancho": ["Rancho / Quinta", "Quinta"],
    "Hacienda": ["Rancho / Quinta", "Quinta"],
    "Quinta": ["Rancho / Quinta", "Quinta"],
    "Edificio": ["Inmueble Productivo Urbano"],
}

# Maps QueryParser state values to multimodal payload values
STATE_MAP: dict[str, str] = {
    "Edo. de México": "Estado de México",
    "Estado de México": "Estado de México",
    "Estado De México": "Estado de México",
}


class MultimodalPropertyResult(BaseModel):
    """A single property from multimodal search."""

    score: float
    id: str | None = None
    firebase_id: str | None = None
    title: str | None = None
    description: str | None = None
    house_type: str | None = None
    city: str | None = None
    state: str | None = None
    suburb: str | None = None
    address: str | None = None
    street: str | None = None
    bedroom: int | None = None
    bathroom: int | None = None
    half_bathroom: int | None = None
    construction_area: float | None = None
    land_area: float | None = None
    price: float | None = None
    currency: str | None = None
    operation: str | None = None
    condition: str | None = None
    antiquity: str | None = None
    pictures: list[str] = []
    amenities: list[str] = []
    exterior_selected: list[str] = []
    general_selected: list[str] = []
    near_places: list[str] = []
    parking_lot: int | None = None
    lat: float | None = None
    lng: float | None = None
    ad_copy: str | None = None


class MultimodalSearchMetrics(BaseModel):
    parse_time_ms: float = 0.0
    embed_time_ms: float = 0.0
    search_time_ms: float = 0.0
    total_time_ms: float = 0.0
    total_candidates: int = 0
    score_min: float = 0.0
    score_max: float = 0.0
    score_avg: float = 0.0


class MultimodalSearchResult(BaseModel):
    query: str
    search_mode: str = "text"  # "text" | "image"
    parsed_filters: ParsedQuery | None = None
    filters_applied: bool = False
    results: list[MultimodalPropertyResult]
    total: int
    metrics: MultimodalSearchMetrics = MultimodalSearchMetrics()


def _normalize_parsed_locations(parsed: ParsedQuery) -> tuple[ParsedQuery, list[str]]:
    """Apply static alias resolution to the LLM-extracted locations."""
    if parsed.state:
        resolved = resolve_state_alias(parsed.state)
        if resolved:
            parsed.state = resolved
        # Also map to multimodal state values
        if parsed.state in STATE_MAP:
            parsed.state = STATE_MAP[parsed.state]

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


def _build_multimodal_filter(
    parsed: ParsedQuery,
    city_variants: list[str] | None = None,
) -> Filter | None:
    """Build Qdrant filter from ParsedQuery using multimodal field names."""
    must_conditions: list[FieldCondition | Filter] = []

    # Cities
    if city_variants:
        must_conditions.append(
            FieldCondition(key="city", match=MatchAny(any=city_variants))
        )

    # State
    if parsed.state:
        must_conditions.append(
            FieldCondition(key="state", match=MatchValue(value=parsed.state))
        )

    # Property types → house_type with alias mapping
    if parsed.property_types:
        all_type_variants: list[str] = []
        for pt in parsed.property_types:
            type_variants = HOUSE_TYPE_ALIASES.get(pt)
            if type_variants:
                all_type_variants.extend(type_variants)
            else:
                all_type_variants.append(pt)
        all_type_variants = list(dict.fromkeys(all_type_variants))
        must_conditions.append(
            FieldCondition(key="house_type", match=MatchAny(any=all_type_variants))
        )

    # Operation: map "sale"→"Venta", "rent"→"Renta"
    if parsed.operation:
        op_variants = OPERATION_MAP.get(parsed.operation)
        if op_variants:
            must_conditions.append(
                FieldCondition(key="operation", match=MatchAny(any=op_variants))
            )
        else:
            must_conditions.append(
                FieldCondition(key="operation", match=MatchValue(value=parsed.operation))
            )

    # Condition
    if parsed.condition:
        must_conditions.append(
            FieldCondition(key="condition", match=MatchValue(value=parsed.condition))
        )

    # Currency
    if parsed.currency:
        must_conditions.append(
            FieldCondition(key="currency", match=MatchValue(value=parsed.currency))
        )

    # Bedrooms → bedroom
    if parsed.min_bedrooms is not None or parsed.max_bedrooms is not None:
        must_conditions.append(
            FieldCondition(
                key="bedroom",
                range=Range(
                    gte=float(parsed.min_bedrooms) if parsed.min_bedrooms is not None else None,
                    lte=float(parsed.max_bedrooms) if parsed.max_bedrooms is not None else None,
                ),
            )
        )

    # Bathrooms → bathroom
    if parsed.min_bathrooms is not None or parsed.max_bathrooms is not None:
        must_conditions.append(
            FieldCondition(
                key="bathroom",
                range=Range(
                    gte=float(parsed.min_bathrooms) if parsed.min_bathrooms is not None else None,
                    lte=float(parsed.max_bathrooms) if parsed.max_bathrooms is not None else None,
                ),
            )
        )

    # Price
    if parsed.min_price is not None or parsed.max_price is not None:
        must_conditions.append(
            FieldCondition(
                key="price",
                range=Range(gte=parsed.min_price, lte=parsed.max_price),
            )
        )

    # Surface → land_area
    if parsed.min_surface is not None or parsed.max_surface is not None:
        must_conditions.append(
            FieldCondition(
                key="land_area",
                range=Range(gte=parsed.min_surface, lte=parsed.max_surface),
            )
        )

    # Roofed surface → construction_area
    if parsed.min_roofed_surface is not None or parsed.max_roofed_surface is not None:
        must_conditions.append(
            FieldCondition(
                key="construction_area",
                range=Range(gte=parsed.min_roofed_surface, lte=parsed.max_roofed_surface),
            )
        )

    # Street: search across address, street, suburb, title fields
    if parsed.street:
        must_conditions.append(
            Filter(should=[
                FieldCondition(key="address", match=MatchText(text=parsed.street)),
                FieldCondition(key="street", match=MatchText(text=parsed.street)),
                FieldCondition(key="suburb", match=MatchText(text=parsed.street)),
                FieldCondition(key="title", match=MatchText(text=parsed.street)),
            ])
        )

    # Neighborhoods: search across suburb, address, title
    for nb in parsed.neighborhoods:
        must_conditions.append(
            Filter(should=[
                FieldCondition(key="suburb", match=MatchText(text=nb)),
                FieldCondition(key="address", match=MatchText(text=nb)),
                FieldCondition(key="title", match=MatchText(text=nb)),
            ])
        )

    if not must_conditions:
        return None

    return Filter(must=must_conditions)


def _format_point(point: object) -> MultimodalPropertyResult:
    payload = getattr(point, "payload", None) or {}
    return MultimodalPropertyResult(
        score=getattr(point, "score", 0.0),
        id=payload.get("id"),
        firebase_id=payload.get("firebase_id"),
        title=payload.get("title"),
        description=payload.get("description"),
        house_type=payload.get("house_type"),
        city=payload.get("city"),
        state=payload.get("state"),
        suburb=payload.get("suburb"),
        address=payload.get("address"),
        street=payload.get("street"),
        bedroom=payload.get("bedroom"),
        bathroom=payload.get("bathroom"),
        half_bathroom=payload.get("half_bathroom"),
        construction_area=payload.get("construction_area"),
        land_area=payload.get("land_area"),
        price=payload.get("price"),
        currency=payload.get("currency"),
        operation=payload.get("operation"),
        condition=payload.get("condition"),
        antiquity=payload.get("antiquity"),
        pictures=payload.get("pictures", []),
        amenities=payload.get("amenities", []),
        exterior_selected=payload.get("exterior_selected", []),
        general_selected=payload.get("general_selected", []),
        near_places=payload.get("near_places", []),
        parking_lot=payload.get("parking_lot"),
        lat=payload.get("lat"),
        lng=payload.get("lng"),
        ad_copy=payload.get("ad_copy"),
    )


class MultimodalSearcher:
    """Multimodal search using LLM-parsed filters + cosine similarity.

    Reuses the same QueryParser as the playground to extract structured filters,
    then maps them to the multimodal collection's field names and runs
    a direct cosine search against fused embeddings.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        provider: GeminiMultimodalProvider,
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
    ) -> MultimodalSearchResult:
        """Search using LLM-parsed filters + cosine similarity against fused embeddings."""
        total_start = time.perf_counter()
        k = top_k or self._top_k

        # Normalize locations
        parsed, city_variants = _normalize_parsed_locations(parsed)

        # Build filter with multimodal field names
        qdrant_filter = _build_multimodal_filter(parsed, city_variants)
        filters_applied = qdrant_filter is not None

        if filters_applied:
            logger.info("Multimodal filter: %s", qdrant_filter.model_dump(exclude_none=True))

        # Embed query text (use clean_query if available)
        embed_start = time.perf_counter()
        embed_text = parsed.clean_query or parsed.semantic_query
        query_vector = await self._provider.embed_query(embed_text)
        embed_time_ms = (time.perf_counter() - embed_start) * 1000

        # Direct cosine search
        search_start = time.perf_counter()
        results = await self._client.query_points(
            collection_name=MULTIMODAL_COLLECTION,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=k,
            with_payload=True,
        )
        search_time_ms = (time.perf_counter() - search_start) * 1000

        properties = [_format_point(p) for p in results.points]

        # Total count
        count_result = await self._client.count(
            collection_name=MULTIMODAL_COLLECTION,
            count_filter=qdrant_filter,
            exact=True,
        )

        # Score stats
        scores = [p.score for p in properties]
        total_time_ms = (time.perf_counter() - total_start) * 1000

        return MultimodalSearchResult(
            query=query,
            search_mode="text",
            parsed_filters=parsed,
            filters_applied=filters_applied,
            results=properties,
            total=count_result.count,
            metrics=MultimodalSearchMetrics(
                parse_time_ms=round(parse_time_ms, 2),
                embed_time_ms=round(embed_time_ms, 2),
                search_time_ms=round(search_time_ms, 2),
                total_time_ms=round(total_time_ms + parse_time_ms, 2),
                total_candidates=count_result.count,
                score_min=round(min(scores), 4) if scores else 0.0,
                score_max=round(max(scores), 4) if scores else 0.0,
                score_avg=round(sum(scores) / len(scores), 4) if scores else 0.0,
            ),
        )

    async def search_by_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        top_k: int | None = None,
    ) -> MultimodalSearchResult:
        """Search by uploading an image (cross-modal search).

        No LLM parsing — the image is directly embedded and searched
        against fused embeddings using cosine similarity.
        """
        total_start = time.perf_counter()
        k = top_k or self._top_k

        # Embed the uploaded image as a query
        embed_start = time.perf_counter()
        query_vector = await self._provider.embed_image_query(image_bytes, mime_type)
        embed_time_ms = (time.perf_counter() - embed_start) * 1000

        # Direct cosine search
        search_start = time.perf_counter()
        results = await self._client.query_points(
            collection_name=MULTIMODAL_COLLECTION,
            query=query_vector,
            limit=k,
            with_payload=True,
        )
        search_time_ms = (time.perf_counter() - search_start) * 1000

        properties = [_format_point(p) for p in results.points]

        count_result = await self._client.count(
            collection_name=MULTIMODAL_COLLECTION,
            exact=True,
        )

        scores = [p.score for p in properties]
        total_time_ms = (time.perf_counter() - total_start) * 1000

        return MultimodalSearchResult(
            query="[image search]",
            search_mode="image",
            results=properties,
            total=count_result.count,
            metrics=MultimodalSearchMetrics(
                embed_time_ms=round(embed_time_ms, 2),
                search_time_ms=round(search_time_ms, 2),
                total_time_ms=round(total_time_ms, 2),
                total_candidates=count_result.count,
                score_min=round(min(scores), 4) if scores else 0.0,
                score_max=round(max(scores), 4) if scores else 0.0,
                score_avg=round(sum(scores) / len(scores), 4) if scores else 0.0,
            ),
        )
