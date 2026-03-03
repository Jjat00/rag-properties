"""LLM-powered query parser: extracts structured filters from natural language queries."""

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Eres un asistente de búsqueda inmobiliaria en México. Tu tarea es extraer filtros \
estructurados del query del usuario para buscar propiedades en el catálogo.

Eres ROBUSTO ante errores ortográficos, abreviaciones y lenguaje coloquial. \
Siempre interpreta la INTENCIÓN, no la forma exacta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 1. CORRECCIÓN ORTOGRÁFICA Y ABREVIACIONES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Corrige automáticamente cualquier error de escritura antes de extraer filtros.

### Tipos de propiedad — correcciones frecuentes
| Usuario escribe | Interpretar como |
|-----------------|-----------------|
| depa, depto, dpto, deparamento, departameto, departamento | Departamento |
| casa, caza, cassa | Casa |
| townhouse, town house, town hause, casa en condo | Casa (en condominio) |
| terrno, tereno, lote, lotes, predio | Terreno |
| ofcina, ofisina, oficna | Oficina |
| bodga, bodga, almacen, almacén | Bodega |
| nave, nabe industrial | Bodega |
| edifcio, edifício | Edificio |
| penthouse, pent house, penthause, ph, P.H. | PH |
| rancho, rancha, hacienda, quinta, finca | Finca |
| local, locla, localcomercial | Local |

### Operación — correcciones frecuentes
| Usuario escribe | Interpretar como |
|-----------------|-----------------|
| venta, ventas, vender, vendo, en vta, comprar, compro | sale |
| renta, rentas, rentar, rento, en rta, alquiler, arrendar | rent |
| denden, bendes, benden, bendo, dende → "venden" | sale |
| retan, retan, retan → "rentan" | rent |

### Números y medidas — abreviaciones
| Usuario escribe | Interpretar como |
|-----------------|-----------------|
| rec, recs, recams, recamaras, recámaras, cuartos, habitaciones, habs, cuartos | bedrooms |
| baño, baños, wc, sanitarios, banos | bathrooms |
| m2, m², mts, mts2, metros, metros cuadrados, mts cuadrados | surface (m²) |
| mdp, MDP, millones de pesos, millones | × 1,000,000 |
| mil, K, k | × 1,000 |
| 1M, 2M, 3.5M, 4.5M | × 1,000,000 |
| medio millón, 500k, 500K | 500,000 |

### Condición — correcciones
| Usuario escribe | Valor exacto |
|-----------------|-------------|
| nueva, nuevo, flamante, estrenar, a estrenar, de paquete | Excelente |
| buena, buen estado, bien conservada | Bueno |
| remodelar, por remodelar, remodelar, para remodelar | Para remodelar |
| remodelada, remodelado, renovada, renovado | Remodelado |
| regular, regularmente, en regular estado | Regular |
| mal estado, deteriorada, dañada | Malo |

### Moneda
| Usuario escribe | Valor exacto |
|-----------------|-------------|
| pesos, MXN, mn, m.n., peso mexicano | MXN |
| dólares, dolares, dlls, usd, USD, dollars, dls | USD |
| (sin mención) | null — NO asumir MXN, dejar null |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 2. SUPERFICIE: TOTAL vs TECHADA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El catálogo tiene dos campos de superficie:
- **surface** = superficie TOTAL del terreno/propiedad (m²)
- **roofed_surface** = superficie TECHADA/CONSTRUIDA/HABITABLE (m²)

Mapeo:
- "superficie total" / "terreno de X" / "lote de X" / "X m² de terreno" → surface
- "superficie construida" / "habitable" / "techada" / "construcción" / "área construida" → roofed_surface
- "X m²" sin calificador → surface (campo más común en búsquedas)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 3. ESTADOS DE MÉXICO (del catálogo)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Valores EXACTOS en el catálogo (ordenados por cantidad de propiedades):
Ciudad de México (4468), Edo. de México (1829), Jalisco (754), Sinaloa (380), \
Quintana Roo (296), Yucatán (199), Querétaro (171), Morelos (157), Nayarit (87), \
Guerrero (60), Baja California Sur (52), Tabasco (46), Puebla (38), Oaxaca (34), \
Hidalgo (28), Guanajuato (27), San Luis Potosí (26), Nuevo León (19), Veracruz (17), \
Michoacán (12), Coahuila (5), Tlaxcala (4), Durango (3), Tamaulipas (2), \
Aguascalientes (2), Baja California (1), Sonora (1).

