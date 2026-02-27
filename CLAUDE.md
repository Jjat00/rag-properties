# RAG Properties — Instrucciones del Proyecto

## Objetivo

Sistema RAG para búsqueda semántica de propiedades inmobiliarias.
El usuario puede buscar propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún")
y el sistema retorna las propiedades más relevantes del catálogo.

**Flujo principal:**
1. Ingesta: Leer Excel de propiedades → generar embeddings → almacenar en Qdrant
2. Búsqueda: Query en lenguaje natural → embedding → búsqueda vectorial en Qdrant → resultados

---

## Stack tecnológico

- **Lenguaje**: Python (backend)
- **Package manager**: `uv` — SIEMPRE usar uv, nunca pip directamente
- **Vector DB**: Qdrant (local con Docker inicialmente)
- **Embeddings**: OpenAI text-embedding-3-small (1536d, barato, buen soporte español)
- **Query parsing**: Gemini Flash o GPT-4o-mini con structured output para extraer filtros
- **LLM credits**: Gemini y OpenAI (NO Anthropic). Nunca usar APIs de Anthropic.
- **Self-hosted**: NADA self-hosted. Solo APIs y servicios managed.
- **Backend**: FastAPI (sin LangGraph, flujo lineal simple)
- **Frontend**: Playground web para visualizar resultados (a definir)
- **Fecha de inicio**: 16 de febrero de 2026

---

## Reglas de desarrollo

### Python y entorno virtual
- **SIEMPRE usar `uv`** como manejador de paquetes. Nunca usar `pip install` directamente.
- Activar el entorno virtual antes de ejecutar cualquier script Python:
  ```bash
  source .venv/bin/activate
  ```
- Para instalar dependencias: `uv add <paquete>`
- Para crear el entorno: `uv venv && source .venv/bin/activate`
- Para ejecutar scripts: `uv run python script.py` o con el venv activado

### Qdrant
- Usar Qdrant **local** via Docker durante desarrollo
- Puerto por defecto: `6333` (HTTP) y `6334` (gRPC)
- Arrancar con: `docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant`

### Código
- Usar **type hints** en todas las funciones Python
- Preferir **async/await** en FastAPI
- Usar **Pydantic** para validación de datos
- Variables de entorno en `.env` (nunca hardcodear credenciales)

---

## Estructura del proyecto (objetivo)

```
rag-properties/
├── CLAUDE.md
├── pyproject.toml          # Gestionado por uv
├── .env                    # Variables de entorno (no commitear)
├── .env.example
├── data/
│   └── properties.xlsx     # Excel fuente de datos
├── backend/
│   ├── main.py             # FastAPI app
│   ├── ingestion/
│   │   ├── excel_loader.py # Leer y parsear Excel
│   │   └── indexer.py      # Generar embeddings e indexar en Qdrant
│   ├── search/
│   │   └── searcher.py     # Búsqueda semántica
│   └── models/
│       └── property.py     # Modelos Pydantic de propiedad
└── frontend/
    └── (playground web)
```

---

## Esquema de datos — Propiedades

Columnas del Excel fuente:

| Campo Excel | Descripción |
|-------------|-------------|
| `ID` | Identificador único de la propiedad |
| `Agent: FirstName` | Nombre del agente |
| `Agent: LastName` | Apellido del agente |
| `Agent: Company: Name` | Empresa del agente |
| `AgentSeller: Phone` | Teléfono del agente |
| `Listing: Price: Currency` | Moneda del precio (ej: MXN) |
| `Listing: Price: Price` | Precio de la propiedad |
| `Type` | Tipo de propiedad (Casa, Terreno comercial, Casa en condominio, etc.) |
| `Listing: Operation` | Tipo de operación (sale, rent, etc.) |
| `Listing: Title` | Título del anuncio |
| `InternalId` | ID interno (ej: CQC-063) |
| `Address: Neighborhood: Name` | Colonia/Fraccionamiento |
| `Address: PublicStreet` | Dirección completa |
| `Address: State: Name` | Estado |
| `Address: City: Name` | Ciudad |
| `Attributes: Suites` | Número de recámaras/suites |
| `Attributes: Bathrooms` | Número de baños |
| `Attributes: RoofedSurface` | Superficie techada (m²) |
| `Attributes: Surface` | Superficie total (m²) |
| `Attributes: Condition` | Condición (Bueno, Excelente, etc.) |
| `Address: Name` | Nombre de referencia de la dirección |

**Volumen inicial**: ~8,000 propiedades, escalable a más.

