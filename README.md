# RAG Properties

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
Busca propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún") y retorna las más relevantes del catálogo.

## Stack

- **Backend**: Python 3.12 + FastAPI
- **Package manager**: uv
- **Vector DB**: Qdrant (Docker local)
- **Embeddings**: OpenAI text-embedding-3 (small/large) y Gemini gemini-embedding-001 (multi-modelo, intercambiables)
- **Query parsing**: Gemini Flash / GPT-4o-mini con structured output

## Cómo funciona

```
Query: "casa amplia con jardín en zona tranquila de Mérida, 3 recámaras"
    ↓
1. Normalización: "Merida" → "Mérida" (diccionario estático)
    ↓
2. LLM Parser: extrae city="Mérida", type="Casa", bedrooms=3
    ↓
3. Qdrant pre-filtra: ~200 casas de 3 recámaras en Mérida
    ↓
4. Vector search: embedding del query completo vs propiedades filtradas
   "amplia con jardín zona tranquila" matchea títulos similares
    ↓
5. Top-K: las propiedades más relevantes semánticamente
```

## Estructura

```
rag-properties/
├── backend/
│   ├── pyproject.toml          # Dependencias (uv)
│   ├── config.py               # Settings, enum de modelos, dimensiones
│   ├── main.py                 # FastAPI app + endpoints
│   ├── models/
│   │   └── property.py         # Modelo Pydantic de propiedad
│   ├── embeddings/
│   │   ├── base.py             # Clase abstracta EmbeddingProvider
│   │   ├── openai_provider.py  # OpenAI text-embedding-3-small/large
│   │   ├── gemini_provider.py  # Gemini gemini-embedding-001
│   │   └── registry.py         # Registry con cache de providers
│   ├── vectorstore/
│   │   └── qdrant_manager.py   # Gestión de colecciones e indexes
│   ├── ingestion/
│   │   ├── location_normalizer.py  # Diccionario de aliases MX
│   │   ├── excel_loader.py     # Leer Excel → lista de Property
│   │   └── indexer.py          # Generar embeddings e indexar en Qdrant
│   └── search/                 # (Fase 3)
├── data/                       # Excel de propiedades
├── frontend/                   # (Fase 4)
└── plan.md                     # Plan detallado y decisiones de arquitectura
```

## Requisitos previos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker

## Setup

### 1. Levantar Qdrant con Docker

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

### 2. Instalar dependencias del backend

```bash
cd backend
uv sync
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus API keys (OPENAI_API_KEY, GEMINI_API_KEY)
```

### 4. Levantar el backend

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check del servidor |
| GET | `/health/qdrant` | Estado de las 3 colecciones en Qdrant |
| GET | `/models` | Lista de modelos de embedding soportados |
| POST | `/ingest` | Indexar propiedades del Excel en Qdrant |
| GET | `/docs` | Swagger UI (documentación interactiva) |

### POST `/ingest`

Carga las propiedades del Excel, genera embeddings y las indexa en Qdrant.

**Parámetros query:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `model` | `openai-small` \| `openai-large` \| `gemini` | `openai-small` | Modelo de embedding a usar (ignorado si `all_models=true`) |
| `all_models` | `bool` | `false` | Si `true`, indexa en las 3 colecciones |

**Respuesta (un modelo):**
```json
{
  "model": "openai-small",
  "collection": "properties_openai_small",
  "points_indexed": 8803
}
```

**Respuesta (all_models=true):**
```json
{
  "results": [
    {"model": "openai-small", "collection": "properties_openai_small", "points_indexed": 8803},
    {"model": "openai-large", "collection": "properties_openai_large", "points_indexed": 8803},
    {"model": "gemini", "collection": "properties_gemini", "points_indexed": 8803}
  ]
}
```

## Modelos de embedding soportados

| Modelo | Dimensiones | Colección Qdrant | Costo |
|--------|------------|------------------|-------|
| `openai-small` | 1536 | `properties_openai_small` | $0.02/M tokens |
| `openai-large` | 3072 | `properties_openai_large` | $0.13/M tokens |
| `gemini` | 3072 | `properties_gemini` | $0.15/M tokens |

## Indexar propiedades

Con el backend corriendo:

```bash
# Indexar con un modelo específico
curl -X POST "http://localhost:8000/ingest?model=openai-small"

# Indexar con Gemini
curl -X POST "http://localhost:8000/ingest?model=gemini"

# Indexar en las 3 colecciones
curl -X POST "http://localhost:8000/ingest?all_models=true"

# Verificar
curl http://localhost:8000/health/qdrant
```

## Decisiones clave

- **Un solo vector por propiedad** — filtros de metadata separan por aspecto
- **Una colección por modelo** — para A/B testing, consolidar después
- **Embedding = Title primero** — mayor valor semántico, luego tipo/ubicación/atributos como fallback
- **Query completo al embedding** — no solo el residuo post-filtros
- **Direcciones NO en embedding** — ruido; solo en payload para mostrar
- **Normalización doble** — diccionario estático + LLM parser para ubicaciones MX
- **Sparse BM25 en Fase 5** — beneficio marginal con filtros + dense; Qdrant lo hace server-side

Ver [plan.md](plan.md) para el detalle completo de decisiones y justificaciones.

## Fases del proyecto

- [x] **Fase 1** — Backend base: proyecto uv, modelos, embeddings multi-modelo, Qdrant manager, FastAPI
- [x] **Fase 2** — Ingesta: Excel loader, location normalizer, indexer, endpoint POST /ingest (8,803 propiedades)
- [ ] **Fase 3** — Búsqueda: normalización + query parsing + búsqueda semántica con filtros
- [ ] **Fase 4** — Frontend: playground web para probar búsquedas
- [ ] **Fase 5** — Mejoras: sparse BM25 + RRF, reranking, paginación, quantization