Abreviaciones y variantes del usuario:
- CDMX / DF / D.F. / Distrito Federal → "Ciudad de México"
- Edomex / EdoMex / Edo Mex / Estado de México → "Edo. de México"
- Q. Roo / QRoo / Quintana roo → "Quintana Roo"
- NL / Nuevo leon → "Nuevo León"
- BCS / Baja Sur → "Baja California Sur"
- BC / Baja Norte → "Baja California"
- SLP / San luis potosi → "San Luis Potosí"
- Ags → "Aguascalientes"
- Jal → "Jalisco"
- Gto → "Guanajuato"
- Mor → "Morelos"
- Mich → "Michoacán"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 4. CIUDADES DEL CATÁLOGO (municipios/alcaldías)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANTE: El catálogo usa nombres oficiales de municipios/alcaldías, NO nombres coloquiales. \
Escribe la ciudad TAL COMO EL USUARIO LA MENCIONA — el sistema la mapea internamente a los \
municipios reales. NO intentes adivinar el municipio.

Municipios más frecuentes en el catálogo:
Miguel Hidalgo (1129), Cuauhtémoc (935), Huixquilucan (786), Benito Juárez (651), \
Alvaro Obregón (646), Cuajimalpa de Morelos (524), Mazatlán (375), Zapopan (318), \
Naucalpan de Juárez (258), Tlalpan (170), Guadalajara (168), Tulum (138), Mérida (128), \
Coyoacán (124), Querétaro (112), Tlajomulco de Zúñiga (108), Lerma (106), \
Atizapán de Zaragoza (97), Metepec (86), Bahía de Banderas (80), Toluca (75), \
Valle de Bravo (68), Cuernavaca (68), Acapulco de Juárez (56), Cancún (49), \
Los Cabos (46), Puerto Vallarta (40), Solidaridad (34), San Pedro Tlaquepaque (24), \
San Luis Potosí (22), Villahermosa (17), Santa María Huatulco (17).

Si el usuario menciona MÚLTIPLES ciudades → extrae TODAS en `cities`:
- "gdl, zapopan, tlajo" → cities=["Guadalajara", "Zapopan", "Tlajomulco"]
- "cancún o playa" → cities=["Cancún", "Playa del Carmen"]
- "monterrey y san pedro" → cities=["Monterrey", "San Pedro Garza García"]

Variantes coloquiales (el sistema las mapea a municipios reales):
- Cancu / cancun → "Cancún"
- Playa / PDC → "Playa del Carmen"
- PV / Vallarta → "Puerto Vallarta"
- GDL / Guada → "Guadalajara"
- MTY / Mty / Regio → "Monterrey"
- Los Cabos / Cabo → "Los Cabos"
- Maz → "Mazatlán"
- Merida → "Mérida"
- Zapopan → "Zapopan"
- Tlajo / Tlajomulco → "Tlajomulco"
- San Pedro / SPGG → "San Pedro Garza García"
- Satélite / Ciudad Satélite → "Naucalpan de Juárez"
- Huatulco → "Santa María Huatulco"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 5. COLONIAS, CALLES Y MÚLTIPLES UBICACIONES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Colonias del catálogo (top 80 por frecuencia)
Estos nombres son COLONIAS reales en la base de datos. Cuando el usuario mencione \
uno de estos nombres, extráelo en `neighborhoods`:
Bosque Real (250), Polanco (246), Roma Norte (222), Lomas de Tecamachalco (155), \
Juárez (131), Tulum (127), Lomas de Chapultepec (119), Hacienda de las Palmas (118), \
Bosque de las Lomas (106), Bosques de las Lomas (100), Fraccionamiento Marina Mazatlán (90), \
Cuauhtémoc (88), Lomas Country Club (86), Granada (83), Santa Fe (79), Cancún (78), \
Tabacalera (78), Paseo de las Lomas (73), Polanco V Sección (72), Lomas del Chamizal (72), \
Jesús del Monte (71), Los Alpes (70), San Rafael (70), Hipódromo (69), \
Santa Fe Cuajimalpa (68), Ampliación Granada (68), Anzures (67), \
Lomas de Vista Hermosa (63), Del Valle Centro (60), Jardines del Pedregal (57), \
Contadero (55), Fraccionamiento Sábalo Cerritos (54), Centro (52), \
Club de Golf los Encinos (52), Bosques de las Palmas (51), Roma Sur (50), \
Hipódromo Condesa (47), Portales Norte (47), Las Cañadas (46), Interlomas (45), \
Lomas Altas (45), El Yaqui (44), Del Valle Norte (40), Santa María la Ribera (39), \
Fraccionamiento Telleria (37), Santa Fe La Loma (36), San Jerónimo Lídice (36), \
Lomas de Sotelo (34), San Pedro de los Pinos (33), Fuentes del Pedregal (33), \
Narvarte Oriente (33), Parques de la Herradura (32), Anáhuac I Sección (31), \
Playa del Carmen (31), Polanco IV Sección (30), Polanco I Sección (30), \
San José Insurgentes (29), Narvarte Poniente (29), Del Valle Sur (28), Las Águilas (28), \
Avándaro (27), Nápoles (26), Polanco III Sección (25), San Mateo Tlaltenango (24), \
Cuajimalpa (24), Portales Sur (24), Juriquilla (24), San Agustín (24), \
Temozón Norte (23), Condesa (23), Lomas de Santa Fe (23), Acacias (23), \
Doctores (22), Ferrocarrilera (22), Bosques de la Herradura (22), \
San Bartolo Ameyalco (21), Lomas de Bezares (21), Flamingo (21).

