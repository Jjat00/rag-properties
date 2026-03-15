"""Pydantic model for multimodal properties (JSON/MongoDB export)."""

from pydantic import BaseModel, computed_field, field_validator


def _clean_image_url(url: str) -> str:
    """Extract the real Firebase Storage URL from the proxy-duplicated URL.

    URLs come as:
    https://agile-ridge-02432.herokuapp.com/https://agile-ridge-02432.herokuapp.com/https://firebasestorage...
    We want just the https://firebasestorage... part.
    """
    marker = "https://firebasestorage.googleapis.com/"
    idx = url.rfind(marker)
    if idx != -1:
        return url[idx:]
    return url


class MultimodalProperty(BaseModel):
    id: str
    firebase_id: str | None = None
    ad_status: str | None = None
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

    @field_validator("pictures", mode="before")
    @classmethod
    def clean_pictures(cls, v: list[str] | None) -> list[str]:
        if not v:
            return []
        return [_clean_image_url(url) for url in v if url]

    @classmethod
    def from_json(cls, raw: dict) -> "MultimodalProperty":
        """Parse a single document from the MongoDB JSON export."""
        oid = raw.get("_id", {})
        doc_id = oid.get("$oid", "") if isinstance(oid, dict) else str(oid)

        prices = raw.get("prices_types", [])
        price_val = prices[0] if prices else None

        return cls(
            id=doc_id,
            firebase_id=raw.get("firebase_id"),
            ad_status=raw.get("ad_status"),
            title=raw.get("title"),
            description=raw.get("description"),
            house_type=raw.get("house_type"),
            city=raw.get("city"),
            state=raw.get("state"),
            suburb=raw.get("suburb"),
            address=raw.get("address"),
            street=raw.get("street"),
            bedroom=raw.get("bedroom"),
            bathroom=raw.get("bathroom"),
            half_bathroom=raw.get("half_bathroom"),
            construction_area=raw.get("construction_area"),
            land_area=raw.get("land_area"),
            price=price_val,
            currency=raw.get("currency_display"),
            operation=raw.get("monetization_type_display"),
            condition=raw.get("physical_state"),
            antiquity=raw.get("antiquity"),
            pictures=raw.get("pictures", []),
            amenities=raw.get("amenities", []),
            exterior_selected=raw.get("exterior_selected", []),
            general_selected=raw.get("general_selected", []),
            near_places=raw.get("near_places", []),
            parking_lot=raw.get("parking_lot"),
            lat=raw.get("lat"),
            lng=raw.get("lng"),
            ad_copy=raw.get("ad_copy"),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def embedding_text(self) -> str:
        """Build text for embedding. Combines title, description, type, location, amenities."""
        parts: list[str] = []

        if self.title:
            parts.append(self.title + ".")

        if self.description:
            # Take first 500 chars of description to keep embedding focused
            desc = self.description[:500].strip()
            if desc:
                parts.append(desc)

        type_op = f"{self.house_type or 'Propiedad'} en {self.operation or 'venta'}"
        location = ", ".join(filter(None, [self.suburb, self.city, self.state]))
        if location:
            type_op += f" en {location}"
        parts.append(type_op + ".")

        attrs: list[str] = []
        if self.bedroom is not None:
            attrs.append(f"{self.bedroom} recámaras")
        if self.bathroom is not None:
            attrs.append(f"{self.bathroom} baños")
        if self.half_bathroom:
            attrs.append(f"{self.half_bathroom} medio baño")
        if self.construction_area is not None:
            attrs.append(f"{self.construction_area}m² construcción")
        if self.land_area is not None:
            attrs.append(f"{self.land_area}m² terreno")
        if attrs:
            parts.append(", ".join(attrs) + ".")

        if self.condition:
            parts.append(f"Condición: {self.condition}.")
        if self.antiquity:
            parts.append(f"Antigüedad: {self.antiquity}.")

        # Amenities and features
        all_features = self.amenities + self.exterior_selected + self.general_selected
        if all_features:
            parts.append("Amenidades: " + ", ".join(all_features[:15]) + ".")

        if self.near_places:
            parts.append("Cerca de: " + ", ".join(self.near_places[:10]) + ".")

        return " ".join(parts)

    def to_qdrant_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "firebase_id": self.firebase_id,
            "title": self.title,
            "description": self.description,
            "house_type": self.house_type,
            "city": self.city,
            "state": self.state,
            "suburb": self.suburb,
            "address": self.address,
            "street": self.street,
            "bedroom": self.bedroom,
            "bathroom": self.bathroom,
            "half_bathroom": self.half_bathroom,
            "construction_area": self.construction_area,
            "land_area": self.land_area,
            "price": self.price,
            "currency": self.currency,
            "operation": self.operation,
            "condition": self.condition,
            "antiquity": self.antiquity,
            "pictures": self.pictures,
            "amenities": self.amenities,
            "exterior_selected": self.exterior_selected,
            "general_selected": self.general_selected,
            "near_places": self.near_places,
            "parking_lot": self.parking_lot,
            "lat": self.lat,
            "lng": self.lng,
            "ad_copy": self.ad_copy,
        }
