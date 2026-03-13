"""Multimodal semantic search with direct cosine similarity.

Uses fused embeddings (text + images in the same 3072d vector space).
Each property has exactly ONE point, so no deduplication is needed.
Search is a simple nearest-neighbor lookup — no prefetch or RRF fusion.
"""

import logging
import time

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    Range,
)

from config import MULTIMODAL_COLLECTION
from embeddings.gemini_multimodal_provider import GeminiMultimodalProvider

logger = logging.getLogger(__name__)


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
    embed_time_ms: float = 0.0
    search_time_ms: float = 0.0
    total_time_ms: float = 0.0
    total_candidates: int = 0


class MultimodalSearchResult(BaseModel):
    query: str
    search_mode: str = "text"  # "text" | "image"
    results: list[MultimodalPropertyResult]
    total: int
    metrics: MultimodalSearchMetrics = MultimodalSearchMetrics()


def _build_filter(
    city: str | None = None,
    state: str | None = None,
    house_type: str | None = None,
    operation: str | None = None,
    min_bedrooms: int | None = None,
    max_bedrooms: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> Filter | None:
    """Build Qdrant filters for multimodal search."""
    must: list[FieldCondition] = []

    if city:
        must.append(FieldCondition(key="city", match=MatchValue(value=city)))
    if state:
        must.append(FieldCondition(key="state", match=MatchValue(value=state)))
    if house_type:
        must.append(FieldCondition(key="house_type", match=MatchValue(value=house_type)))
    if operation:
        must.append(FieldCondition(key="operation", match=MatchValue(value=operation)))
    if min_bedrooms is not None or max_bedrooms is not None:
        must.append(
            FieldCondition(
                key="bedroom",
                range=Range(
                    gte=float(min_bedrooms) if min_bedrooms is not None else None,
                    lte=float(max_bedrooms) if max_bedrooms is not None else None,
                ),
            )
        )
    if min_price is not None or max_price is not None:
        must.append(
            FieldCondition(
                key="price",
                range=Range(gte=min_price, lte=max_price),
            )
        )

    return Filter(must=must) if must else None


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
    """Multimodal search using direct cosine similarity.

    Since all embeddings (text and images) live in the same vector space,
    a single cosine search finds the most relevant properties regardless
    of whether the match is textual or visual.
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
        top_k: int | None = None,
        city: str | None = None,
        state: str | None = None,
        house_type: str | None = None,
        operation: str | None = None,
        min_bedrooms: int | None = None,
        max_bedrooms: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> MultimodalSearchResult:
        """Search using direct cosine similarity against fused embeddings."""
        total_start = time.perf_counter()
        k = top_k or self._top_k

        qdrant_filter = _build_filter(
            city=city,
            state=state,
            house_type=house_type,
            operation=operation,
            min_bedrooms=min_bedrooms,
            max_bedrooms=max_bedrooms,
            min_price=min_price,
            max_price=max_price,
        )

        # Embed query text
        embed_start = time.perf_counter()
        query_vector = await self._provider.embed_query(query)
        embed_time_ms = (time.perf_counter() - embed_start) * 1000

        # Direct cosine search — one point per property, no dedup needed
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

        # Count total matching properties
        count_result = await self._client.count(
            collection_name=MULTIMODAL_COLLECTION,
            count_filter=qdrant_filter,
            exact=True,
        )

        total_time_ms = (time.perf_counter() - total_start) * 1000

        return MultimodalSearchResult(
            query=query,
            search_mode="text",
            results=properties,
            total=count_result.count,
            metrics=MultimodalSearchMetrics(
                embed_time_ms=round(embed_time_ms, 2),
                search_time_ms=round(search_time_ms, 2),
                total_time_ms=round(total_time_ms, 2),
                total_candidates=count_result.count,
            ),
        )

    async def search_by_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        top_k: int | None = None,
    ) -> MultimodalSearchResult:
        """Search properties by uploading an image (cross-modal search).

        The image is embedded with RETRIEVAL_QUERY task type and searched
        against fused embeddings using direct cosine similarity.
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
            ),
        )