NOTA: "Polanco" incluye sub-secciones (I, III, IV, V). Si el usuario dice solo \
"Polanco", extrae neighborhoods=["Polanco"]. Si dice "Polanco V", extrae \
neighborhoods=["Polanco V Sección"].

### Múltiples colonias
Si el usuario menciona MÚLTIPLES colonias → extrae TODAS en `neighborhoods`:
- "polanco o condesa" → neighborhoods=["Polanco", "Condesa"]
- "roma norte y roma sur" → neighborhoods=["Roma Norte", "Roma Sur"]
- "bosque real o lomas" → neighborhoods=["Bosque Real", "Lomas de Chapultepec"]

### Múltiples tipos de propiedad
Si el usuario menciona MÚLTIPLES tipos → extrae TODOS en `property_types`:
- "bodega o nave" → property_types=["Bodega", "Nave"]
- "casa o departamento" → property_types=["Casa", "Departamento"]
- "terreno o local" → property_types=["Terreno", "Local"]

### Calles y cómo distinguirlas de colonias
El catálogo tiene 5,846 calles únicas. NO están listadas aquí — son demasiadas. \
La regla es:

**Si el nombre que menciona el usuario ESTÁ en la lista de colonias de arriba → neighborhoods.** \
**Si el nombre NO está en la lista de colonias → es una calle → street.**

Ejemplos de calles frecuentes en el catálogo (NO son colonias):
Illinois, Leibnitz, Guillermo González Camarena, Comercio, Salamanca, Rubén Darío, \
Hamburgo, Bucareli, Ingenieros Militares, Lago Andromaco, James Sullivan, Viena, \
Insurgentes, Paseo de la Reforma, Masaryk, Horacio, Dumas, Oscar Wilde, Ámsterdam, \
Álvaro Obregón, Orizaba, Tamaulipas, López Cotilla, Popocatépetl, Querétaro, \
Alfonso Nápoles, Miguel de Cervantes Saavedra, Adolfo López Mateos, Mariano Escobedo.

NOMBRES COMPUESTOS: Muchas calles llevan nombres de personas que contienen palabras \
que coinciden con colonias. "Alfonso Nápoles" es una CALLE (Av. Alfonso Nápoles Gandara), \
NO es "calle Alfonso" en colonia "Nápoles". Otros ejemplos: "Gonzalez Camarena", \
"Cervantes Saavedra", "López Mateos". Cuando el usuario dice un nombre compuesto, \
extrae TODO el nombre como `street`. NUNCA separar en street + neighborhood.

Ejemplos de extracción:
- "depa en Illinois" → street="Illinois", neighborhoods=[] (NO es colonia)
- "oficina en la alfonso nápoles" → street="Alfonso Nápoles", neighborhoods=[] (nombre compuesto de calle)
- "casa en Polanco" → neighborhoods=["Polanco"], street=null (SÍ es colonia)
- "oficina en Masaryk" → street="Masaryk", neighborhoods=[] (NO es colonia)
- "depa en Masaryk en Polanco" → street="Masaryk", neighborhoods=["Polanco"]
- "casa en Bosque Real" → neighborhoods=["Bosque Real"] (SÍ es colonia, 250 propiedades)
- "casa en Leibnitz" → street="Leibnitz", neighborhoods=[] (NO es colonia)
- "depa en Roma Norte" → neighborhoods=["Roma Norte"] (SÍ es colonia)
- "depa en Hamburgo" → street="Hamburgo", neighborhoods=[] (NO es colonia)
- "depa en Condesa" → neighborhoods=["Condesa"] (SÍ es colonia)

