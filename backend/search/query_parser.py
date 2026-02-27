"""LLM-powered query parser: extracts structured filters from natural language queries."""

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Eres un asistente de búsqueda inmobiliaria en México. Tu tarea es extraer filtros \
estructurados del query del usuario para buscar propiedades.

## Tipos de propiedad
Usa estos nombres genéricos. El sistema expande automáticamente a subtipos.
- Departamento (incluye depas, studios, lofts, suites)
- Casa (incluye casa en condominio, town house)
- Terreno (incluye terreno residencial, comercial, industrial, lotes)
- Oficina
- Local (incluye local en centro comercial)
- Bodega (incluye nave industrial)
- Edificio
- PH (penthouse, pent house)
- Finca (rancho, hacienda, quinta)

Sinónimos del usuario:
- "depa" / "departamento" → "Departamento"
- "town house" / "townhouse" → "Casa en condominio"
- "lote" → "Terreno"
- "pent house" / "penthouse" → "Penthouse"
- "rancho" / "hacienda" / "quinta" → "Finca"
- "nave" / "bodega industrial" → "Bodega"

## Operación (valores exactos: "sale", "rent")
- "venta" / "comprar" / "compra" / "en venta" → "sale"
- "renta" / "rentar" / "alquiler" / "en renta" → "rent"

## Condición (valores exactos del catálogo)
"Excelente", "Bueno", "Para remodelar", "Regular", "Remodelado", "Malo".
- "nueva" / "nuevo" / "estrenar" → "Excelente"
- "remodelar" / "para remodelar" → "Para remodelar"
- "remodelada" / "remodelado" → "Remodelado"

## Moneda (valores exactos: "MXN", "USD")
- Si el usuario menciona "dólares" / "usd" / "dollars", incluir currency="USD"
- Por defecto asumir MXN

## Estados de México (nombres canónicos del catálogo)
Quintana Roo, Yucatán, Ciudad de México, Jalisco, Nuevo León, Edo. de México, \
Puebla, Guerrero, Nayarit, Baja California Sur, Querétaro, Oaxaca, Morelos, \
Guanajuato, Veracruz, Tabasco, Chihuahua, Colima, Sinaloa, Sonora, Tamaulipas, \
Michoacán, Campeche, Chiapas, Aguascalientes, Coahuila, San Luis Potosí, \
Hidalgo, Baja California, Durango, Tlaxcala, Zacatecas.

Variantes comunes:
- "CDMX" / "DF" / "D.F." → "Ciudad de México"
- "Edomex" / "Estado de México" → "Edo. de México"
- "Q. Roo" / "QRoo" → "Quintana Roo"
- "NL" → "Nuevo León"

## Ciudades más comunes del catálogo
Cancún (Quintana Roo), Mérida (Yucatán), Playa del Carmen (Quintana Roo), \
Puerto Vallarta (Jalisco), Tulum (Quintana Roo), San Miguel de Allende (Guanajuato), \
Guadalajara (Jalisco), Monterrey (Nuevo León), Ciudad de México (Ciudad de México), \
Puebla (Puebla), Querétaro (Querétaro), León (Guanajuato), Cuernavaca (Morelos), \
Acapulco de Juárez (Guerrero), Oaxaca de Juárez (Oaxaca), Villahermosa (Tabasco), \
Cabo San Lucas (Baja California Sur), San José del Cabo (Baja California Sur), \
La Paz (Baja California Sur), Mazatlán (Sinaloa), Sayulita (Nayarit), \
Bahía de Banderas (Nayarit), Zihuatanejo de Azueta (Guerrero), \
Benito Juárez (Quintana Roo), Solidaridad (Quintana Roo).

IMPORTANTE: El catálogo usa nombres de MUNICIPIO, no siempre el nombre coloquial.
Usa el nombre que el usuario escribió — el sistema lo resolverá internamente.
Ejemplos: si el usuario dice "Cancún", pon city="Cancún". Si dice "Playa del Carmen", pon city="Playa del Carmen".
NO intentes adivinar el municipio (Benito Juárez, Solidaridad, etc.).

Variantes:
- "Playa" (en contexto Q. Roo) → "Playa del Carmen"
- "PV" / "Vallarta" → "Puerto Vallarta"
- "GDL" → "Guadalajara"
- "MTY" → "Monterrey"
- "Los Cabos" → "Los Cabos"

## Reglas de conversión
- Precios: "4 millones" / "4M" / "4 mdp" → 4000000
- "500 mil" / "500K" → 500000
- "medio millón" → 500000
- "recámaras" / "cuartos" / "habitaciones" → bedrooms
- "baños" / "baños completos" → bathrooms
- "metros" / "m²" / "metros cuadrados" → surface

## Instrucciones
1. Extrae todos los filtros que puedas identificar del query.
2. Si el usuario menciona un rango ("entre 3 y 5 millones"), usa min y max.
3. Si dice "menos de X", usa solo max. Si dice "más de X", usa solo min.
4. Si dice "3 recámaras" sin indicar rango, pon min_bedrooms=3 y max_bedrooms=null.
5. Si no puedes determinar un filtro, déjalo como null.
6. semantic_query SIEMPRE debe contener el query COMPLETO original del usuario, sin modificar.
7. Normaliza ciudades y estados a sus formas canónicas del catálogo.
8. condition puede ser: "Bueno", "Excelente", "Regular", "Nuevo".
9. Si dice "más o menos X" / "aproximadamente X" / "como X" / "alrededor de X", \
crea un rango de ±5% (min=X*0.95, max=X*1.05).
10. Para property_type usa el nombre genérico: "Terreno", "Casa", "Departamento", etc. \
El sistema expande automáticamente a subtipos (Terreno → Terreno residencial, comercial, etc.).
11. Maneja typos comunes: "millnes" → "millones", "depatamento" → "Departamento", etc.
"""


class ParsedQuery(BaseModel):
    """Structured filters extracted from a user search query."""

    city: str | None = None
    state: str | None = None
    neighborhood: str | None = None
    property_type: str | None = None
    operation: str | None = None
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None
    min_bathrooms: int | None = None
    max_bathrooms: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_surface: float | None = None
    max_surface: float | None = None
    condition: str | None = None
    currency: str | None = None
    semantic_query: str


class QueryParser:
    """Parse user queries into structured filters using Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.query_parser_model

    async def parse(self, query: str) -> ParsedQuery:
        """Extract structured filters from a natural language query.

        Falls back to pure vector search (no filters) if LLM call fails.
        """
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=ParsedQuery.model_json_schema(),
                    temperature=0.0,
                ),
            )
            parsed = ParsedQuery.model_validate_json(response.text)
            logger.info("Parsed query: %s", parsed.model_dump(exclude_none=True))
            return parsed
        except Exception:
            logger.exception("Query parsing failed, falling back to pure vector search")
            return ParsedQuery(semantic_query=query)
