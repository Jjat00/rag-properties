# RAG Properties

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
Busca propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún") y retorna las más relevantes del catálogo.

## Stack

- **Backend**: Python 3.12 + FastAPI
- **Package manager**: uv
- **Vector DB**: Qdrant (local Docker en desarrollo, Qdrant Cloud en producción)
- **Embeddings**: Gemini gemini-embedding-001 (default) + OpenAI text-embedding-3 small/large (multi-modelo, intercambiables)
- **Query parsing**: Gemini 3 Flash con structured output
- **Agente conversacional**: LangGraph (ReAct) + Gemini 3 Flash con tool calling
- **Streaming**: SSE (Server-Sent Events) para chat en tiempo real
- **Frontend**: React 19 + Vite + Shadcn/ui + Tailwind v4 (dos vistas: Chat y Playground)

## Dos modos de uso

### Chat (vista principal)
Conversación multi-turno con un agente que busca propiedades, presenta resultados y hace preguntas dirigidas cuando hay ambigüedad. Split-screen: chat a la izquierda, propiedades a la derecha.

```
User: "ando buscando casa en renta por andares, puerta de hierro o valle real"
Agent: [ejecuta búsqueda] → "Encontré 8 casas en renta..."
User: "menos de 30 mil al mes"
Agent: [refina búsqueda] → "3 casas en ese rango..."
```

### Playground
Búsqueda single-shot con analytics (distribución de scores, gráfica de similitud, comparación de modelos A/B).

## Cómo funciona

```
Flujo del Chat:
User message
    → Agente (Gemini 3 Flash + LangGraph ReAct)
    → Tool: search_properties(query)
        → QueryParser (Gemini 3 Flash structured output) → ParsedQuery
        → Normalización de ubicaciones (diccionario estático)
        → Filtros must en Qdrant (city, state, type, operation, rangos, MatchText)
        → Embedding del query completo (Gemini embedding-001)
        → Vector search + desambiguación automática
    → Agente analiza resultados + disambiguation
    → Responde al usuario (streaming SSE token por token)
    → Frontend: chat panel + propiedades panel (actualización en tiempo real)

Flujo del Playground:
Query → POST /search → QueryParser → Searcher → SearchResult → Frontend
```

### Pipeline de búsqueda (detalle)

```
Query: "bodega o nave en gdl, zapopan, tlajo en calle alfonso nápoles"
    ↓
1. Normalización: "gdl"→["Guadalajara","Zapopan","Tlajomulco de Zúñiga"]
    ↓
2. LLM Parser (Gemini 3 Flash): extrae
   cities=["Guadalajara","Zapopan","Tlajomulco"], property_types=["Bodega","Nave"],
   street="Alfonso Nápoles"
    ↓
3. Filtros must en Qdrant:
   must: city IN [...], property_type IN ["Bodega comercial","Nave industrial"],
         (address OR neighborhood OR title MATCH "Alfonso Nápoles")
    ↓
4. Vector search: embedding del query completo vs propiedades filtradas
    ↓
5. Top-K + desambiguación automática por estado/colonia/tipo
```

## Estructura

