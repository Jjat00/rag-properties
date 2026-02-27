# RAG Properties

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
Busca propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún") y retorna las más relevantes del catálogo.

## Stack

- **Backend**: Python 3.12 + FastAPI
- **Package manager**: uv
- **Vector DB**: Qdrant (Docker local)
- **Embeddings**: OpenAI (small/large) y Gemini (multi-modelo, intercambiables)
- **Query parsing**: Gemini Flash / GPT-4o-mini con structured output

## Estructura

```
rag-properties/
├── backend/
│   ├── config.py               # Settings, enum de modelos, dimensiones
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
│   ├── search/                 # (Fase 3)
│   └── main.py                 # FastAPI app + endpoints
├── data/                       # Excel de propiedades
└── frontend/                   # (Fase 4)
```

## Requisitos previos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker

## Setup

### 1. Clonar y entrar al proyecto

```bash
cd rag-properties
```

### 2. Levantar Qdrant con Docker

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

### 3. Instalar dependencias del backend

```bash
cd backend
uv sync
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus API keys
```

### 5. Levantar el backend

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

| Modelo | Dimensiones | Colección Qdrant |
|--------|------------|------------------|
| `openai-small` | 1536 | `properties_openai_small` |
| `openai-large` | 3072 | `properties_openai_large` |
| `gemini` | 768 | `properties_gemini` |

## Fases del proyecto

- [x] **Fase 1** — Backend base: proyecto uv, modelos, embeddings multi-modelo, Qdrant manager, FastAPI
- [ ] **Fase 2** — Ingesta: leer Excel → generar embeddings → indexar en Qdrant
- [ ] **Fase 3** — Búsqueda: query parsing + búsqueda semántica con filtros
- [ ] **Fase 4** — Frontend: playground web para probar búsquedas
