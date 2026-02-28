# RAG Properties

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
Busca propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún") y retorna las más relevantes del catálogo.

## Stack

- **Backend**: Python 3.12 + FastAPI
- **Package manager**: uv
- **Vector DB**: Qdrant (local Docker en desarrollo, Qdrant Cloud en producción)
- **Embeddings**: OpenAI text-embedding-3 (small/large) y Gemini gemini-embedding-001 (multi-modelo, intercambiables)
- **Query parsing**: Gemini 3 Flash (preview) con structured output
- **Frontend**: React 19 + Vite + Shadcn/ui + Tailwind v4

## Cómo funciona

```
Query: "bodega o nave en gdl, zapopan, tlajo en calle alfonso nápoles"
    ↓
1. Normalización: "gdl"→["Guadalajara","Zapopan","Tlajomulco de Zúñiga"], "tlajo"→["Tlajomulco de Zúñiga"]
    ↓
2. LLM Parser (Gemini 3 Flash): extrae
   cities=["Guadalajara","Zapopan","Tlajomulco"], property_types=["Bodega","Nave"],
   street="Alfonso Nápoles"
    ↓
3. Filtros must + should en Qdrant:
   must: city IN [...], property_type IN ["Bodega comercial","Nave industrial"]
   should: address MATCH "Alfonso Nápoles", title MATCH "Alfonso Nápoles"
    ↓
4. Vector search: embedding del query completo vs propiedades filtradas
    ↓
5. Top-K: propiedades más relevantes (should-matching primero)
```

## Estructura

```
rag-properties/
├── backend/
│   ├── pyproject.toml              # Dependencias (uv)
│   ├── config.py                   # Settings, enum de modelos, dimensiones
│   ├── main.py                     # FastAPI app + endpoints
│   ├── models/
│   │   └── property.py             # Modelo Pydantic de propiedad
│   ├── embeddings/
│   │   ├── base.py                 # Clase abstracta EmbeddingProvider
│   │   ├── openai_provider.py      # OpenAI text-embedding-3-small/large
│   │   ├── gemini_provider.py      # Gemini gemini-embedding-001
│   │   └── registry.py             # Registry con cache de providers
│   ├── vectorstore/
│   │   └── qdrant_manager.py       # Gestión de colecciones e indexes
│   ├── ingestion/
│   │   ├── location_normalizer.py  # Diccionario de aliases MX
│   │   ├── excel_loader.py         # Leer Excel → lista de Property
│   │   └── indexer.py              # Generar embeddings e indexar en Qdrant
│   └── search/
│       ├── query_parser.py         # LLM structured output → ParsedQuery
│       └── searcher.py             # Búsqueda semántica con filtros
├── frontend/                       # Playground web (React 19 + Vite + Shadcn)
│   └── src/
│       ├── components/
│       │   ├── search/             # Barra de búsqueda
│       │   ├── results/            # Cards de propiedades
│       │   └── analytics/          # Gráfica de similitud
│       └── types/
├── data/                           # Excel de propiedades
└── plan.md                         # Plan detallado y decisiones de arquitectura
```

## Requisitos previos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- Docker (solo en desarrollo local)

## Setup local

### 1. Levantar Qdrant con Docker

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

### 2. Backend

```bash
cd backend
uv sync
cp .env.example .env
# Editar .env con OPENAI_API_KEY y/o GEMINI_API_KEY
source .venv/bin/activate
uvicorn main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 4. Indexar propiedades

```bash
# Con el backend corriendo:
curl -X POST "http://localhost:8000/ingest?model=gemini"
```

## Variables de entorno

```bash
# .env (basado en .env.example)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
DEFAULT_EMBEDDING_MODEL=openai-small   # openai-small | openai-large | gemini

# Qdrant local (desarrollo)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Qdrant Cloud (producción — si se configura, ignora host/port)
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=tu-api-key

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check del servidor |
| GET | `/health/qdrant` | Estado de las 3 colecciones en Qdrant |
| GET | `/models` | Lista de modelos de embedding soportados |
| POST | `/ingest` | Indexar propiedades del Excel en Qdrant |
| POST | `/search` | Búsqueda en lenguaje natural |
| GET | `/docs` | Swagger UI |

### POST `/search`

```json
{
  "query": "casa con alberca en Cancún, 3 recámaras, menos de 5 millones",
  "model": "gemini",
  "top_k": 10
}
```

### POST `/ingest`

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `model` | `openai-small` | Modelo de embedding (ignorado si `all_models=true`) |
| `all_models` | `false` | Indexar en las 3 colecciones |

## Modelos de embedding

| Modelo | Dimensiones | Colección Qdrant | Costo |
|--------|------------|------------------|-------|
| `openai-small` | 1536 | `properties_openai_small` | $0.02/M tokens |
| `openai-large` | 3072 | `properties_openai_large` | $0.13/M tokens |
| `gemini` | 3072 | `properties_gemini` | $0.15/M tokens |

## Decisiones clave

- **Un solo vector por propiedad** — filtros de metadata separan por aspecto
- **Una colección por modelo** — para A/B testing, consolidar después
- **Embedding = Title primero** — mayor valor semántico, luego tipo/ubicación/atributos
- **Query completo al embedding** — no solo el residuo post-filtros
- **Direcciones NO en embedding, SÍ indexadas como TEXT** — ruido para embeddings pero buscables via MatchText tokenizado
- **Filtros must + should** — must para filtros duros (ciudad, tipo, precio), should para text-match suave (calle, colonia) que prioriza sin excluir
- **Multi-valor en ParsedQuery** — cities[], neighborhoods[], property_types[] soportan queries con múltiples ubicaciones/tipos
- **Normalización doble** — diccionario estático + LLM parser para ubicaciones MX
- **Sparse BM25 en Fase 5** — beneficio marginal con filtros + dense; Qdrant lo hace server-side

Ver [plan.md](plan.md) para el detalle completo de decisiones y justificaciones.

## Fases del proyecto

- [x] **Fase 1** — Backend base: proyecto uv, modelos, embeddings multi-modelo, Qdrant manager, FastAPI
- [x] **Fase 2** — Ingesta: Excel loader, location normalizer, indexer, endpoint POST /ingest (8,803 propiedades)
- [x] **Fase 3** — Búsqueda: query parsing con Gemini 3 Flash + búsqueda semántica con filtros must/should, multi-ciudad/tipo/colonia, detección de calle
- [x] **Fase 4** — Frontend: playground React 19 + Vite + Shadcn/ui con gráfica de similitud interactiva
- [ ] **Fase 5** — Mejoras: sparse BM25 + RRF, reranking, paginación, quantization
- [x] **Fase 6** — Deploy: Railway (backend) + Vercel (frontend) + Qdrant Cloud
