# RAG Properties

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
Busca propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún") y retorna las más relevantes del catálogo.

## Stack

- **Backend**: Python 3.12 + FastAPI
- **Package manager**: uv
- **Vector DB**: Qdrant (Docker local)
- **Embeddings**: OpenAI (small/large) y Gemini (multi-modelo, intercambiables)
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
│   │   ├── gemini_provider.py  # Gemini text-embedding-004
│   │   └── registry.py         # Registry con cache de providers
│   ├── vectorstore/
│   │   └── qdrant_manager.py   # Gestión de colecciones e indexes
│   ├── ingestion/              # (Fase 2)
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
| GET | `/docs` | Swagger UI |

## Modelos de embedding soportados

| Modelo | Dimensiones | Colección Qdrant | Costo |
|--------|------------|------------------|-------|
| `openai-small` | 1536 | `properties_openai_small` | $0.02/M tokens |
| `openai-large` | 3072 | `properties_openai_large` | $0.13/M tokens |
| `gemini` | 768 | `properties_gemini` | Gratis (con límite) |

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
- [ ] **Fase 2** — Ingesta: leer Excel, canonicalizar ubicaciones, generar embeddings, indexar en Qdrant
- [ ] **Fase 3** — Búsqueda: normalización + query parsing + búsqueda semántica con filtros
- [ ] **Fase 4** — Frontend: playground web para probar búsquedas
- [ ] **Fase 5** — Mejoras: sparse BM25 + RRF, reranking, paginación, quantization
