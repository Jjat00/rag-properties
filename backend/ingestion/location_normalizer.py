"""Normalize Mexican location names for consistent filtering in Qdrant.

Two-layer strategy:
  1. STATE_CANONICAL — fixes inconsistencies IN the Excel data (ingestion time)
  2. STATE_ALIASES — maps user query variants to canonical names (query time, Fase 3)
"""

# Corrections for values found in the Excel.
# The canonical form is whichever variant has the most rows.
STATE_CANONICAL: dict[str, str] = {
    "Estado de México": "Edo. de México",
    "Baja California Norte": "Baja California",
    "San luis Potosí": "San Luis Potosí",
}

# Query-time aliases — maps lowercased user input to the canonical state name
# used in Qdrant payloads. Applied in Fase 3 (search/location_normalizer.py).
STATE_ALIASES: dict[str, str] = {
    # Edo. de México
    "edomex": "Edo. de México",
    "edo mex": "Edo. de México",
    "edo. mex": "Edo. de México",
    "edo de mexico": "Edo. de México",
    "edo. de mexico": "Edo. de México",
    "estado de mexico": "Edo. de México",
    "estado de méxico": "Edo. de México",
    # CDMX
    "cdmx": "Ciudad de México",
    "df": "Ciudad de México",
    "d.f.": "Ciudad de México",
    "distrito federal": "Ciudad de México",
    "ciudad de mexico": "Ciudad de México",
    # Quintana Roo
    "q. roo": "Quintana Roo",
    "qroo": "Quintana Roo",
    "q roo": "Quintana Roo",
    "quintanaroo": "Quintana Roo",
    # Nuevo León
    "nl": "Nuevo León",
    "nuevo leon": "Nuevo León",
    "nvo leon": "Nuevo León",
    # Baja California Sur
    "bcs": "Baja California Sur",
    "baja california sur": "Baja California Sur",
    # Baja California
    "bc": "Baja California",
    "baja california": "Baja California",
    "baja california norte": "Baja California",
    # San Luis Potosí
    "slp": "San Luis Potosí",
    "san luis potosi": "San Luis Potosí",
    # Aguascalientes
    "ags": "Aguascalientes",
    # Jalisco
    "jal": "Jalisco",
}


def canonicalize_state(raw: str | None) -> str | None:
    """Normalize a state name from Excel data to its canonical form."""
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    return STATE_CANONICAL.get(stripped, stripped)


def canonicalize_city(raw: str | None) -> str | None:
    """Normalize a city name: strip whitespace and fix capitalization."""
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    return stripped


# City aliases: maps a user-facing city name (lowercased) to ALL matching
# city values in the Qdrant payload.  Used with MatchAny at query time.
# The data often uses municipio names (Benito Juárez, Solidaridad, Miguel Hidalgo)
# instead of the colloquial city name users type.
CITY_ALIASES: dict[str, list[str]] = {
    # Quintana Roo
    "cancún": ["Cancún", "Benito Juárez"],
    "cancun": ["Cancún", "Benito Juárez"],
    "playa del carmen": ["Solidaridad", "Playa del Carmen"],
    "playa": ["Solidaridad", "Playa del Carmen"],
    "pdc": ["Solidaridad", "Playa del Carmen"],
    # CDMX delegaciones — user says "CDMX" but data has delegaciones
    "ciudad de méxico": [
        "Miguel Hidalgo", "Cuauhtémoc", "Benito Juárez", "Alvaro Obregón",
        "Cuajimalpa de Morelos", "Tlalpan", "Coyoacán", "Gustavo A. Madero",
        "Azcapotzalco", "La Magdalena Contreras", "Iztapalapa", "Xochimilco",
        "Venustiano Carranza", "Iztacalco", "Tláhuac", "Milpa Alta",
    ],
    "cdmx": [
        "Miguel Hidalgo", "Cuauhtémoc", "Benito Juárez", "Alvaro Obregón",
        "Cuajimalpa de Morelos", "Tlalpan", "Coyoacán", "Gustavo A. Madero",
        "Azcapotzalco", "La Magdalena Contreras",
    ],
    # Jalisco
    "guadalajara": ["Guadalajara", "Zapopan", "Tlajomulco de Zúñiga"],
    "gdl": ["Guadalajara", "Zapopan", "Tlajomulco de Zúñiga"],
    "puerto vallarta": ["Puerto Vallarta"],
    "vallarta": ["Puerto Vallarta"],
    "pv": ["Puerto Vallarta"],
    # Nuevo León
    "monterrey": ["Monterrey", "San Pedro Garza García", "San Nicolás de los Garza"],
    "mty": ["Monterrey", "San Pedro Garza García", "San Nicolás de los Garza"],
    # Yucatán
    "mérida": ["Mérida"],
    "merida": ["Mérida"],
    # Nayarit
    "sayulita": ["Bahía de Banderas", "Sayulita"],
    # Edo. de México
    "toluca": ["Toluca", "Metepec", "Lerma"],
    # Morelos
    "cuernavaca": ["Cuernavaca"],
    # Guerrero
    "acapulco": ["Acapulco de Juárez"],
    # Sinaloa
    "mazatlán": ["Mazatlán"],
    "mazatlan": ["Mazatlán"],
    # BCS
    "los cabos": ["Cabo San Lucas", "San José del Cabo", "Los Cabos"],
    "cabo san lucas": ["Cabo San Lucas", "Los Cabos"],
    "san josé del cabo": ["San José del Cabo", "Los Cabos"],
    # Querétaro
    "querétaro": ["Querétaro"],
    "queretaro": ["Querétaro"],
    # Guanajuato
    "san miguel de allende": ["San Miguel de Allende"],
    "león": ["León"],
    "leon": ["León"],
    # Oaxaca
    "oaxaca": ["Oaxaca de Juárez"],
    # Tabasco
    "villahermosa": ["Villahermosa", "Centro"],
}


def resolve_state_alias(user_input: str) -> str | None:
    """Resolve a user query state name to its canonical form (query time).

    Returns None if no alias matched — caller should use the input as-is.
    """
    key = user_input.strip().lower()
    return STATE_ALIASES.get(key)


def resolve_city_alias(user_input: str) -> list[str] | None:
    """Resolve a user query city name to all matching Qdrant city values.

    Returns None if no alias matched — caller should use the input as-is.
    """
    key = user_input.strip().lower()
    return CITY_ALIASES.get(key)