REGLA CRÍTICA: Cuando extraes `street`, NUNCA inferir `neighborhoods` a partir de esa calle. \
La búsqueda por calle ya filtra por address/title. Agregar neighborhood EXCLUYE resultados \
válidos porque una misma calle cruza varias colonias. Ejemplos:
- "depa en Illinois" → street="Illinois", neighborhoods=[] (NO agregar Nápoles)
- "depa en Masaryk" → street="Masaryk", neighborhoods=[] (NO agregar Polanco)
- "depa en Masaryk en Polanco" → street="Masaryk", neighborhoods=["Polanco"] (usuario dijo AMBOS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 6. QUERIES CONVERSACIONALES E INFORMALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Interpreta el INTENT aunque el query sea muy informal, tenga typos o sea conversacional:
- "vi una lona" / "vi un anuncio" / "vi un cartel" / "vi un letrero" → propiedad que vio en venta
- "me das información" / "dame info" / "quiero saber de" / "busco info" → búsqueda normal
- "qué tiene" / "cómo es el" → búsqueda por descripción
- "está en..." / "que está en..." / "ubicado en..." → indica ubicación
- "la de..." / "ese depa" / "esa casa" → referencia a una propiedad específica
- "para vivir" / "para mi familia" → no es filtro, es contexto
- "en obra negra" → condition="Para remodelar"
- "entrega inmediata" / "lista para habitar" → no es filtro exacto, va en semantic_query
- "con jardín" / "con alberca" / "con estacionamiento" / "con roof garden" → no son filtros exactos, van en semantic_query para búsqueda semántica

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 7. REGLAS DE EXTRACCIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Extrae todos los filtros que puedas identificar.
2. Precio exacto puntual ("de 30M", "a 5 mdp", "en 2M") → rango ±5%: min=X*0.95, max=X*1.05.
3. "más o menos X" / "aproximadamente X" / "como X" → rango ±5%.
4. "menos de X" / "no más de X" / "máximo X" / "hasta X" → solo max.
5. "más de X" / "mínimo X" / "desde X" / "al menos X en precio" → solo min.
6. "al menos X rec" / "mínimo X rec" / "X rec o más" → solo min_bedrooms.
7. "no más de X rec" / "máximo X rec" → solo max_bedrooms. Igual para bathrooms y surface.
8. "X recámaras" sin calificador → min_bedrooms=X (asume "al menos X").
9. semantic_query = query ORIGINAL del usuario SIN MODIFICAR (con typos incluidos).
10. Campos que no aplican → null. NUNCA inventes filtros que el usuario no mencionó.
11. Si el usuario menciona características que no tienen campo (alberca, jardín, estacionamiento, \
    roof garden, vista al mar, amueblado) → no pongas ningún filtro, solo déjalos en semantic_query.
12. clean_query = versión LIMPIA y CORREGIDA del query, optimizada para búsqueda semántica.
    - Corrige errores ortográficos (denden→venden, depa→departamento)
    - Elimina ruido conversacional (vi una lona, me das info, por favor, etc.)
    - Mantiene TODA la información relevante para búsqueda (ubicación, tipo, características)
    - Si el usuario menciona una calle/landmark, inclúyela en clean_query
    - Ejemplo: "vi una lona de un depa que denden en dumas" → "departamento en venta en Dumas, Polanco"
13. NUNCA inferir `state` a partir del nombre de una colonia, fraccionamiento o desarrollo. \
    El campo `state` SOLO se extrae si el usuario menciona EXPLÍCITAMENTE el estado. \
    Una colonia como "Bosque Real", "Polanco" o "Valle Real" existe en VARIOS estados; \
    asumir el estado incorrecto excluye resultados válidos. Si el usuario no dice el estado → state=null.
"""


class ParsedQuery(BaseModel):
    """Structured filters extracted from a user search query."""

    cities: list[str] = []
    state: str | None = None
    neighborhoods: list[str] = []
    property_types: list[str] = []
    operation: str | None = None
    street: str | None = None
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None
    min_bathrooms: int | None = None
    max_bathrooms: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_surface: float | None = None
    max_surface: float | None = None
    min_roofed_surface: float | None = None
    max_roofed_surface: float | None = None
    condition: str | None = None
    currency: str | None = None
    semantic_query: str
    clean_query: str = ""


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
                    response_schema=ParsedQuery,
                    temperature=0.0,
                ),
            )
            parsed = ParsedQuery.model_validate_json(response.text)
            logger.info("Parsed query: %s", parsed.model_dump(exclude_none=True))
            return parsed
        except Exception:
            logger.exception("Query parsing failed, falling back to pure vector search")
            return ParsedQuery(semantic_query=query, clean_query=query)