### Texto para embedding
El texto que se va a embeddear por propiedad debe combinar los campos más relevantes para búsqueda semántica:
```
{Type} en {operation} en {City}, {State}. {Title}.
{Suites} recámaras, {Bathrooms} baños.
Superficie: {Surface}m² ({RoofedSurface}m² techados).
Condición: {Condition}. Colonia: {Neighborhood}. Precio: {Currency} {Price}.
```

### Payload en Qdrant
Almacenar todos los campos originales como payload para poder filtrar y mostrar resultados completos.

---

## Estrategia RAG — Decisiones de arquitectura

### Por qué NO LangGraph
El flujo es lineal (query → parse → search → respond). No hay branching, loops ni human-in-the-loop.
LangGraph añade complejidad sin beneficio para este caso. Un endpoint FastAPI simple es suficiente.

### Modelos de embedding (multi-modelo, intercambiables)
El sistema soporta múltiples modelos de embedding para poder comparar resultados.
Cada modelo genera una colección separada en Qdrant.

| Modelo | Dimensiones | Costo | Provider |
|--------|------------|-------|----------|
| `text-embedding-3-small` | 1536d | $0.02/M tokens | OpenAI |
| `text-embedding-3-large` | 3072d | $0.13/M tokens | OpenAI |
| `text-embedding-004` | 768d | gratis (con límite) | Gemini |

- Todos via API, **nada self-hosted**
- Cosine similarity para todos
- El modelo activo se configura via `.env` o parámetro en el endpoint
- Esto permite A/B testing de calidad de resultados

### Estrategia de búsqueda: Filtros primero, semántica después
En búsqueda inmobiliaria, el 80-90% de la relevancia viene de atributos estructurados.
1. **Gemini Flash / GPT-4o-mini** parsea el query con structured output → extrae filtros + texto semántico
2. **Qdrant pre-filtra** por metadata (ciudad, recámaras, precio, tipo)
3. **Búsqueda vectorial dense** sobre los resultados filtrados
4. Retorna top-k propiedades

### Qdrant: Configuración de colecciones
- **Una colección por modelo de embedding** (ej: `properties_openai_small`, `properties_openai_large`, `properties_gemini`)
- Cada colección tiene su vector dense con las dimensiones correspondientes
- **Payload indexes** (crear ANTES de subir datos):
  - `city` (keyword) — para filtrar por ciudad
  - `state` (keyword) — para filtrar por estado
  - `property_type` (keyword) — casa, departamento, terreno, etc.
  - `operation` (keyword) — sale, rent
  - `bedrooms` (integer) — número de recámaras
  - `bathrooms` (integer) — número de baños
  - `price` (float) — para rangos de precio
  - `surface` (float) — superficie total m²
  - `condition` (keyword) — Bueno, Excelente, etc.

### Query parsing con Gemini Flash / GPT-4o-mini
Usar structured output / function calling para extraer filtros del query.
System prompt para el parser:
```
Eres un asistente de búsqueda inmobiliaria en México. Extrae filtros estructurados
del query del usuario. Normaliza nombres de ciudades (ej: "cancun" → "Cancún").
Convierte expresiones de precio ("4 millones" → 4000000, "4 mdp" → 4000000).
Mapea términos coloquiales: "recamaras"/"cuartos" → bedrooms,
"depa" → departamento, "baños completos" → bathrooms.
Pon aspectos descriptivos/subjetivos en semantic_query para búsqueda vectorial.
```

### Reranking: NO por ahora
Con 8K propiedades y filtros estructurados, la búsqueda híbrida es suficiente.
Si se necesita en el futuro: Cohere Rerank 3.5 o BGE-reranker-v2-m3.

---

## Fases del proyecto

1. **Fase 1 — Backend base**: Inicializar proyecto con uv, FastAPI, modelos Pydantic
2. **Fase 2 — Ingesta**: Leer Excel, generar embeddings con BGE-M3, indexar en Qdrant
3. **Fase 3 — Búsqueda**: Query parsing con Claude Haiku + búsqueda híbrida en Qdrant
4. **Fase 4 — Frontend**: Playground web para probar búsquedas
5. **Fase 5 — Mejoras**: Reranking, paginación, filtros avanzados (si se necesitan)

---

## Comandos útiles

```bash
# Levantar Qdrant local
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Crear entorno virtual
uv venv

# Activar entorno
source .venv/bin/activate

# Instalar dependencias
uv add fastapi qdrant-client openai openpyxl pandas python-dotenv

# Correr backend
uv run uvicorn backend.main:app --reload
```
