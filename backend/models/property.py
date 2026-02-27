import re

from pydantic import BaseModel, computed_field, field_validator


EXCEL_COLUMN_MAP: dict[str, str] = {
    "ID": "id",
    "Agent: FirstName": "agent_first_name",
    "Agent: LastName": "agent_last_name",
    "Agent: Company: Name": "agent_company",
    "AgentSeller: Phone": "agent_phone",
    "Listing: Price: Currency": "currency",
    "Listing: Price: Price": "price",
    "Type": "property_type",
    "Listing: Operation": "operation",
    "Listing: Title": "title",
    "InternalId": "internal_id",
    "Address: Neighborhood: Name": "neighborhood",
    "Address: PublicStreet": "address",
    "Address: State: Name": "state",
    "Address: City: Name": "city",
    "Attributes: Suites": "bedrooms",
    "Attributes: Bathrooms": "bathrooms",
    "Attributes: RoofedSurface": "roofed_surface",
    "Attributes: Surface": "surface",
    "Attributes: Condition": "condition",
    "Address: Name": "address_name",
}


def _normalize_number(value: object) -> float | None:
    """Normalize Mexican-style numbers: 30.000.000 → 30000000, 139,5 → 139.5."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Pattern: digits separated by dots with optional comma decimal (MX format)
    # e.g. "30.000.000" or "1.500.000,50"
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        return float(s)

    # Pattern: comma as decimal separator (e.g. "139,5")
    if re.match(r"^\d+,\d+$", s):
        s = s.replace(",", ".")
        return float(s)

    try:
        return float(s)
    except (ValueError, TypeError):
        return None


class Property(BaseModel):
    id: str | None = None
    agent_first_name: str | None = None
    agent_last_name: str | None = None
    agent_company: str | None = None
    agent_phone: str | None = None
    currency: str | None = None
    price: float | None = None
    property_type: str | None = None
    operation: str | None = None
    title: str | None = None
    internal_id: str | None = None
    neighborhood: str | None = None
    address: str | None = None
    state: str | None = None
    city: str | None = None
    bedrooms: float | None = None
    bathrooms: float | None = None
    roofed_surface: float | None = None
    surface: float | None = None
    condition: str | None = None
    address_name: str | None = None

    @field_validator("agent_phone", "id", "internal_id", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v).strip() or None

    @field_validator("price", "surface", "roofed_surface", mode="before")
    @classmethod
    def normalize_numeric(cls, v: object) -> float | None:
        return _normalize_number(v)

    @field_validator("bedrooms", "bathrooms", mode="before")
    @classmethod
    def normalize_int_like(cls, v: object) -> float | None:
        result = _normalize_number(v)
        if result is not None:
            return float(int(result))
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def embedding_text(self) -> str:
        """Build text for embedding. Title first (highest semantic value),
        then structured context. Price excluded (better as exact filter).
        Address excluded (noise). Neighborhood included (descriptive search).
        """
        parts: list[str] = []

        if self.title:
            parts.append(self.title + ".")

        type_op = f"{self.property_type or 'Propiedad'} en {self.operation or 'venta'}"
        location = ", ".join(filter(None, [self.neighborhood, self.city, self.state]))
        if location:
            type_op += f" en {location}"
        parts.append(type_op + ".")

        attrs: list[str] = []
        if self.bedrooms is not None:
            attrs.append(f"{int(self.bedrooms)} recámaras")
        if self.bathrooms is not None:
            attrs.append(f"{int(self.bathrooms)} baños")
        if self.surface is not None:
            attrs.append(f"{self.surface}m²")
        if attrs:
            parts.append(", ".join(attrs) + ".")

        if self.condition:
            parts.append(f"Condición: {self.condition}.")

        return " ".join(parts)

    def to_qdrant_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "agent_first_name": self.agent_first_name,
            "agent_last_name": self.agent_last_name,
            "agent_company": self.agent_company,
            "agent_phone": self.agent_phone,
            "currency": self.currency,
            "price": self.price,
            "property_type": self.property_type,
            "operation": self.operation,
            "title": self.title,
            "internal_id": self.internal_id,
            "neighborhood": self.neighborhood,
            "address": self.address,
            "state": self.state,
            "city": self.city,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "roofed_surface": self.roofed_surface,
            "surface": self.surface,
            "condition": self.condition,
            "address_name": self.address_name,
        }