```
rag-properties/
├── backend/
│   ├── pyproject.toml              # Dependencias (uv)
│   ├── config.py                   # Settings, enum de modelos, dimensiones
│   ├── main.py                     # FastAPI app + endpoints (search, chat SSE)
│   ├── models/
│   │   └── property.py             # Modelo Pydantic de propiedad
│   ├── agent/                      # Agente conversacional (LangGraph)
│   │   ├── state.py                # AgentState (MessagesState + campos de búsqueda)
│   │   ├── prompt.py               # System prompt del agente
│   │   ├── tools.py                # Tool search_properties (wrappea Searcher)
│   │   ├── graph.py                # ReAct graph: agent → tools → loop
│   │   └── session.py              # SessionManager in-memory
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
├── frontend/                       # React 19 + Vite + Shadcn (Chat + Playground)
│   └── src/
│       ├── components/
│       │   ├── chat/               # Vista Chat (split-screen)
│       │   │   ├── chat-view.tsx   # Layout 60/40 (chat + propiedades)
│       │   │   ├── chat-panel.tsx  # Lista de mensajes + input
│       │   │   ├── chat-input.tsx  # Textarea + enviar
│       │   │   ├── chat-message.tsx # Burbujas con markdown
│       │   │   └── properties-panel.tsx # Panel derecho con resultados
│       │   ├── search/             # Barra de búsqueda (playground)
│       │   ├── results/            # Cards de propiedades (compartido)
│       │   └── analytics/          # Gráficas de similitud (playground)
│       ├── hooks/
│       │   ├── use-chat.ts         # Estado del chat + streaming
│       │   └── use-search.ts       # Estado de búsqueda (playground)
│       ├── lib/
│       │   ├── chat-api.ts         # SSE stream parser con callbacks
│       │   └── api.ts              # API client REST
│       └── types/
│           └── api.ts              # Tipos compartidos
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
# Editar .env con GEMINI_API_KEY (requerido) y opcionalmente OPENAI_API_KEY
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
GEMINI_API_KEY=AI...              # Requerido (embeddings, query parser, agente)
OPENAI_API_KEY=sk-...             # Opcional (solo si usas modelos OpenAI)
DEFAULT_EMBEDDING_MODEL=gemini    # gemini | openai-small | openai-large

# Agente conversacional
AGENT_MODEL=gemini-3-flash-preview

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
| POST | `/search` | Búsqueda single-shot en lenguaje natural |
| POST | `/chat` | Chat conversacional via SSE streaming |
| GET | `/chat/{id}/history` | Historial de una sesión de chat |
| DELETE | `/chat/{id}` | Borrar sesión de chat |
| GET | `/docs` | Swagger UI |

### POST `/search` (Playground)

```json
{
  "query": "casa con alberca en Cancún, 3 recámaras, menos de 5 millones",
  "model": "gemini",
  "top_k": 10
}
```

### POST `/chat` (Chat conversacional)

```json
{
  "message": "ando buscando casa en renta por andares, puerta de hierro o valle real",
  "session_id": null,
  "model": "gemini",
  "top_k": 10
}
```

Retorna SSE stream con eventos: `session`, `token`, `tool_start`, `results`, `filters`, `disambiguation`, `state_results`, `metrics`, `done`, `error`.

### POST `/ingest`

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `model` | `gemini` | Modelo de embedding (ignorado si `all_models=true`) |
| `all_models` | `false` | Indexar en las 3 colecciones |

## Modelos

### Embeddings (intercambiables)

| Modelo | Dimensiones | Colección Qdrant | Costo | Default |
|--------|------------|------------------|-------|---------|
| `gemini` | 3072 | `properties_gemini` | $0.15/M tokens | **Sí** |
| `openai-small` | 1536 | `properties_openai_small` | $0.02/M tokens | No |
| `openai-large` | 3072 | `properties_openai_large` | $0.13/M tokens | No |

### LLMs

| Uso | Modelo | Provider |
|-----|--------|----------|
| Query parsing | `gemini-3-flash-preview` | Google Gemini |
| Agente conversacional | `gemini-3-flash-preview` | Google Gemini |

## Arquitectura del agente conversacional

```
┌─────────────────────────────────────────────────┐
│  POST /chat (SSE)                               │
│                                                 │
│  User message                                   │
│       ↓                                         │
│  ┌─────────┐    tool_calls?    ┌──────────┐     │
│  │  Agent   │ ──────────────→  │  Tools   │     │
│  │ (Gemini  │ ←──────────────  │ (search) │     │
│  │  3 Flash)│   tool results   └──────────┘     │
│  └─────────┘                                    │
│       ↓ no tool_calls                           │
│  Response (streaming SSE)                       │
│       ↓                                         │
│  Frontend: chat panel + properties panel        │
└─────────────────────────────────────────────────┘
```

**Grafo ReAct (LangGraph):**
- `START` → `agent_node` (Gemini 3 Flash con tools)
- `agent_node` → `should_continue?`
  - Tiene `tool_calls` → `tool_node` (ejecuta search) → `agent_node` (loop)
  - No tiene `tool_calls` → `END` (responde al usuario)

**Tool `search_properties`:**
- Wrappea el pipeline completo: QueryParser → Searcher (normalización → filtros → embed → vector search → desambiguación)
- Retorna JSON con: results, parsed_filters, disambiguation, state_results, metrics
- El agente recibe un resumen + datos para razonar; el frontend recibe resultados completos via SSE

**Memoria:**
- `MemorySaver` (LangGraph in-memory checkpointer) por `thread_id` = `session_id`
- Acumula contexto entre turnos: "terreno en el centro" + "en Quintana Roo" → "terreno en el centro en Quintana Roo"

**SSE Events emitidos por `/chat`:**

| Evento | Data | Propósito |
|--------|------|-----------|
| `session` | `{session_id}` | ID de sesión para continuidad |
| `token` | string | Token de texto del LLM (streaming) |
| `tool_start` | `{name, args}` | El agente invoca búsqueda |
| `results` | `PropertyResult[]` | Resultados de búsqueda |
| `filters` | `ParsedQuery` | Filtros extraídos |
| `disambiguation` | `DisambiguationInfo[]` | Datos de desambiguación |
| `state_results` | `{estado: PropertyResult[]}` | Resultados por estado |
| `metrics` | `SearchMetrics` | Métricas de la búsqueda |
| `done` | `""` | Stream completo |
| `error` | string | Error |

## Decisiones clave

- **Un solo vector por propiedad** — filtros de metadata separan por aspecto
- **Una colección por modelo** — para A/B testing, consolidar después
- **Embedding = Title primero** — mayor valor semántico, luego tipo/ubicación/atributos
- **Query completo al embedding** — no solo el residuo post-filtros
- **Direcciones NO en embedding, SÍ indexadas como TEXT** — ruido para embeddings pero buscables via MatchText tokenizado
- **Filtros unified must** — todos los filtros son must; ubicaciones textuales usan `Filter(should=[address, neighborhood, title])` anidado
- **Multi-valor en ParsedQuery** — cities[], neighborhoods[], property_types[] soportan queries con múltiples ubicaciones/tipos
- **Normalización doble** — diccionario estático + LLM parser para ubicaciones MX
- **Desambiguación automática** — facets por estado, conteo por colonia y tipo
- **LLM prompt basado en datos reales** — estados, ciudades, colonias y calles del catálogo
- **Agente pasa query verbatim** — el agente NUNCA reformula el query del usuario; el parser downstream se encarga de interpretar
- **LangGraph para chat, FastAPI para playground** — multi-turno justifica LangGraph; single-shot no lo necesita

Ver [plan.md](plan.md) para el detalle completo de decisiones y justificaciones.

## Fases del proyecto

- [x] **Fase 1** — Backend base: proyecto uv, modelos, embeddings multi-modelo, Qdrant manager, FastAPI
- [x] **Fase 2** — Ingesta: Excel loader, location normalizer, indexer, endpoint POST /ingest (8,803 propiedades)
- [x] **Fase 3** — Búsqueda: query parsing con Gemini 3 Flash + filtros unified must + desambiguación automática
- [x] **Fase 4** — Frontend playground: React 19 + Vite + Shadcn/ui con analytics y desambiguación clickeable
- [x] **Fase 4.5** — Chat conversacional: agente LangGraph ReAct + Gemini 3 Flash + SSE streaming + UI split-screen
- [ ] **Fase 5** — Mejoras: sparse BM25 + RRF, reranking, paginación, quantization
- [x] **Fase 6** — Deploy: Railway (backend) + Vercel (frontend) + Qdrant Cloud
